import {
  adminDbTableListResponseSchema,
  adminDbTableRowsResponseSchema,
  analysisDetailSchema,
  analysisListResponseSchema,
  type AnalysisFormValues,
  type AnalysisDetail,
  type AnalysisListResponse,
  type AdminDbTableListResponse,
  type AdminDbTableRowsResponse,
  type PerceptionRun,
  type ProblemDetails,
  perceptionRunSchema,
  problemDetailsSchema,
} from "./schemas";

export type MarketplaceReviewDecision =
  | "official_match"
  | "official_variant"
  | "licensed_alternative"
  | "compatible_alternative"
  | "rejected"
  | "alternate_package";

export class ApiProblemError extends Error {
  problem: ProblemDetails;

  constructor(problem: ProblemDetails) {
    super(problem.detail);
    this.name = "ApiProblemError";
    this.problem = problem;
  }
}

export async function createPerceptionRun(
  values: AnalysisFormValues,
  images: File[],
): Promise<PerceptionRun> {
  if (process.env.NEXT_PUBLIC_USE_FIXTURES === "true") {
    await new Promise((resolve) => setTimeout(resolve, 250));
    const response = await fetch("/fixtures/mock-run.json");
    return perceptionRunSchema.parse(await response.json());
  }

  const formData = new FormData();
  images.forEach((image) => formData.append("images", image));
  Object.entries(values).forEach(([key, value]) => {
    if (key !== "access_key" && value) {
      formData.append(key, value);
    }
  });

  const baseUrl = apiBaseUrl();
  const accessKey = values.access_key?.trim();
  const response = await fetch(`${baseUrl}/api/v1/perception-runs`, {
    method: "POST",
    headers: accessKey ? { "X-App-Access-Key": accessKey } : undefined,
    body: formData,
  });
  const payload = await response.json();
  if (!response.ok) {
    const parsed = problemDetailsSchema.safeParse(payload);
    if (parsed.success) {
      throw new ApiProblemError(parsed.data);
    }
    throw new Error("Analysis request failed.");
  }
  return perceptionRunSchema.parse(payload);
}

export async function saveMarketplaceOverride({
  runId,
  listingId,
  decision,
  accessKey,
}: {
  runId: string;
  listingId: string;
  decision: MarketplaceReviewDecision;
  accessKey?: string;
}): Promise<void> {
  if (process.env.NEXT_PUBLIC_USE_FIXTURES === "true") {
    await new Promise((resolve) => setTimeout(resolve, 100));
    return;
  }

  const baseUrl = apiBaseUrl();
  const response = await fetch(
    `${baseUrl}/api/v1/perception-runs/${runId}/marketplace-overrides`,
    {
      method: "POST",
      headers: {
        "content-type": "application/json",
        ...(accessKey ? { "X-App-Access-Key": accessKey } : {}),
      },
      body: JSON.stringify({
        listing_id: listingId,
        decision,
      }),
    },
  );
  const payload = await response.json();
  if (!response.ok) {
    const parsed = problemDetailsSchema.safeParse(payload);
    if (parsed.success) {
      throw new ApiProblemError(parsed.data);
    }
    throw new Error("Marketplace override request failed.");
  }
}

export async function listAnalyses({
  accessKey,
  limit = 20,
  offset = 0,
  search,
}: {
  accessKey?: string;
  limit?: number;
  offset?: number;
  search?: string;
} = {}): Promise<AnalysisListResponse> {
  if (process.env.NEXT_PUBLIC_USE_FIXTURES === "true") {
    const fixture = await fixtureRun();
    return {
      items: [
        {
          analysis_id: fixture.analysis_run_id ?? fixture.run_id,
          run_id: fixture.run_id,
          created_at: fixture.created_at,
          completed_at: fixture.completed_at,
          product_name: fixture.product_profile.product_name?.value ?? null,
          brand: fixture.product_profile.brand?.value ?? null,
          status: "completed",
          marketplace_observation_count:
            fixture.marketplace_snapshot.validated_listings.length,
          validated_match_count:
            fixture.marketplace_snapshot.validated_listings.length,
          keyword_count: fixture.keyword_candidates.length,
          provider_status: "success",
          duration_ms: fixture.metadata.latency_ms as number | null,
        },
      ],
      total: 1,
      limit,
      offset,
    };
  }

  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  if (search?.trim()) {
    params.set("search", search.trim());
  }
  const response = await fetch(`${apiBaseUrl()}/api/v1/analyses?${params}`, {
    headers: accessHeaders(accessKey),
  });
  return parseResponse(response, analysisListResponseSchema);
}

