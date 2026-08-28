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
    cited_source_references: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Project a settled Ask answer into linked report and alert contracts.

    Alert delivery is explicitly subscription-driven.  A citation-bearing
    answer is eligible for evidence-change alerts, but this function never
    guesses urgency from words in the answer.
    """
    evidence_by_post = {
        str(item["post_id"]): list(item.get("facts") or ())
        for item in cited_post_evidence
        if item.get("post_id")
    }
    references_by_post: dict[str, list[dict[str, Any]]] = {}
    for item in cited_source_references:
        post_id = str(item.get("post_id") or "")
        url = item.get("evidence_url")
        if not post_id or not isinstance(url, str) or not url:
            continue
        references_by_post.setdefault(post_id, []).append(
            {
                "url": url,
                "title": item.get("evidence_title_text"),
                "excerpt": item.get("evidence_excerpt_text"),
                "judgment_code": item.get("judgment_code"),
                "lead_kind_code": item.get("lead_kind_code"),
                "next_action": item.get("next_action_text"),
            }
        )
    documents = []
    for post in cited_posts:
        post_id = str(post["post_id"])
        encoded_id = quote(post_id, safe="")
        documents.append(
            {
                "post_id": post_id,
                "title": str(post["post_title"]),
                "api_path": f"/api/posts/{encoded_id}",
                "resource_uri": f"lineageweave://posts/{encoded_id}",
                "evidence_facts": evidence_by_post.get(post_id, []),
                "source_references": references_by_post.get(post_id, []),
            }
        )
    return {
        "contract_version": "1.0",
        "report": {
            "media_type": "text/markdown",
            "body": answer_text,
            "source_documents": documents,
        },
        "alert": {
            "trigger_code": "cited_evidence_changed",
            "delivery_status_code": "not_subscribed",
            "eligible": bool(documents),
            "watched_resource_uris": [item["resource_uri"] for item in documents],
        },
    }
