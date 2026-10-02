import { beforeEach, describe, expect, it, vi } from "vitest"

describe("React Query Cache Logic", () => {
  let queryCache: Map<string, { data: unknown; timestamp: number; staleTime: number }>
  const now = () => Date.now()

  beforeEach(() => {
    queryCache = new Map()
  })

  function getQueryKey(key: unknown[]) {
    return JSON.stringify(key)
  }

  function setQueryData(key: unknown[], data: unknown, staleTime = 0) {
    queryCache.set(getQueryKey(key), { data, timestamp: now(), staleTime })
  }

  function getQueryData(key: unknown[]) {
    const entry = queryCache.get(getQueryKey(key))
    if (!entry) return null

    const isStale = now() - entry.timestamp > entry.staleTime
    return { data: entry.data, isStale }
  }

  function invalidateQuery(key: unknown[]) {
    queryCache.delete(getQueryKey(key))
  }

  it("stores and retrieves cached data", () => {
    setQueryData(["user", "1"], { name: "John" })
    const result = getQueryData(["user", "1"])

    expect(result).not.toBeNull()
    expect(result?.data).toEqual({ name: "John" })
    expect(result?.isStale).toBe(true)
  })

  it("respects staleTime", () => {
    setQueryData(["user", "1"], { name: "John" }, 5000)
    const result = getQueryData(["user", "1"])

    expect(result).not.toBeNull()
    expect(result?.isStale).toBe(false)
  })

  it("marks data as stale after staleTime expires", () => {
    const originalNow = Date.now
    const mockTime = 1000000
    Date.now = vi.fn(() => mockTime)

    setQueryData(["user", "1"], { name: "John" }, 1000)

    Date.now = vi.fn(() => mockTime + 500)
    let result = getQueryData(["user", "1"])
    expect(result?.isStale).toBe(false)

    Date.now = vi.fn(() => mockTime + 1500)
    result = getQueryData(["user", "1"])
    expect(result?.isStale).toBe(true)

    Date.now = originalNow
  })

  it("invalidates cache", () => {
    setQueryData(["user", "1"], { name: "John" })
    invalidateQuery(["user", "1"])
    const result = getQueryData(["user", "1"])

    expect(result).toBeNull()
  })

  it("handles multiple queries independently", () => {
    setQueryData(["user", "1"], { name: "John" })
    setQueryData(["user", "2"], { name: "Jane" })

    const user1 = getQueryData(["user", "1"])
    const user2 = getQueryData(["user", "2"])

    expect(user1?.data).toEqual({ name: "John" })
    expect(user2?.data).toEqual({ name: "Jane" })

    invalidateQuery(["user", "1"])

    expect(getQueryData(["user", "1"])).toBeNull()
    expect(getQueryData(["user", "2"])).not.toBeNull()
  })
})
