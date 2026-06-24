import { afterEach, describe, expect, it, vi } from "vitest";
import { createPerceptionRun } from "@/lib/api-client";
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
});
