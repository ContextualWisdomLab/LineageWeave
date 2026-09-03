"""Versioned product-UI translation reads with exact screen-key cache identities.

PostgreSQL is the source of truth. Valkey is only an exact-version read cache;
malformed or unavailable cache data falls back to PostgreSQL and can never
supply ontology labels or cross-locale fallback copy.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol

import asyncpg
from redis.exceptions import RedisError


SUPPORTED_UI_LOCALES: tuple[str, ...] = ("ko", "en", "ja", "zh", "vi", "es", "de", "fr")
_CACHE_TTL_SECONDS = 300

_SELECT_REQUIRED_KEYS_SQL = """
select translation_key.translation_key,
       case
           when translation_text.translated_text is null then null
           else encode(sha256(convert_to(translation_text.translated_text, 'UTF8')), 'hex')
       end as translated_text_sha256
  from ui_translation_resource as resource
  join ui_translation_key as translation_key
    on translation_key.resource_id = resource.resource_id
  left join ui_translation_text as translation_text
    on translation_text.resource_id = translation_key.resource_id
   and translation_text.translation_key = translation_key.translation_key
   and translation_text.locale = $4
 where resource.product_key = $1
   and resource.screen_key = $2
   and resource.resource_version = $3
   and resource.publication_state = 'published'
 order by translation_key.translation_key
"""

_SELECT_SCREEN_SQL = """
with selected_resource as (
    select resource_id, resource_version
      from ui_translation_resource
     where product_key = $1
       and screen_key = $2
       and publication_state = 'published'
       and ($4::bigint is null or resource_version = $4)
     order by resource_version desc
     limit 1
)
select selected_resource.resource_version,
       translation_key.translation_key,
       translation_text.translated_text
  from selected_resource
  join ui_translation_key as translation_key
    on translation_key.resource_id = selected_resource.resource_id
  left join ui_translation_text as translation_text
    on translation_text.resource_id = translation_key.resource_id
   and translation_text.translation_key = translation_key.translation_key
   and translation_text.locale = $3
 order by translation_key.translation_key
