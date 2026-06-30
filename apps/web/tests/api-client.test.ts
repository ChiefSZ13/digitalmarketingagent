import { afterEach, describe, expect, it, vi } from "vitest";
import { createPerceptionRun, saveMarketplaceOverride } from "@/lib/api-client";
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
});
