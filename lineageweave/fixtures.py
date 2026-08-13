"""Synthetic demo dataset. No real organization, customer, or record data --
every id, label, and date below is fabricated for demonstration purposes.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .models import Record

_BASE = datetime(2026, 1, 1)


def _day(offset: int) -> datetime:
    return _BASE + timedelta(days=offset)


def sample_records() -> list[Record]:
    """A small synthetic dataset with a deliberate branch point in group A-100.

    The pricing-renegotiation follow-up (rec-002) is where the delivery
    question (rec-004) attaches instead of the very first record -- both
    scored closer to rec-002 in time and text than to the day-0 initial
    visit -- so rec-002 ends up with two children (rec-003's revised quote,
    and rec-004's delivery question): the "git branch" shape this project
    demonstrates. rec-006 is intentionally unrelated (different topic, no
    shared project code) and should surface as its own root, not be
    force-attached to a weak match.
    """
    return [
        Record("rec-001", "A-100", "Initial site visit and project scope discussion", _day(0), "proj-alpha"),
        Record("rec-002", "A-100", "Pricing renegotiation follow-up", _day(5), "proj-alpha"),
        Record("rec-003", "A-100", "Pricing renegotiation: revised quote sent", _day(9), "proj-alpha"),
        Record("rec-004", "A-100", "Delivery schedule question raised", _day(6), "proj-alpha"),
        Record("rec-005", "A-100", "Delivery schedule confirmed with logistics", _day(11), "proj-alpha"),
        Record("rec-006", "A-100", "Unrelated: annual account review", _day(40), ""),
        Record("rec-101", "B-200", "Technical specification review meeting", _day(2), "proj-beta"),
        Record("rec-102", "B-200", "Specification revision requested", _day(8), "proj-beta"),
        Record("rec-103", "B-200", "Revised specification approved", _day(15), "proj-beta"),
    ]


def ambiguous_keyman_post() -> tuple[str, str]:
    """A synthetic post that is not a trivially-templated 'Alice of Acme'
    list. Side and affiliation have to be read out of running prose:
    one of our people, one dual-hatted counterparty, one internal
    counsel mentioned only by role, and an organization that sent
    nobody (so it must not be invented as a person).
    """
    title = "Follow-up after the Northridge transformer bid workshop"
    body = (
        "Jordan Hale walked our sales team through the revised bid timeline "
        "and asked Priya Nair (who sits on both Northridge Grid and its "
        "parent, Northridge Holdings) to confirm the inspection window. "
        "Jordan also looped in our legal counsel, Sam Okonkwo, because "
        "Priya's dual role at the holding company is what made the "
        "warranty language messy last quarter. No one from Westfield "
        "Power attended -- they sent a note saying they would review the "
        "minutes later."
    )
    return title, body


def ambiguous_entity_relationship_post() -> tuple[str, str, list[str]]:
    """A synthetic post where a keyword-matcher would get the relationship
    classification wrong: the same organization is both a current customer
    (in one product line) and a known competitor (in another), described
    in running prose rather than a labeled list. Also names a supplier
    (the uncommon "vos" case) and a pure market-signal mention with no
    single counterparty.

    Returns (title, body, organization_names).
    """
    title = "Meridian account review and switchgear market note"
    body = (
        "Meridian Utilities placed a repeat order for our transformer line "
        "this quarter -- their third since the original installation -- but "
        "their newly-acquired switchgear division has started bidding "
        "directly against us on two municipal contracts, undercutting our "
        "quote by double digits. Separately, Colby Insulation shipped the "
        "replacement gasket stock a week early, which kept the Meridian "
        "order from slipping. Industry chatter at the regional utilities "
        "conference suggested overall grid-modernization spending is up "
        "this year, though no specific buyer named that directly."
    )
    return title, body, ["Meridian Utilities", "Colby Insulation"]


def ambiguous_commitment_post() -> tuple[str, str]:
    """A synthetic post with a genuine customer commitment whose deadline
    is stated relative to the post date ("by next Friday"), not as an
    absolute date -- exercising the reference-date resolution that makes
    commitment extraction harder than a plain keyword match. Also
    contains a second sentence that looks date-like but is NOT a
    commitment (a past event, not a promise), so a naive "does this post
    mention a date" heuristic would get it wrong.
    """
    title = "Follow-up on the Riverbend order confirmation"
    body = (
        "Thanks for confirming the order last Tuesday -- that part is "
        "already done. One open item: we still owe Riverbend the revised "
        "delivery schedule, and I told their buyer we'd have it to them by "
        "next Friday. Please make sure procurement has final numbers "
        "before then."
    )
    return title, body
