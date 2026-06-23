# ADR 0002: Provider Abstraction

## Status

Accepted

## Context

The app needs mock-backed CI and optional live multimodal analysis.

## Decision

Define `PerceptionProvider` as a domain-facing port. Implement `MockPerceptionProvider` and `OpenAIPerceptionProvider` in infrastructure.

## Consequences

Domain and pipeline code do not depend on OpenAI SDK details, and tests never require external API access.

