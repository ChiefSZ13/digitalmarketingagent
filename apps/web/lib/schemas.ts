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
  provider: z.string().nullable().optional(),
  platform: z.string().nullable().optional(),
  listing_id: z.string().nullable().optional(),
  field_name: z.string().nullable().optional(),
  observed_value: z.unknown().nullable().optional(),
  observed_at: z.string().nullable().optional(),
  provider_run_id: z.string().nullable().optional(),
  normalization_version: z.string().nullable().optional(),
  matcher_version: z.string().nullable().optional(),
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
  marketing_term_type: z.string().optional().default("search_query"),
  query_family: z.string().optional().default("generic_product"),
  intent: z.string(),
  category: z.string(),
  rationale: z.string(),
  source: z.string(),
  evidence_ids: z.array(z.string()),
  relevance_score: z.number(),
  confidence_score: z.number(),
  generation_confidence: z.number().optional().default(0),
  product_relevance_score: z.number().optional().default(0),
  query_realism_score: z.number().optional().default(0),
  specificity_score: z.number().optional().default(0),
  commercial_intent_score: z.number().optional().default(0),
  source_concepts: z.array(z.string()).optional().default([]),
  origin: z.string().optional().default("deterministic_search_query_generator"),
  origins: z.array(z.string()).optional().default(["model_generated"]),
  rejection_reasons: z.array(z.string()).optional().default([]),
  eligible_for_live_enrichment: z.boolean().optional().default(false),
  generator_version: z.string().optional().default("search-query-generator-v1"),
  score_components: z.object({
    product_match: z.number(),
    intent_value: z.number(),
    evidence_strength: z.number(),
    audience_fit: z.number(),
    specificity: z.number(),
    risk_penalty: z.number(),
  }),
  market_signal_score: z.number().nullable().optional().default(null),
  opportunity_score: z.number().nullable().optional().default(null),
  opportunity_components: z
    .object({
      product_relevance: z.number(),
      market_demand: z.number().nullable(),
      competition_advantage: z.number().nullable(),
      commercial_intent: z.number(),
      cpc_efficiency: z.number().nullable(),
      trend_signal: z.number().nullable(),
      data_completeness: z.number(),
      risk_penalty: z.number(),
    })
    .nullable()
    .optional()
    .default(null),
  scoring_policy_version: z
    .string()
    .optional()
    .default("keyword-opportunity-v1"),
  risk_flags: z.array(z.string()),
  enrichment: z.object({
    average_monthly_searches: z.number().nullable(),
    competition_level: z.string().nullable(),
    cpc_low: z.number().nullable(),
    cpc_high: z.number().nullable(),
    trend: z.string().nullable(),
    source_confidence: z.number().nullable(),
    provider: z.string().nullable().optional().default(null),
    provider_record_id: z.string().nullable().optional().default(null),
    provider_match_type: z.string().nullable().optional().default(null),
    provider_match_confidence: z.number().nullable().optional().default(null),
    matched_provider_term: z.string().nullable().optional().default(null),
    market: z.string().nullable().optional().default(null),
    language: z.string().nullable().optional().default(null),
    currency: z.string().nullable().optional().default(null),
    retrieved_at: z.string().nullable().optional().default(null),
  }),
});

export const keywordMonthlyMetricSchema = z.object({
  year: z.number(),
  month: z.number(),
  searches: z.number(),
});

export const keywordMarketMetricsSchema = z.object({
  provider: z.string(),
  provider_record_id: z.string().nullable(),
  keyword: z.string(),
  matched_provider_term: z.string(),
  provider_match_type: z.string(),
  provider_match_confidence: z.number(),
  average_monthly_searches: z.number().nullable(),
  competition: z.string().nullable(),
  competition_index: z.number().nullable().optional().default(null),
  cpc_low: z.number().nullable(),
  cpc_high: z.number().nullable(),
  currency: z.string().nullable(),
  monthly_history: z.array(keywordMonthlyMetricSchema),
  trend_direction: z.string(),
  trend_strength: z.number().nullable(),
  trend_explanation: z.string().nullable(),
  market: z.string(),
  language: z.string(),
  retrieved_at: z.string(),
  source_confidence: z.number().nullable(),
});

