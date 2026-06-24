import { z } from "zod";

export const problemDetailsSchema = z.object({
  type: z.string(),
  title: z.string(),
  status: z.number(),
  detail: z.string(),
  instance: z.string(),
  request_id: z.string(),
});

export const evidenceLinkedTextSchema = z.object({
  value: z.string(),
  evidence_ids: z.array(z.string()),
  confidence: z.number(),
});

export const evidenceRecordSchema = z.object({
  id: z.string(),
  source: z.string(),
  source_reference: z.string(),
  observation: z.string(),
  quote: z.string().nullable(),
  confidence: z.number(),
  created_at: z.string(),
});

export const claimFlagSchema = z.object({
  claim: z.string(),
  reason: z.string(),
  severity: z.string(),
  evidence_ids: z.array(z.string()),
});

export const productProfileSchema = z.object({
  product_name: evidenceLinkedTextSchema.nullable(),
  brand: evidenceLinkedTextSchema.nullable(),
  category: evidenceLinkedTextSchema.nullable(),
  subcategory: evidenceLinkedTextSchema.nullable(),
  marketplace_search_query: evidenceLinkedTextSchema.nullable(),
  summary: evidenceLinkedTextSchema,
  visual_attributes: z.array(evidenceLinkedTextSchema),
  observed_facts: z.array(evidenceLinkedTextSchema),
  user_provided_facts: z.array(evidenceLinkedTextSchema),
  inferred_attributes: z.array(evidenceLinkedTextSchema),
  features: z.array(evidenceLinkedTextSchema),
  benefits: z.array(evidenceLinkedTextSchema),
  materials: z.array(evidenceLinkedTextSchema),
  colors: z.array(evidenceLinkedTextSchema),
  use_cases: z.array(evidenceLinkedTextSchema),
  target_audiences: z.array(evidenceLinkedTextSchema),
  differentiators: z.array(evidenceLinkedTextSchema),
  limitations: z.array(evidenceLinkedTextSchema),
  ambiguities: z.array(evidenceLinkedTextSchema),
  unknowns: z.array(evidenceLinkedTextSchema),
  unsafe_or_unverified_claims: z.array(claimFlagSchema),
  claim_flags: z.array(claimFlagSchema),
  evidence: z.array(evidenceRecordSchema),
  overall_confidence: z.number(),
});

export const keywordCandidateSchema = z.object({
  text: z.string(),
  normalized_text: z.string(),
  intent: z.string(),
  category: z.string(),
  rationale: z.string(),
  source: z.string(),
  evidence_ids: z.array(z.string()),
  relevance_score: z.number(),
  confidence_score: z.number(),
  score_components: z.object({
    product_match: z.number(),
    intent_value: z.number(),
    evidence_strength: z.number(),
    audience_fit: z.number(),
    specificity: z.number(),
    risk_penalty: z.number(),
  }),
  risk_flags: z.array(z.string()),
  enrichment: z.object({
    average_monthly_searches: z.number().nullable(),
    competition_level: z.string().nullable(),
    cpc_low: z.number().nullable(),
    cpc_high: z.number().nullable(),
    trend: z.string().nullable(),
    source_confidence: z.number().nullable(),
  }),
});

export const keywordClusterSchema = z.object({
  id: z.string(),
  theme: z.string(),
  primary_keyword: z.string(),
  member_keywords: z.array(z.string()),
  dominant_intent: z.string(),
  category: z.string(),
  aggregate_relevance: z.number(),
  evidence_ids: z.array(z.string()),
  recommended_usage: z.string(),
});

export const marketplacePlatformEstimateSchema = z.object({
  rank: z.number(),
  platform: z.string(),
  platform_type: z.string(),
  data_source: z.string(),
  estimated_sales_potential_score: z.number(),
  observed_offer_count: z.number().nullable(),
  observed_review_count: z.number().nullable(),
  observed_units_sold: z.number().nullable(),
  observed_sales_signal: z.string().nullable(),
  sales_rank_basis: z.string(),
  listing_search_phrase: z.string(),
  source_url: z.string().nullable(),
  evidence_ids: z.array(z.string()),
  confidence: z.number(),
  risk_flags: z.array(z.string()),
});

export const marketplacePriceEstimateSchema = z.object({
  platform: z.string(),
  data_source: z.string(),
  price_low: z.number().nullable(),
  price_high: z.number().nullable(),
  currency: z.string(),
  observed_offer_count: z.number().nullable(),
  price_basis: z.string(),
  listing_search_phrase: z.string(),
  source_url: z.string().nullable(),
  evidence_ids: z.array(z.string()),
  confidence: z.number(),
  risk_flags: z.array(z.string()),
});

export const marketplaceSnapshotSchema = z.object({
  title: z.string(),
  summary: z.string(),
  source_provider: z.string(),
  source_query: z.string(),
  retrieved_at: z.string(),
  is_live_data: z.boolean(),
  methodology: z.string(),
  limitations: z.array(z.string()),
  platform_rankings: z.array(marketplacePlatformEstimateSchema),
  price_estimates: z.array(marketplacePriceEstimateSchema),
  warnings: z.array(z.string()),
  overall_confidence: z.number(),
});

export const perceptionRunSchema = z.object({
  schema_version: z.string(),
  run_id: z.string(),
  created_at: z.string(),
  completed_at: z.string().nullable(),
  request: z.record(z.unknown()),
  images: z.array(z.record(z.unknown())),
  product_profile: productProfileSchema,
  marketplace_snapshot: marketplaceSnapshotSchema,
  keyword_candidates: z.array(keywordCandidateSchema),
  keyword_clusters: z.array(keywordClusterSchema),
  warnings: z.array(z.string()),
  errors: z.array(z.string()),
  stage_statuses: z.array(z.record(z.unknown())),
  metadata: z.record(z.unknown()),
});

export const analysisFormSchema = z.object({
  access_key: z.string().optional(),
  description: z.string().trim().min(1, "Description is required."),
  brand: z.string().optional(),
  market: z.string().optional(),
  language: z.string().optional(),
  category_hint: z.string().optional(),
  target_audience_hint: z.string().optional(),
});

export type ProblemDetails = z.infer<typeof problemDetailsSchema>;
export type EvidenceLinkedText = z.infer<typeof evidenceLinkedTextSchema>;
export type EvidenceRecord = z.infer<typeof evidenceRecordSchema>;
export type ClaimFlag = z.infer<typeof claimFlagSchema>;
export type ProductProfile = z.infer<typeof productProfileSchema>;
export type KeywordCandidate = z.infer<typeof keywordCandidateSchema>;
export type KeywordCluster = z.infer<typeof keywordClusterSchema>;
export type MarketplacePlatformEstimate = z.infer<
  typeof marketplacePlatformEstimateSchema
>;
export type MarketplacePriceEstimate = z.infer<
  typeof marketplacePriceEstimateSchema
>;
export type MarketplaceSnapshot = z.infer<typeof marketplaceSnapshotSchema>;
export type PerceptionRun = z.infer<typeof perceptionRunSchema>;
export type AnalysisFormValues = z.infer<typeof analysisFormSchema>;
