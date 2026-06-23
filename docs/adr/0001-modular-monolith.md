# ADR 0001: Modular Monolith First

## Status

Accepted

## Context

The first slice needs a working API, CLI, and frontend without premature distributed infrastructure.

## Decision

Use one FastAPI backend with internal boundaries: domain, application, infrastructure, API, and observability.

## Consequences

Development and tests stay simple while provider and persistence seams remain explicit for future slices.

