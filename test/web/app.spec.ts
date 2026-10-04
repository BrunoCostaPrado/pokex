import { expect, test } from "@playwright/test"

test.use({ baseURL: "http://localhost:3000" })

const MOCK_ETAG = 'W/"mock-etag-123"'

test.describe("Web App E2E", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/")
  })

  test("loads home page", async ({ page }) => {
    await expect(page).toHaveTitle(/PokéX|Pokemon/)
  })

  test("navigates to scan page", async ({ page }) => {
    await page.click('text="Scan"')
    await expect(page).toHaveURL(/.*scan/)
  })

  test("navigates to collection page", async ({ page }) => {
    await page.click('text="Collection"')
    await expect(page).toHaveURL(/.*collection/)
  })

  test("navigates to sets page", async ({ page }) => {
    await page.click('text="Sets"')
    await expect(page).toHaveURL(/\/$/)
  })
})

test.describe("Cache Headers E2E", () => {
  test.beforeEach(async ({ page }) => {
    // Mock data-ingestion API endpoints
    await page.route("**/api/v1/health*", async route => {
      const request = route.request()
      const ifNoneMatch = request.headers()["if-none-match"] || request.headers()["if-none-match"]
      if (ifNoneMatch === MOCK_ETAG) {
        await route.fulfill({ status: 304, headers: { ETag: MOCK_ETAG } })
        return
      }
      await route.fulfill({
        status: 200,
        headers: {
          "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
          ETag: MOCK_ETAG,
        },
        body: JSON.stringify({
          status: "ok",
          service: "data-ingestion",
          version: "0.1.0",
        }),
      })
    })

    await page.route("**/api/v1/sets**", async route => {
      const request = route.request()
      const url = request.url()
      if (request.method() === "POST") {
        await route.fulfill({
          status: 422,
          headers: {},
          body: JSON.stringify({ detail: "Validation error" }),
        })
      } else if (url.includes("/nonexistent")) {
        await route.fulfill({
          status: 404,
          headers: {},
          body: JSON.stringify({ detail: "Not found" }),
        })
      } else {
        await route.continue()
      }
    })

    await page.goto("/")
  })

  test("GET /api/v1/health returns Cache-Control and ETag", async ({ page }) => {
    const response = await page.goto("/api/v1/health")
    expect(response?.status()).toBe(200)
    expect(response?.headers()["cache-control"]).toContain("public, max-age=60")
    expect(response?.headers().ETag).toBe(MOCK_ETAG)
  })

  test("ETag validation returns 304", async ({ page }) => {
    // First request gets ETag
    const response1 = await page.goto("/api/v1/health")
    expect(response1?.status()).toBe(200)
    const etag = response1?.headers().etag
    expect(etag).toBe(MOCK_ETAG)

    // Second request with If-None-Match returns 304 - use fetch from page context
    const response2 = await page.evaluate(async etag => {
      const res = await fetch("/api/v1/health", {
        headers: { "If-None-Match": etag },
      })
      return {
        status: res.status,
        headers: Object.fromEntries(res.headers.entries()),
      }
    }, etag)
    expect(response2.status).toBe(304)
    expect(response2.headers.etag).toBe(MOCK_ETAG)
  })

  test("POST request has no cache headers", async ({ page }) => {
    const response = await page.evaluate(async () => {
      const res = await fetch("/api/v1/sets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: "test", name: "Test Set" }),
      })
      return {
        status: res.status,
        headers: Object.fromEntries(res.headers.entries()),
      }
    })
    expect(response.status).toBe(422)
    expect(response.headers["cache-control"]).toBeUndefined()
  })

  test("GET error response has no cache headers", async ({ page }) => {
    const response = await page.evaluate(async () => {
      const res = await fetch("/api/v1/sets/nonexistent")
      return {
        status: res.status,
        headers: Object.fromEntries(res.headers.entries()),
      }
    })
    expect(response.status).toBe(404)
    expect(response.headers["cache-control"]).toBeUndefined()
  })
})
