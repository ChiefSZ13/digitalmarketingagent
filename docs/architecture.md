# Architecture

The system is a small modular monolith with one FastAPI process and one Next.js frontend.

```mermaid
flowchart LR
  Browser["Next.js Browser UI"] --> API["FastAPI API"]
  CLI["marketing-agent CLI"] --> Pipeline["Perception Pipeline"]
  API --> Pipeline
  Pipeline --> Domain["Domain Services"]
  Pipeline --> ProviderPort["PerceptionProvider Port"]
  ProviderPort --> Mock["MockPerceptionProvider"]
  ProviderPort --> OpenAI["OpenAIPerceptionProvider"]
  Pipeline --> RepoPort["ArtifactRepository Port"]
  RepoPort --> LocalJson["Local JSON Artifacts"]
```

```mermaid
flowchart TD
  A["Validate request"] --> B["Validate and normalize images"]
  B --> C["Create content hashes"]
  C --> D["Call perception provider"]
  D --> E["Parse structured response"]
  E --> F["Validate evidence coverage"]
  F --> G["Normalize product profile"]
  G --> H["Generate keyword candidates"]
  H --> I["Normalize and deduplicate"]
  I --> J["Classify intent and category"]
  J --> K["Cluster candidates"]
  K --> L["Score candidates and clusters"]
  L --> M["Persist immutable run artifact"]
  M --> N["Return JSON response"]
```

Domain code does not import FastAPI, OpenAI SDKs, persistence SDKs, or vendor-specific keyword providers. Provider-specific logic lives under `apps/api/src/marketing_agent/infrastructure`.

