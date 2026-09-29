import { describe, it, expect, vi, beforeEach } from "vitest";

describe("Cache-Control Headers", () => {
  it("parses public cache directive", () => {
    const header = "public, max-age=60, stale-while-revalidate=300";
    const directives = header.split(",").map((d) => d.trim());

    expect(directives).toContain("public");
    expect(directives.some((d) => d.startsWith("max-age="))).toBe(true);
    expect(directives.some((d) => d.startsWith("stale-while-revalidate="))).toBe(true);
  });

  it("parses private cache directive", () => {
    const header = "private, max-age=60";
    const directives = header.split(",").map((d) => d.trim());

    expect(directives).toContain("private");
    expect(directives).not.toContain("public");
  });

  it("parses no-cache directive", () => {
    const header = "no-cache, no-store, must-revalidate";
    const directives = header.split(",").map((d) => d.trim());

    expect(directives).toContain("no-cache");
    expect(directives).toContain("no-store");
    expect(directives).toContain("must-revalidate");
  });

  it("extracts max-age value", () => {
    const header = "public, max-age=60, stale-while-revalidate=300";
    const maxAgeMatch = header.match(/max-age=(\d+)/);

    expect(maxAgeMatch).not.toBeNull();
    expect(parseInt(maxAgeMatch![1], 10)).toBe(60);
  });

  it("extracts stale-while-revalidate value", () => {
    const header = "public, max-age=60, stale-while-revalidate=300";
    const swrMatch = header.match(/stale-while-revalidate=(\d+)/);

    expect(swrMatch).not.toBeNull();
    expect(parseInt(swrMatch![1], 10)).toBe(300);
  });

  it("handles missing optional directives", () => {
    const header = "public, max-age=60";
    const swrMatch = header.match(/stale-while-revalidate=(\d+)/);

    expect(swrMatch).toBeNull();
  });
});

describe("ETag Validation", () => {
  it("generates weak ETag", () => {
    const content = JSON.stringify({ data: "test" });
    const etag = `W/"${hash(content)}"`;

    expect(etag).toMatch(/^W\/".*"$/);
  });

  it("matches identical ETags", () => {
    const content = JSON.stringify({ data: "test" });
    const etag1 = `W/"${hash(content)}"`;
    const etag2 = `W/"${hash(content)}"`;

    expect(etag1).toBe(etag2);
  });

  it("detects different ETags", () => {
    const etag1 = `W/"${hash("content1")}"`;
    const etag2 = `W/"${hash("content2")}"`;

    expect(etag1).not.toBe(etag2);
  });

  it("validates If-None-Match header", () => {
    const content = JSON.stringify({ data: "test" });
    const etag = `W/"${hash(content)}"`;
    const ifNoneMatch = etag;

    expect(ifNoneMatch === etag).toBe(true);
  });
});

function hash(input: string): string {
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    const char = input.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash |= 0;
  }
  return Math.abs(hash).toString(16);
}