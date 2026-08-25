# Unreleased — Analysis-run provider work releases the database pool

## Fixed

- Analysis-run delivery now commits its claim before ThreadWeave adjudication
  or TEPP transport, releases the pooled connection while that work runs, and
  persists the complete outcome in a second short transaction. PostgreSQL
  session advisory locks serialize the HTTP and worker paths without an
  invented lease timeout.