export async function getAnalysisDetail({
  analysisId,
  accessKey,
}: {
  analysisId: string;
  accessKey?: string;
}): Promise<AnalysisDetail> {
  if (process.env.NEXT_PUBLIC_USE_FIXTURES === "true") {
    const fixture = await fixtureRun();
    return analysisDetailSchema.parse({
      summary: {
        analysis_id: fixture.analysis_run_id ?? fixture.run_id,
        run_id: fixture.run_id,
        created_at: fixture.created_at,
        completed_at: fixture.completed_at,
        product_name: fixture.product_profile.product_name?.value ?? null,
        brand: fixture.product_profile.brand?.value ?? null,
        status: "completed",
        marketplace_observation_count:
          fixture.marketplace_snapshot.validated_listings.length,
        validated_match_count:
          fixture.marketplace_snapshot.validated_listings.length,
        keyword_count: fixture.keyword_candidates.length,
        provider_status: "success",
        duration_ms: (fixture.metadata.latency_ms as number | null) ?? null,
      },
      product_profile: fixture.product_profile,
      marketplace_snapshot: fixture.marketplace_snapshot,
      keyword_candidates: fixture.keyword_candidates,
      keyword_intelligence: fixture.keyword_intelligence,
      provider_runs: fixture.provider_runs.map((run, index) => ({
        id: `fixture-provider-${index}`,
        provider_name: run.provider,
        provider_type: run.operation.includes("keyword")
          ? "keyword"
          : "marketplace",
        operation: run.operation,
        status: run.status,
        result_count: run.result_count,
        started_at: run.started_at,
        completed_at: run.completed_at,
        latency_ms: run.latency_ms,
        estimated_cost_usd: null,
        actual_cost_usd: null,
        error_type: run.error_category,
        error_message: null,
        correlation_id: run.correlation_id,
      })),
      marketplace_observations: [],
      match_results: [],
      manual_overrides: [],
      report: fixture,
    });
  }

  const response = await fetch(
    `${apiBaseUrl()}/api/v1/analyses/${analysisId}`,
    {
      headers: accessHeaders(accessKey),
    },
  );
  return parseResponse(response, analysisDetailSchema);
}

export async function getAnalysisReport({
  analysisId,
  accessKey,
}: {
  analysisId: string;
  accessKey?: string;
}): Promise<PerceptionRun> {
  if (process.env.NEXT_PUBLIC_USE_FIXTURES === "true") {
    return fixtureRun();
  }
  const response = await fetch(
    `${apiBaseUrl()}/api/v1/analyses/${analysisId}/report`,
    { headers: accessHeaders(accessKey) },
  );
  return parseResponse(response, perceptionRunSchema);
}

export async function saveAnalysisObservationOverride({
  analysisId,
  observationId,
  decision,
  reason,
  accessKey,
}: {
  analysisId: string;
  observationId: string;
  decision: MarketplaceReviewDecision;
  reason?: string;
  accessKey?: string;
}): Promise<void> {
  const response = await fetch(
    `${apiBaseUrl()}/api/v1/analyses/${analysisId}/marketplace/${observationId}/override`,
    {
      method: "POST",
      headers: {
        "content-type": "application/json",
        ...accessHeaders(accessKey),
      },
      body: JSON.stringify({
        override_status: decision,
        reason,
      }),
    },
  );
  await parseResponse(response);
}

export async function listAdminDbTables(
  accessKey?: string,
): Promise<AdminDbTableListResponse> {
  const response = await fetch(`${apiBaseUrl()}/admin/db/tables`, {
    headers: accessHeaders(accessKey),
  });
  return parseResponse(response, adminDbTableListResponseSchema);
}

export async function listAdminDbRows({
  tableName,
  accessKey,
  limit = 25,
  offset = 0,
  search,
}: {
  tableName: string;
  accessKey?: string;
  limit?: number;
  offset?: number;
  search?: string;
}): Promise<AdminDbTableRowsResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  if (search?.trim()) {
    params.set("search", search.trim());
  }
  const response = await fetch(
    `${apiBaseUrl()}/admin/db/tables/${tableName}?${params}`,
    { headers: accessHeaders(accessKey) },
  );
  return parseResponse(response, adminDbTableRowsResponseSchema);
}

async function fixtureRun(): Promise<PerceptionRun> {
  const response = await fetch("/fixtures/mock-run.json");
  return perceptionRunSchema.parse(await response.json());
}

function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
}

function accessHeaders(accessKey?: string): HeadersInit | undefined {
  const trimmed = accessKey?.trim();
  return trimmed ? { "X-App-Access-Key": trimmed } : undefined;
}

async function parseResponse<T>(
  response: Response,
  schema?: { parse: (value: unknown) => T },
): Promise<T> {
  const payload = await response.json();
  if (!response.ok) {
    const parsed = problemDetailsSchema.safeParse(payload);
    if (parsed.success) {
      throw new ApiProblemError(parsed.data);
    }
    throw new Error("API request failed.");
  }
  return schema ? schema.parse(payload) : (payload as T);
}
