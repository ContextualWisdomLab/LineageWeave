# ADR 0272: Twenty-millisecond read SLO

- Status: Accepted
- Date: 2026-08-31
- Supersedes: the no-read-threshold statements in ADR 0206

## Context

Authenticated Dashboard reads against 43,189 source records exposed a planner
cardinality error: PostgreSQL estimated one eligible row, repeatedly probed an
index, and left the browser in a loading state. A timeout would only hide that
cost. The product owner has now set an explicit requirement that every lookup
complete within 20 milliseconds.

ISO/IEC 25010:2023 makes performance efficiency part of the product quality
model, while ISO/IEC 25023:2016 defines quantitative product-quality
measurement. The threshold itself is the product-owner requirement; it is not
derived from either standard or from a rule of thumb.

## Decision

1. Every authenticated REST `GET` and MCP read tool has a maximum 20 ms
   service-processing budget. Measurement starts at application request entry
   and ends when the complete response bytes are ready. It includes identity
   and authorization checks, database work, projection, and serialization.
2. Provider and measurement computations are asynchronous commands, not
   lookups. Their enqueue, status, result, and citation reads remain subject to
   20 ms; the external computation duration is reported separately.
3. Acceptance measures cold and warm reads. A cache-hit run alone is not
   evidence. The declared deployment, dataset cardinality, response-byte
   count, concurrency, hardware, and raw maximum distribution stay with the
   runtime evidence. Every observed request must meet 20 ms; an average or
   percentile cannot conceal a slower request.
4. Setting a 20 ms timeout, returning an incomplete response, dropping
   authorized evidence, or moving an ordinary read behind a job does not meet
   the SLO. A failed request is a failed functional and performance check.
5. Read paths use bounded projections and continuation where the complete
   detail set cannot meet the budget. Summary counts remain exact over the
   authorized population; continuation changes transport size, not evidence
   membership, ranking, or measurement.
6. PostgreSQL plans must use narrow, maintained access paths instead of
   rescanning wide source bodies. Eligibility predicates remain logically
   identical, ABAC executes before aggregation, and source/provenance tables
   remain authoritative and normalized.
7. k6 and database-plan checks enforce the same 20 ms maximum. The gate records
   cold and warm observations separately and fails on any HTTP, authorization,
   schema, citation, or latency failure.
8. Backend PostgreSQL sessions disable JIT. Runtime plans showed compilation
   startup dominating the bounded interactive aggregates without changing the
   result; analytical workers may opt in only with their own measured plan.

## Consequences

The existing Dashboard observation that defined no latency threshold is no
longer sufficient. Each read surface needs exact-head runtime evidence before
release. Slow endpoints stay an explicit product gap until both cold and warm
checks meet the budget; documentation or a green unit suite cannot close it.

## References

International Organization for Standardization. (2016). *Systems and software
engineering—Systems and software Quality Requirements and Evaluation
(SQuaRE)—Measurement of system and software product quality* (ISO/IEC Standard
No. 25023:2016). https://www.iso.org/standard/35747.html

International Organization for Standardization. (2023). *Systems and software
engineering—Systems and software Quality Requirements and Evaluation
(SQuaRE)—Product quality model* (ISO/IEC Standard No. 25010:2023).
https://www.iso.org/standard/78176.html
