# ADR 0003: Local Artifact Storage

## Status

Accepted

## Context

MVP 1 needs retrieval and reproducibility, but durable campaign memory is MVP 2.

## Decision

Persist completed runs as immutable JSON files under configurable `ARTIFACT_DIR` using atomic writes.

## Consequences

The slice remains easy to run locally. PostgreSQL and Redis are deferred until campaign memory requires them.

