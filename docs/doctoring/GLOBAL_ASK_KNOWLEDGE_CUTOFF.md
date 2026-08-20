# Global Ask knowledge cutoff (ADR 0101 / v2.23.0)

Ask Agent now accepts an optional ISO-8601 `knowledge_cutoff`.

## Buyer next action

1. Open Ask Agent.
2. Enter a question. Optionally set **Knowledge cutoff**.
3. If the cutoff is empty, the answer is live-only and is never labeled
   as-of.
4. If the cutoff is set, open a cited post to compare the retained body.
   A post created after the cutoff does not appear. A missing historical
   body is named; the live rewrite is not used.

No TEPP theta is invented. No SearXNG claim is invented.

## References

International Organization for Standardization. (2019). *ISO 8601-1:2019:
Date and time—Representations for information interchange—Part 1: Basic
rules*.

Jensen, C. S., & Snodgrass, R. T. (1999). Temporal data management.
*IEEE Transactions on Knowledge and Data Engineering, 11*(1), 36–44.

World Wide Web Consortium. (2022). *Time ontology in OWL*.
https://www.w3.org/TR/owl-time/
