# ADR 0004: Structured Model Output

## Status

Accepted

## Context

Perception output needs evidence coverage, confidence scores, and explicit uncertainty.

## Decision

Prompt the live model for structured JSON matching the `ProductProfile` schema and validate with Pydantic. Reject schema-invalid output after one bounded repair attempt.

## Consequences

The pipeline can fail visibly instead of silently accepting fluent but invalid output.

