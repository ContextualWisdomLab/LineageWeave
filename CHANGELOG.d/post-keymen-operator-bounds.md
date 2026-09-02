# Post-Keyman operator bounds

The bounded Post Keyman backfill now admits only exact batch limits from 1 through 100, so one `--all` invocation cannot become an effectively unbounded serial crawl. Direct programmatic calls receive the same admission checks as the CLI.

The operator-selected per-post timeout is also forwarded to both Keyman extraction and synchronous Vision requests through the contextual-orchestrator client boundary. This removes hidden shorter 180-second transport caps without introducing provider/model configuration in LineageWeave.
