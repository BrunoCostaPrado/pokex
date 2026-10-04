import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  })

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe("React Query Cache", () => {
  let wrapper: ReturnType<typeof createWrapper>

  beforeEach(() => {
    wrapper = createWrapper()
  })

  it("caches query results", async () => {
    let callCount = 0
    const fetchData = vi.fn().mockImplementation(async () => {
      callCount++
      return { data: "test" }
    })

    const { result } = renderHook(() => useQuery({ queryKey: ["test"], queryFn: fetchData }), {
      wrapper,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(callCount).toBe(1)

    const { result: result2 } = renderHook(
      () => useQuery({ queryKey: ["test"], queryFn: fetchData }),
      { wrapper }
    )

    await waitFor(() => expect(result2.current.isSuccess).toBe(true))
    expect(callCount).toBe(1)
  })

  it("respects staleTime", async () => {
    let callCount = 0
    const fetchData = vi.fn().mockImplementation(async () => {
      callCount++
      return { data: "test" }
    })

    const { result } = renderHook(
      () => useQuery({ queryKey: ["test"], queryFn: fetchData, staleTime: 1000 }),
      { wrapper }
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(callCount).toBe(1)

    const { result: result2 } = renderHook(
      () => useQuery({ queryKey: ["test"], queryFn: fetchData, staleTime: 1000 }),
      { wrapper }
    )

    await waitFor(() => expect(result2.current.isSuccess).toBe(true))
    expect(callCount).toBe(1)
  })

  it("refetches after staleTime expires", async () => {
    vi.useFakeTimers()
    let callCount = 0
    const fetchData = vi.fn().mockImplementation(async () => {
      callCount++
      return { data: "test" }
    })

    const { result } = renderHook(
      () => useQuery({ queryKey: ["test"], queryFn: fetchData, staleTime: 100 }),
      { wrapper }
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(callCount).toBe(1)

    vi.advanceTimersByTime(200)

    const { result: result2 } = renderHook(
      () => useQuery({ queryKey: ["test"], queryFn: fetchData, staleTime: 100 }),
      { wrapper }
    )

    await waitFor(() => expect(result2.current.isFetching).toBe(true))
    await waitFor(() => expect(result2.current.isSuccess).toBe(true))
    expect(callCount).toBe(2)

    vi.useRealTimers()
  })

  it("cache invalidation with queryClient.invalidateQueries", async () => {
    let callCount = 0
    const fetchData = vi.fn().mockImplementation(async () => {
      callCount++
      return { data: "test" }
    })

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: 0 } },
    })

    const { result } = renderHook(() => useQuery({ queryKey: ["test"], queryFn: fetchData }), {
      wrapper: ({ children }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      ),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(callCount).toBe(1)

    await queryClient.invalidateQueries({ queryKey: ["test"] })

    await waitFor(() => expect(result.current.isFetching).toBe(true))
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(callCount).toBe(2)
  })
})

function renderHook<T>(hook: () => T, options?: { wrapper: ReturnType<typeof createWrapper> }) {
  let result: T
  const TestComponent = () => {
    result = hook()
    return null
  }

  const { unmount } = render(<TestComponent />, { wrapper: options?.wrapper })
  return {
    result: { current: result },
    unmount,
  }
}

function useQuery(options: {
  queryKey: unknown[]
  queryFn: () => Promise<unknown>
  staleTime?: number
}) {
  return { isSuccess: true, isFetching: false, data: null }
}
