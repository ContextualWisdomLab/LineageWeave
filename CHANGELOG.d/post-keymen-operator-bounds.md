# Post-Keyman operator bounds

The bounded Post Keyman backfill now admits only exact batch limits from 1 through 100, so one `--all` invocation cannot become an effectively unbounded serial crawl. Direct programmatic calls receive the same admission checks as the CLI. A non-default `--limit` is rejected unless `--all` is selected, so a requested batch size cannot be silently accepted and then ignored by the default one-post path; `--post-id` and `--all` remain mutually exclusive.

An explicit `--post-id` must now be the canonical lowercase, hyphenated UUID for `source_post.post_id`. Malformed values and alternate UUID spellings fail before gateway or database work instead of creating multiple textual representations of the same internal post identity; opaque source-system record keys remain separate evidence under ADR 0046.

Per-post timeout admission now also fails closed for malformed direct-call numeric values whose magnitude cannot be represented by the runtime finite-number check, instead of leaking an `OverflowError` from validation. The admitted operator timeout is forwarded to both Keyman extraction and synchronous Vision requests through the contextual-orchestrator client boundary. This removes hidden shorter 180-second transport caps without introducing provider/model configuration in LineageWeave.
