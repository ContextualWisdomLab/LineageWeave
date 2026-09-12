"""Stable delivery projection for evidence-grounded Ask answers.

The Ask worker owns retrieval and reasoning.  This module only packages its
settled answer and citations for UI, report, alert, and future MCP consumers;
it never classifies text or invents evidence.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping
from urllib.parse import quote


def build_ask_delivery(
    answer_text: str,
    cited_posts: Iterable[Mapping[str, str]],
    cited_post_evidence: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Project a settled Ask answer into linked report and alert contracts.

    Alert delivery is explicitly subscription-driven.  A citation-bearing
    answer is eligible for evidence-change alerts, but this function never
    guesses urgency from words in the answer.
    """
    evidence_facts_by_post_id = {
        str(post_evidence["post_id"]): list(post_evidence.get("facts") or ())
        for post_evidence in cited_post_evidence
        if post_evidence.get("post_id")
    }
    source_documents = []
    for cited_post in cited_posts:
        post_id = str(cited_post["post_id"])
        encoded_post_id = quote(post_id, safe="")
        source_documents.append(
            {
                "post_id": post_id,
                "title": str(cited_post["post_title"]),
                "api_path": f"/api/posts/{encoded_post_id}",
                "resource_uri": f"lineageweave://posts/{encoded_post_id}",
                "evidence_facts": evidence_facts_by_post_id.get(post_id, []),
            }
        )
    return {
        "contract_version": "1.0",
        "report": {
            "media_type": "text/markdown",
            "body": answer_text,
            "source_documents": source_documents,
        },
        "alert": {
            "trigger_code": "cited_evidence_changed",
            "delivery_status_code": "not_subscribed",
            "eligible": bool(source_documents),
            "watched_resource_uris": [
                source_document["resource_uri"] for source_document in source_documents
            ],
        },
    }
