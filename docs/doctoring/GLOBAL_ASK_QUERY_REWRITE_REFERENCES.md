# Global Ask query-rewrite references

This register supports ADR 0217. It records research and standards inputs; the
ADR is the normative decision.

Ma, X., Gong, Y., He, P., Zhao, H., & Duan, N. (2023). Query rewriting in
retrieval-augmented large language models. In *Proceedings of the 2023
Conference on Empirical Methods in Natural Language Processing* (pp.
5303–5315). Association for Computational Linguistics.
https://doi.org/10.18653/v1/2023.emnlp-main.322

PostgreSQL Global Development Group. (2026). *Text search functions and
operators*. https://www.postgresql.org/docs/current/functions-textsearch.html

Adoption note: LineageWeave adopts a query-rewrite stage, not unconstrained
query expansion. The repository accepts only phrases copied exactly from the
question and applies them as separately parameterized PostgreSQL text-search
queries. contextual-orchestrator owns structured generation, model discovery,
and reasoning allocation; RankWeave retains ranking fusion ownership.
