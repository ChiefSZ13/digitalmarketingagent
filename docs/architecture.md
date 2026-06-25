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
  Pipeline --> MarketPort["MarketplaceDataProvider Port"]
  MarketPort --> MockMarket["Mock Marketplace Provider"]
  MarketPort --> SerpApi["SerpAPI Google Shopping Provider"]
  MarketPort --> Matcher["Deterministic Product Matcher"]
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
  G --> H["Build marketplace search query"]
  H --> I["Fetch raw provider listings"]
  I --> J["Normalize marketplace listings"]
  J --> K["Run hard product-validation rules"]
  K --> L["Score deterministic match features"]
  L --> M["Classify accepted, review, rejected, and alternate listings"]
  M --> N["Aggregate validated primary marketplace facts"]
  N --> O["Generate keyword candidates"]
  O --> P["Normalize and deduplicate"]
  P --> Q["Classify intent and category"]
  Q --> R["Cluster candidates"]
  R --> S["Score candidates and clusters"]
  S --> T["Persist immutable run artifact"]
  T --> U["Return JSON response"]
```

Domain code does not import FastAPI, OpenAI SDKs, persistence SDKs, or vendor-specific keyword providers. Provider-specific logic lives under `apps/api/src/marketing_agent/infrastructure`.

Marketplace matching is deterministic-first. The provider adapters convert vendor
payloads into `NormalizedMarketplaceListing` records, then the domain matcher
compares them with a canonical `ProductIdentity`. LLM ambiguity review is
reserved behind disabled configuration and is not required for the pipeline.
Hard identifier, model, brand, accessory, and condition conflicts cannot be
overridden by similarity scoring.