export const keywordOpportunityComponentsSchema = z.object({
  product_relevance: z.number(),
  market_demand: z.number().nullable(),
  competition_advantage: z.number().nullable(),
  commercial_intent: z.number(),
  cpc_efficiency: z.number().nullable(),
  trend_signal: z.number().nullable(),
  data_completeness: z.number(),
  risk_penalty: z.number(),
});

export const keywordIntelligenceKeywordSchema = z.object({
  text: z.string(),
  normalized_text: z.string(),
  origins: z.array(z.string()),
  intent: z.string(),
  category: z.string(),
  query_family: z.string(),
  product_relevance_score: z.number(),
  confidence_score: z.number(),
  market_signal_score: z.number().nullable(),
  opportunity_score: z.number().nullable(),
  opportunity_components: keywordOpportunityComponentsSchema.nullable(),
  scoring_policy_version: z.string(),
  metrics: keywordMarketMetricsSchema.nullable(),
  rationale: z.string(),
  evidence_ids: z.array(z.string()),
  risk_flags: z.array(z.string()),
  source: z.string(),
  related_to: z.string().nullable(),
});

export const keywordIntelligenceClusterSchema = z.object({
  id: z.string(),
  theme: z.string(),
  primary_keyword: z.string(),
  member_keywords: z.array(z.string()),
  dominant_intent: z.string(),
  aggregate_relevance: z.number(),
  aggregate_opportunity: z.number().nullable(),
  keyword_count: z.number(),
});

