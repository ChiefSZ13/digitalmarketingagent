import { afterEach, describe, expect, it, vi } from "vitest";
import {
  createPerceptionRun,
  listAdminDbRows,
  listAnalyses,
  saveMarketplaceOverride,
} from "@/lib/api-client";
import fixture from "../public/fixtures/mock-run.json";

describe("createPerceptionRun", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends the access key as a header and not form data", async () => {
    const fetchMock = vi.fn<typeof fetch>(
      async () =>
        new Response(JSON.stringify(fixture), {
          status: 201,
          headers: { "content-type": "application/json" },
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await createPerceptionRun(
      {
        access_key: "secret",
        description: "Portable rechargeable desk lamp",
      },
      [new File(["image"], "lamp.png", { type: "image/png" })],
    );

    const request = fetchMock.mock.calls[0]?.[1];
    expect(request).toBeDefined();
    if (!request) {
      throw new Error("Expected fetch request options.");
    }
    expect(request.headers).toEqual({ "X-App-Access-Key": "secret" });
    expect(request.body).toBeInstanceOf(FormData);
    expect((request.body as FormData).get("access_key")).toBeNull();
    expect((request.body as FormData).get("description")).toBe(
      "Portable rechargeable desk lamp",
    );
  });

  it("saves marketplace overrides with the access key header", async () => {
    const fetchMock = vi.fn<typeof fetch>(
      async () =>
        new Response(
          JSON.stringify({
            run_id: "run_123",
            listing_id: "listing-1",
            decision: "official_match",
            note: null,
            reviewer: "manual",
            created_at: "2026-06-26T00:00:00Z",
            updated_at: "2026-06-26T00:00:00Z",
          }),
          {
            status: 201,
            headers: { "content-type": "application/json" },
          },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await saveMarketplaceOverride({
      runId: "run_123",
      listingId: "listing-1",
      decision: "official_match",
      accessKey: "secret",
    });

    const request = fetchMock.mock.calls[0]?.[1];
    expect(request).toBeDefined();
    if (!request) {
      throw new Error("Expected fetch request options.");
    }
    expect(request.method).toBe("POST");
    expect(request.headers).toEqual({
      "content-type": "application/json",
      "X-App-Access-Key": "secret",
    });
    expect(JSON.parse(String(request.body))).toEqual({
      listing_id: "listing-1",
      decision: "official_match",
    });
  });

  it("lists persisted analyses with access key and search params", async () => {
    const fetchMock = vi.fn<typeof fetch>(
      async () =>
        new Response(
          JSON.stringify({
            items: [
              {
                analysis_id: "analysis-1",
                run_id: "run_123",
                created_at: "2026-06-30T00:00:00Z",
                completed_at: "2026-06-30T00:00:01Z",
                product_name: "Portable lamp",
                brand: "Acme",
                status: "completed",
                marketplace_observation_count: 10,
                validated_match_count: 4,
                keyword_count: 20,
                provider_status: "success",
                duration_ms: 1000,
              },
            ],
            total: 1,
            limit: 10,
            offset: 0,
          }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await listAnalyses({
      accessKey: "secret",
      limit: 10,
      search: "lamp",
    });

    expect(response.items[0]?.analysis_id).toBe("analysis-1");
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain(
      "/api/v1/analyses?limit=10&offset=0&search=lamp",
    );
    expect(fetchMock.mock.calls[0]?.[1]?.headers).toEqual({
      "X-App-Access-Key": "secret",
    });
  });

  it("lists admin database rows with pagination params", async () => {
    const fetchMock = vi.fn<typeof fetch>(
      async () =>
        new Response(
          JSON.stringify({
            table_name: "analysis_runs",
            columns: ["id", "status"],
            rows: [{ id: "analysis-1", status: "completed" }],
            total: 1,
            limit: 25,
            offset: 0,
          }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await listAdminDbRows({
      tableName: "analysis_runs",
      accessKey: "secret",
      search: "completed",
    });

    expect(response.rows[0]?.status).toBe("completed");
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain(
      "/admin/db/tables/analysis_runs?limit=25&offset=0&search=completed",
    );
  });
});
