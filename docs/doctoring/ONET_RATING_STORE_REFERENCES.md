# O*NET occupation-rating store evidence

This supporting note records the source and database capabilities governed by
ADR 0254. It introduces no independent architecture decision.

O*NET 31.0 occupation data tables publish occupation and element identifiers,
scale identifiers and names, decimal values, optional category values, sample
sizes, standard errors, confidence bounds, suppression/relevance flags, update
dates, and domain sources. These fields remain source observations; they are
not locally estimated psychometric weights.

PostgreSQL declarative partitioning provides exact LIST boundaries and
partition pruning. A unique constraint on a partitioned table includes its
partition key; `UNIQUE NULLS NOT DISTINCT` makes a missing category one stable
identity without a sentinel value.

## APA 7 references

National Center for O*NET Development. (2026). *O*NET 31.0 database* [Data
set]. https://www.onetcenter.org/database.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation:
Table partitioning*. https://www.postgresql.org/docs/current/ddl-partitioning.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation:
CREATE TABLE*. https://www.postgresql.org/docs/current/sql-createtable.html