export const keywordIntelligenceSchema = z.object({
  status: z.string(),
  provider: z.string(),
  market: z.string(),
  language: z.string(),
  collected_at: z.string(),
  keywords: z.array(keywordIntelligenceKeywordSchema),
  clusters: z.array(keywordIntelligenceClusterSchema),
  warnings: z.array(z.string()),
  methodology: z.object({
    scoring_policy_version: z.string(),
    matching_policy_version: z.string(),
    trend_policy_version: z.string(),
    notes: z.array(z.string()),
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
  source_count: z.number(),
  validated_listing_count: z.number(),
  matcher_version: z.string().nullable(),
  confidence: z.number(),
  risk_flags: z.array(z.string()),
});

export const marketplacePriceEstimateSchema = z.object({
  platform: z.string(),
  data_source: z.string(),
  price_low: z.number().nullable(),
  price_median: z.number().nullable(),
  price_high: z.number().nullable(),
  currency: z.string(),
  observed_offer_count: z.number().nullable(),
  source_count: z.number(),
  observation_started_at: z.string().nullable(),
  observation_ended_at: z.string().nullable(),
  aggregation_group: z.string(),
  matcher_version: z.string().nullable(),
  price_basis: z.string(),
  listing_search_phrase: z.string(),
  source_url: z.string().nullable(),
  evidence_ids: z.array(z.string()),
  confidence: z.number(),
  risk_flags: z.array(z.string()),
});

export const productIdentitySchema = z.object({
  brand: z.string().nullable(),
  manufacturer: z.string().nullable(),
  sub_brand: z.string().nullable().optional().default(null),
  product_name: z.string(),
  normalized_product_name: z.string().optional().default(""),
  official_product_line: z.string().nullable().optional().default(null),
  product_type: z.string().nullable(),
  category: z.string().nullable(),
  model_number: z.string().nullable(),
  manufacturer_part_number: z.string().nullable(),
  gtin: z.string().nullable(),
  upc: z.string().nullable(),
  ean: z.string().nullable(),
  isbn: z.string().nullable(),
  asin: z.string().nullable(),
  variant: z.string().nullable(),
  color: z.string().nullable(),
  size: z.string().nullable(),
  material: z.string().nullable(),
  pack_quantity: z.number().nullable(),
  unit_quantity: z.number().nullable(),
  unit_type: z.string().nullable(),
  expected_condition: z.string().nullable(),
  normalized_title: z.string(),
  allowed_brand_aliases: z.array(z.string()).optional().default([]),
  allowed_manufacturer_aliases: z.array(z.string()).optional().default([]),
  official_name_patterns: z.array(z.string()).optional().default([]),
  target_is_official_product: z.boolean().optional().default(false),
  aliases: z.array(z.string()),
  excluded_terms: z.array(z.string()),
  source_evidence: z.array(evidenceRecordSchema),
});

export const normalizedMarketplaceListingSchema = z.object({
  provider: z.string(),
  platform: z.string(),
  listing_id: z.string(),
  source_url: z.string().nullable(),
  title: z.string(),
  normalized_title: z.string(),
  description_excerpt: z.string().nullable(),
  brand: z.string().nullable(),
  provider_brand: z.string().nullable().optional().default(null),
  extracted_title_brand: z.string().nullable().optional().default(null),
  manufacturer: z.string().nullable().optional().default(null),
  product_line: z.string().nullable().optional().default(null),
  model_number: z.string().nullable(),
  manufacturer_part_number: z.string().nullable(),
  gtin: z.string().nullable(),
  upc: z.string().nullable(),
  ean: z.string().nullable(),
  isbn: z.string().nullable(),
  asin: z.string().nullable(),
  product_type: z.string().nullable(),
  category: z.string().nullable(),
  variant: z.string().nullable(),
  color: z.string().nullable(),
  size: z.string().nullable(),
  pack_quantity: z.number().nullable(),
  unit_quantity: z.number().nullable(),
  unit_type: z.string().nullable(),
  condition: z.string().nullable(),
  compatibility_targets: z.array(z.string()).optional().default([]),
  compatibility_phrases: z.array(z.string()).optional().default([]),
  claimed_official: z.boolean().nullable().optional().default(null),
  claimed_licensed: z.boolean().nullable().optional().default(null),
  brand_role: z.string().nullable().optional().default(null),
  item_price: z.number().nullable(),
  shipping_price: z.number().nullable(),
  mandatory_fees: z.number().nullable(),
  discount: z.number().nullable(),
  landed_price: z.number().nullable(),
  currency: z.string().nullable(),
  image_urls: z.array(z.string()),
  seller_name: z.string().nullable(),
  stock_status: z.string().nullable(),
  rating: z.number().nullable(),
  review_count: z.number().nullable(),
  raw_rank_signals: z.array(
    z.object({
      name: z.string(),
      value: z.number(),
      source: z.string().nullable(),
    }),
  ),
  raw_provider_payload_reference: z.string().nullable(),
  observed_at: z.string(),
});

export const matchConflictSchema = z.object({
  code: z.string(),
  field: z.string(),
  expected: z.unknown().nullable(),
  observed: z.unknown().nullable(),
  severity: z.string(),
  explanation: z.string(),
});

export const matchFeatureScoresSchema = z.object({
  identifier_score: z.number().nullable(),
  brand_score: z.number().nullable(),
  brand_owner_score: z.number().nullable().optional().default(null),
  manufacturer_score: z.number().nullable().optional().default(null),
  official_product_line_score: z.number().nullable().optional().default(null),
  compatibility_only_penalty: z.number().nullable().optional().default(null),
  third_party_brand_penalty: z.number().nullable().optional().default(null),
  model_score: z.number().nullable(),
  title_score: z.number(),
  important_token_score: z.number(),
  product_type_score: z.number().nullable(),
  category_score: z.number().nullable(),
  variant_score: z.number().nullable(),
  package_score: z.number().nullable(),
  condition_score: z.number().nullable(),
  image_score: z.number().nullable(),
});

export const officialNameVerificationSchema = z.object({
  official_name_match: z.boolean().nullable(),
  official_product_line_match: z.boolean().nullable(),
  expected_brand_present_as_brand: z.boolean().nullable(),
  expected_brand_present_only_as_compatibility_target: z.boolean(),
  detected_listing_brand: z.string().nullable(),
  detected_manufacturer: z.string().nullable(),
  relationship: z.string(),
  reason_codes: z.array(z.string()),
  conflicts: z.array(matchConflictSchema),
});

export const productMatchResultSchema = z.object({
  listing_id: z.string(),
  status: z.string(),
  relationship: z.string().optional().default("unknown"),
  score: z.number(),
  matched_fields: z.array(z.string()),
  unknown_fields: z.array(z.string()),
  conflicts: z.array(matchConflictSchema),
  feature_scores: matchFeatureScoresSchema,
  official_name_verification: officialNameVerificationSchema
    .nullable()
    .optional()
    .default(null),
  reason_codes: z.array(z.string()),
  human_summary: z.string(),
  eligible_for_price_aggregation: z.boolean(),
  aggregation_group: z.string().nullable(),
  requires_human_review: z.boolean(),
  matcher_version: z.string(),
  created_at: z.string(),
});

export const marketplaceListingValidationSchema = z.object({
  listing: normalizedMarketplaceListingSchema,
  match_result: productMatchResultSchema,
  manual_override: z
    .object({
      run_id: z.string(),
      listing_id: z.string(),
      decision: z.string(),
      note: z.string().nullable(),
      reviewer: z.string(),
      created_at: z.string(),
      updated_at: z.string(),
    })
    .nullable()
    .optional()
    .default(null),
});

export const marketplaceValidationSummarySchema = z.object({
  total_candidates: z.number(),
  exact_match_count: z.number(),
  probable_match_count: z.number(),
  uncertain_count: z.number(),
  rejected_count: z.number(),
  primary_eligible_count: z.number(),
  official_match_count: z.number().optional().default(0),
  official_variant_count: z.number().optional().default(0),
  licensed_alternative_count: z.number().optional().default(0),
  compatible_alternative_count: z.number().optional().default(0),
  accessory_or_replacement_count: z.number().optional().default(0),
  alternate_variant_count: z.number(),
  alternate_package_count: z.number(),
  alternate_condition_count: z.number(),
  matcher_version: z.string(),
  scoring_policy_version: z.string(),
  normalization_version: z.string(),
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
  product_identity: productIdentitySchema.nullable(),
  validation_summary: marketplaceValidationSummarySchema.nullable(),
  validated_listings: z.array(marketplaceListingValidationSchema),
  platform_rankings: z.array(marketplacePlatformEstimateSchema),
  price_estimates: z.array(marketplacePriceEstimateSchema),
  warnings: z.array(z.string()),
  manual_overrides: z
    .array(
      z.object({
        run_id: z.string(),
        listing_id: z.string(),
        decision: z.string(),
        note: z.string().nullable(),
        reviewer: z.string(),
        created_at: z.string(),
        updated_at: z.string(),
      }),
    )
    .optional()
    .default([]),
  overall_confidence: z.number(),
});

export const providerRunTelemetrySchema = z.object({
  provider: z.string(),
  operation: z.string(),
  started_at: z.string(),
  completed_at: z.string(),
  latency_ms: z.number(),
  status: z.string(),
  result_count: z.number(),
  cache_status: z.string(),
  cost_micros: z.number().nullable(),
  error_category: z.string().nullable(),
  correlation_id: z.string(),
});

export const perceptionRunSchema = z.object({
  schema_version: z.string(),
  run_id: z.string(),
  analysis_run_id: z.string().nullable().optional().default(null),
  created_at: z.string(),
  completed_at: z.string().nullable(),
  request: z.record(z.unknown()),
  images: z.array(z.record(z.unknown())),
  product_profile: productProfileSchema,
  marketplace_snapshot: marketplaceSnapshotSchema,
  keyword_candidates: z.array(keywordCandidateSchema),
  keyword_clusters: z.array(keywordClusterSchema),
  keyword_intelligence: keywordIntelligenceSchema.optional().default({
    status: "skipped",
    provider: "none",
    market: "US",
    language: "en",
    collected_at: "1970-01-01T00:00:00.000Z",
    keywords: [],
    clusters: [],
    warnings: [],
    methodology: {
      scoring_policy_version: "keyword-opportunity-v1",
      matching_policy_version: "keyword-provider-match-v1",
      trend_policy_version: "keyword-trend-v1",
      notes: [],
    },
  }),
  warnings: z.array(z.string()),
  errors: z.array(z.string()),
  stage_statuses: z.array(z.record(z.unknown())),
  metadata: z.record(z.unknown()),
  provider_runs: z.array(providerRunTelemetrySchema).optional().default([]),
});

export const analysisSummarySchema = z.object({
  analysis_id: z.string(),
  run_id: z.string(),
  created_at: z.string(),
  completed_at: z.string().nullable(),
  product_name: z.string().nullable(),
  brand: z.string().nullable(),
  status: z.string(),
  marketplace_observation_count: z.number(),
  validated_match_count: z.number(),
  keyword_count: z.number(),
  provider_status: z.string(),
  duration_ms: z.number().nullable(),
});

export const analysisListResponseSchema = z.object({
  items: z.array(analysisSummarySchema),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

export const persistedProviderRunSchema = z.object({
  id: z.string(),
  provider_name: z.string(),
  provider_type: z.string(),
  operation: z.string(),
  status: z.string(),
  result_count: z.number().nullable(),
  started_at: z.string(),
  completed_at: z.string().nullable(),
  latency_ms: z.number().nullable(),
  estimated_cost_usd: z.number().nullable(),
  actual_cost_usd: z.number().nullable(),
  error_type: z.string().nullable(),
  error_message: z.string().nullable(),
  correlation_id: z.string().nullable(),
});

export const persistedMarketplaceObservationSchema = z.object({
  id: z.string(),
  provider_name: z.string(),
  platform: z.string(),
  listing_id: z.string(),
  source_url: z.string().nullable(),
  title: z.string(),
  normalized_title: z.string(),
  brand: z.string().nullable(),
  manufacturer: z.string().nullable(),
  model_number: z.string().nullable(),
  condition: z.string().nullable(),
  currency: z.string().nullable(),
  item_price: z.number().nullable(),
  landed_price: z.number().nullable(),
  observed_at: z.string(),
});

export const persistedMatchResultSchema = z.object({
  id: z.string(),
  marketplace_observation_id: z.string(),
  status: z.string(),
  relationship: z.string(),
  score: z.number(),
  eligible_for_price_aggregation: z.boolean(),
  aggregation_group: z.string().nullable(),
  human_summary: z.string(),
  matcher_version: z.string(),
  created_at: z.string(),
});

export const persistedManualOverrideSchema = z.object({
  id: z.string(),
  marketplace_observation_id: z.string(),
  listing_id: z.string(),
  override_status: z.string(),
  override_relationship: z.string().nullable(),
  override_eligible_for_price_aggregation: z.boolean().nullable(),
  reason: z.string().nullable(),
  created_by: z.string().nullable(),
  created_at: z.string(),
});

export const analysisDetailSchema = z.object({
  summary: analysisSummarySchema,
  product_profile: productProfileSchema.nullable(),
  marketplace_snapshot: marketplaceSnapshotSchema.nullable(),
  keyword_candidates: z.array(keywordCandidateSchema),
  keyword_intelligence: keywordIntelligenceSchema.nullable(),
  provider_runs: z.array(persistedProviderRunSchema),
  marketplace_observations: z.array(persistedMarketplaceObservationSchema),
  match_results: z.array(persistedMatchResultSchema),
  manual_overrides: z.array(persistedManualOverrideSchema),
  report: perceptionRunSchema.nullable(),
});

export const adminDbTableSummarySchema = z.object({
  name: z.string(),
  columns: z.array(z.string()),
  record_count: z.number().nullable(),
});

export const adminDbTableListResponseSchema = z.object({
  tables: z.array(adminDbTableSummarySchema),
});

export const adminDbTableRowsResponseSchema = z.object({
  table_name: z.string(),
  columns: z.array(z.string()),
  rows: z.array(z.record(z.unknown())),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
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
export type KeywordIntelligence = z.infer<typeof keywordIntelligenceSchema>;
export type KeywordIntelligenceKeyword = z.infer<
  typeof keywordIntelligenceKeywordSchema
>;
export type MarketplacePlatformEstimate = z.infer<
  typeof marketplacePlatformEstimateSchema
>;
export type MarketplacePriceEstimate = z.infer<
  typeof marketplacePriceEstimateSchema
>;
export type MarketplaceListingValidation = z.infer<
  typeof marketplaceListingValidationSchema
>;
export type MarketplaceSnapshot = z.infer<typeof marketplaceSnapshotSchema>;
export type PerceptionRun = z.infer<typeof perceptionRunSchema>;
export type AnalysisFormValues = z.infer<typeof analysisFormSchema>;
export type AnalysisSummary = z.infer<typeof analysisSummarySchema>;
export type AnalysisListResponse = z.infer<typeof analysisListResponseSchema>;
export type AnalysisDetail = z.infer<typeof analysisDetailSchema>;
export type PersistedProviderRun = z.infer<typeof persistedProviderRunSchema>;
export type PersistedMarketplaceObservation = z.infer<
  typeof persistedMarketplaceObservationSchema
>;
export type PersistedManualOverride = z.infer<
  typeof persistedManualOverrideSchema
>;
export type AdminDbTableSummary = z.infer<typeof adminDbTableSummarySchema>;
export type AdminDbTableListResponse = z.infer<
  typeof adminDbTableListResponseSchema
>;
export type AdminDbTableRowsResponse = z.infer<
  typeof adminDbTableRowsResponseSchema
>;
