"""Authorization value objects for persisted Post Chat replay.

This module owns only the immutable generation-scope comparison. Database
source visibility remains authoritative in ``post_eligibility`` and the
application boundary must still reauthorize every captured source before
replaying derived text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


def _normalized_identity_set(values: Iterable[str]) -> frozenset[str]:
    """Normalize persisted/request identity values without changing their meaning."""
    return frozenset(str(value) for value in values)


@dataclass(frozen=True)
class PostChatAuthorizationScope:
    """Immutable generation authorization scope for one persisted Post Chat answer."""

    corporate_entity_ids: frozenset[str]
    process_unit_ids: frozenset[str]
    process_scope_limited: bool

    @classmethod
    def captured(
        cls,
        *,
        corporate_entity_ids: Iterable[str],
        process_unit_ids: Iterable[str],
    ) -> "PostChatAuthorizationScope":
        """Capture request scope while preserving empty-set unrestricted semantics."""
        normalized_process_ids = _normalized_identity_set(process_unit_ids)
        return cls(
            corporate_entity_ids=_normalized_identity_set(corporate_entity_ids),
            process_unit_ids=normalized_process_ids,
            process_scope_limited=bool(normalized_process_ids),
        )

    def is_subsumed_by(
        self,
        *,
        current_corporate_entity_ids: Iterable[str],
        current_process_unit_ids: Iterable[str],
    ) -> bool:
        """Return whether the current reader is at least as broad as generation scope."""
        current_corporate_ids = _normalized_identity_set(current_corporate_entity_ids)
        if not self.corporate_entity_ids.issubset(current_corporate_ids):
            return False

        current_process_ids = _normalized_identity_set(current_process_unit_ids)
        if not self.process_scope_limited:
            # Empty process scope means authenticated unrestricted visibility.
            # A later restricted reader is narrower and cannot reuse derived text.
            return not current_process_ids

        # An unrestricted current reader is broader than any restricted capture.
        return not current_process_ids or self.process_unit_ids.issubset(current_process_ids)