"""


class TranslationCoverageError(RuntimeError):
    """Raised when a requested locale lacks any key required by a screen."""


class TranslationResourceNotFound(LookupError):
    """Raised when no published resource exists for the requested identity."""


class AsyncTranslationCache(Protocol):
    """Minimal Valkey-compatible contract used by the translation read model."""

    async def get(self, key: str) -> str | bytes | None:
        """Return a cached payload or ``None`` when the key is absent."""
        ...

    async def set(self, key: str, value: str, *, ex: int) -> object:
        """Store a payload with a bounded TTL."""
        ...


@dataclass(frozen=True, slots=True)
class TranslationScreen:
    """One immutable, complete product-screen translation projection."""

    product_key: str
    screen_key: str
    resource_version: int
    locale: str
    cache_key: str
    translations: Mapping[str, str]


def validate_ui_locale(locale: str) -> str:
    """Return a supported locale or reject it without fallback substitution."""
    if locale not in SUPPORTED_UI_LOCALES:
        raise ValueError(f"unsupported UI locale: {locale!r}")
    return locale


def _validate_identity_segment(value: str, *, field_name: str) -> str:
    """Reject blank, padded, or delimiter-bearing cache identity segments."""
    normalized = value.strip()
    if normalized != value:
        raise ValueError(f"{field_name} must not contain leading or trailing whitespace")
    if not normalized or ":" in normalized:
        raise ValueError(f"{field_name} must be nonblank and must not contain ':'")
    return normalized


def build_translation_cache_key(
    product_key: str,
    screen_key: str,
    resource_version: int,
    locale: str,
) -> str:
    """Bind one cache entry to product, screen, immutable version, and locale."""
    product = _validate_identity_segment(product_key, field_name="product_key")
    screen = _validate_identity_segment(screen_key, field_name="screen_key")
    if isinstance(resource_version, bool) or not isinstance(resource_version, int) or resource_version <= 0:
        raise ValueError("resource_version must be a positive integer")
    language = validate_ui_locale(locale)
    return f"ui-translation:{product}:{screen}:v{resource_version}:{language}"


def require_complete_translation_map(
    required_keys: Sequence[str],
    translations: Mapping[str, str | None],
    *,
    locale: str,
) -> dict[str, str]:
    """Return the exact screen projection or fail closed on missing/blank copy."""
    validate_ui_locale(locale)
    projection: dict[str, str] = {}
    missing: list[str] = []
    for key in required_keys:
        value = translations.get(key)
        if not isinstance(value, str) or not value.strip():
            missing.append(key)
            continue
        projection[key] = value
    if missing:
        missing_keys = ", ".join(sorted(missing))
        raise TranslationCoverageError(f"{locale} translation is incomplete: {missing_keys}")
    return projection


def _freeze_translations(translations: Mapping[str, str]) -> Mapping[str, str]:
    """Return a detached read-only mapping for one published screen value object."""
    return MappingProxyType(dict(translations))


def _matches_authoritative_text_digests(
    translations: Mapping[str, str],
    expected_text_digests: Mapping[str, str | None],
) -> bool:
    """Verify cached copy against PostgreSQL-owned SHA-256 evidence for every screen key."""
    if set(translations) != set(expected_text_digests):
        return False
    for key, value in translations.items():
        expected_digest = expected_text_digests.get(key)
        if not isinstance(expected_digest, str) or len(expected_digest) != 64:
            return False
        if hashlib.sha256(value.encode("utf-8")).hexdigest() != expected_digest:
            return False
    return True


def _decode_cached_screen(
    raw_payload: str | bytes,
    *,
    product_key: str,
    screen_key: str,
    resource_version: int,
    locale: str,
    expected_text_digests: Mapping[str, str | None],
) -> TranslationScreen | None:
    """Accept a cache hit only when identity and copy match PostgreSQL evidence."""
    try:
        decoded = json.loads(raw_payload)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
        return None
    if not isinstance(decoded, dict):
        return None
    if decoded.get("product_key") != product_key or decoded.get("screen_key") != screen_key:
        return None
    if (
        isinstance(decoded.get("resource_version"), bool)
        or decoded.get("resource_version") != resource_version
        or decoded.get("locale") != locale
    ):
        return None
    translations = decoded.get("translations")
    if not isinstance(translations, dict) or not translations:
        return None
    if any(not isinstance(key, str) or not isinstance(value, str) or not value.strip() for key, value in translations.items()):
        return None
    if not _matches_authoritative_text_digests(translations, expected_text_digests):
        return None
    cache_key = build_translation_cache_key(product_key, screen_key, resource_version, locale)
    return TranslationScreen(
        product_key=product_key,
        screen_key=screen_key,
        resource_version=resource_version,
        locale=locale,
        cache_key=cache_key,
        translations=_freeze_translations(translations),
    )


async def _read_exact_cache(
    cache: AsyncTranslationCache | None,
    *,
    product_key: str,
    screen_key: str,
    resource_version: int,
    locale: str,
    expected_text_digests: Mapping[str, str | None],
) -> TranslationScreen | None:
    """Read an exact-version cache entry after PostgreSQL establishes copy digests."""
    if cache is None:
        return None
    cache_key = build_translation_cache_key(product_key, screen_key, resource_version, locale)
    try:
        raw_payload = await cache.get(cache_key)
    except RedisError:
        return None
    if raw_payload is None:
        return None
    return _decode_cached_screen(
        raw_payload,
        product_key=product_key,
        screen_key=screen_key,
        resource_version=resource_version,
        locale=locale,
        expected_text_digests=expected_text_digests,
    )


async def _write_exact_cache(cache: AsyncTranslationCache | None, screen: TranslationScreen) -> None:
    """Populate the exact-version cache without making cache availability authoritative."""
    if cache is None:
        return
    payload = json.dumps(
        {
            "product_key": screen.product_key,
            "screen_key": screen.screen_key,
            "resource_version": screen.resource_version,
            "locale": screen.locale,
            "translations": dict(screen.translations),
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    try:
        await cache.set(screen.cache_key, payload, ex=_CACHE_TTL_SECONDS)
    except RedisError:
        return


async def read_translation_screen(
    pool: asyncpg.Pool,
    cache: AsyncTranslationCache | None,
    *,
    product_key: str,
    screen_key: str,
    locale: str,
    resource_version: int | None = None,
) -> TranslationScreen:
    """Read one published screen version and reject incomplete requested-locale copy.

    Explicit-version cache reads first verify PostgreSQL-owned SHA-256 evidence
    for every published screen key, release that connection, and only then
    perform Valkey I/O. A cache miss reacquires PostgreSQL for the authoritative
    projection. Latest reads resolve the complete projection from PostgreSQL
    before populating cache.
    """
    product = _validate_identity_segment(product_key, field_name="product_key")
    screen = _validate_identity_segment(screen_key, field_name="screen_key")
    language = validate_ui_locale(locale)
    if resource_version is not None and (
        isinstance(resource_version, bool)
        or not isinstance(resource_version, int)
        or resource_version <= 0
    ):
        raise ValueError("resource_version must be a positive integer")

    if resource_version is not None:
        async with pool.acquire() as connection:
            key_rows = await connection.fetch(
                _SELECT_REQUIRED_KEYS_SQL,
                product,
                screen,
                resource_version,
                language,
            )
        if not key_rows:
            raise TranslationResourceNotFound(
                f"no published translation resource for {product}/{screen} version {resource_version!r}"
            )
        expected_text_digests: dict[str, str | None] = {}
        for row in key_rows:
            translation_key = str(row["translation_key"])
            digest = row["translated_text_sha256"]
            expected_text_digests[translation_key] = digest if isinstance(digest, str) else None
        cached = await _read_exact_cache(
            cache,
            product_key=product,
            screen_key=screen,
            resource_version=resource_version,
            locale=language,
            expected_text_digests=expected_text_digests,
        )
        if cached is not None:
            return cached

    async with pool.acquire() as connection:
        rows = await connection.fetch(
            _SELECT_SCREEN_SQL,
            product,
            screen,
            language,
            resource_version,
        )
    if not rows:
        raise TranslationResourceNotFound(
            f"no published translation resource for {product}/{screen} version {resource_version!r}"
        )

    resolved_version = int(rows[0]["resource_version"])
    required_keys = [str(row["translation_key"]) for row in rows]
    values = {
        str(row["translation_key"]): row["translated_text"]
        for row in rows
    }
    projection = require_complete_translation_map(required_keys, values, locale=language)
    cache_key = build_translation_cache_key(product, screen, resolved_version, language)
    result = TranslationScreen(
        product_key=product,
        screen_key=screen,
        resource_version=resolved_version,
        locale=language,
        cache_key=cache_key,
        translations=_freeze_translations(projection),
    )
    await _write_exact_cache(cache, result)
    return result
