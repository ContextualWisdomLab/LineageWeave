"""Correctness checks for the DOT/FJA worker-function read model
(ADR 0232).

The tests treat the published Dictionary of Occupational Titles
Appendix B tables as ground truth: every declared concept must carry
the official definition verbatim, the definitional rank from the
published table. Nothing here may accept an invented weight, unsupported
crosswalk, or placeholder for missing evidence.
"""

from __future__ import annotations

import hashlib

import pytest

from lineageweave.ontology import all_declared_lookup_codes
from lineageweave.worker_function_taxonomy import (
    WORKER_FUNCTION_DOMAINS,
    worker_function,
    worker_function_records,
)

_OFFICIAL_TAXONOMY_SHA256 = (
    "b960c338f8fa6a2795dc402a527b012bfadc24de45a1333845c05531e7c32ba3"
)

def _record_map() -> dict[tuple[str, int], object]:
    """Index every declared record by its ``(domain, rank)`` pair."""
    return {(record.domain, record.rank): record for record in worker_function_records()}


def test_every_published_worker_function_is_declared() -> None:
    """The taxonomy declares exactly the 24 DOT functions: Data 0-6,
    People 0-8, Things 0-7 -- no more, no fewer."""
    assert len(WORKER_FUNCTION_DOMAINS) == 3
    assert len(worker_function_records()) == 24


def test_domain_ranks_match_the_published_table_extents() -> None:
    """Each domain declares exactly one concept per published rank."""
    records_by_domain: dict[str, set[int]] = {}
    for record in worker_function_records():
        records_by_domain.setdefault(record.domain, set()).add(record.rank)
    for domain, (low, high) in WORKER_FUNCTION_DOMAINS.items():
        assert records_by_domain[domain] == set(range(low, high + 1))


def test_definitions_carry_the_official_dot_text() -> None:
    """The complete ordered taxonomy matches the verified DOT text."""
    payload = "\n".join(
        f"{record.domain}:{record.rank}:{record.label}:{record.definition}"
        for record in worker_function_records()
    )
    assert hashlib.sha256(payload.encode()).hexdigest() == _OFFICIAL_TAXONOMY_SHA256


def test_labels_are_unique_across_the_scheme() -> None:
    """No two functions share a preferred label, so label-based display
    can never conflate two ranks."""
    labels = [record.label for record in worker_function_records()]
    assert len(labels) == len(set(labels))


def test_records_are_sorted_in_dot_digit_order_then_rank() -> None:
    """Output order is Data, People, Things with ascending ranks inside
    each domain -- byte-stable serialization input."""
    records = worker_function_records()
    domain_order = ["data"] * 7 + ["people"] * 9 + ["things"] * 8
    assert [record.domain for record in records] == domain_order
    assert [record.rank for record in records[:7]] == list(range(7))
    assert [record.rank for record in records[7:16]] == list(range(9))
    assert [record.rank for record in records[16:]] == list(range(8))


def test_iri_is_the_canonical_repository_case_namespace() -> None:
    """Every record IRI uses the repository-case canonical namespace;
    no lowercase compatibility IRI may be minted here (ADR 0207)."""
    canonical_prefix = "https://contextualwisdomlab.github.io/LineageWeave/ontology#"
    for record in worker_function_records():
        assert record.iri.startswith(canonical_prefix)


def test_worker_functions_carry_no_lookup_code() -> None:
    """Worker-function concepts deliberately declare no ``lookupCode``,
    so the lookup-code round trip stays untouched by this extension."""
    from lineageweave.ontology import iri_for_lookup_code

    assert iri_for_lookup_code("worker_function_data_synthesizing") is None
    # The pre-existing governed vocabulary is unchanged in size: the 31
    # lookup codes the schema seeded before this ADR are still all there
    # is.
    assert len(all_declared_lookup_codes()) == 31


@pytest.mark.parametrize(
    ("domain", "rank", "expected_label"),
    [
        ("data", 0, "Synthesizing"),
        ("people", 0, "Mentoring"),
        ("people", 6, "Speaking-Signaling"),
        ("people", 8, "Taking Instructions-Helping"),
        ("things", 0, "Setting Up"),
        ("things", 7, "Handling"),
    ],
)
def test_worker_function_resolves_real_pairs(domain: str, rank: int, expected_label: str) -> None:
    """Published (domain, rank) pairs resolve to their labeled record."""
    record = worker_function(domain, rank)
    assert record is not None
    assert record.label == expected_label


def test_worker_function_returns_none_for_an_absent_rank() -> None:
    """An undeclared rank inside a valid domain is an honest unknown,
    never a placeholder record."""
    assert worker_function("data", 99) is None


def test_worker_function_raises_on_an_unknown_domain() -> None:
    """An unrecognized domain is caller error, not missing evidence."""
    with pytest.raises(ValueError, match="unknown worker-function domain"):
        worker_function("machines", 0)
