import { useQuery } from "@tanstack/react-query"
import { CardGrid } from "./CardGrid"

interface SetData {
  id: string
  logo_url?: string
  name: string
  series: string
  total_cards?: number
}

interface SetsListProps {
  fetchSets: (skip?: number, limit?: number) => Promise<SetData[]>
}

export function SetsList({ fetchSets }: SetsListProps) {
  const {
    data: sets,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["sets", 0, 100],
    queryFn: () => fetchSets(0, 100),
  })

  if (isLoading) return <LoadingState message="Loading sets..." />
  if (error) return <ErrorState message="Failed to load sets" />

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Pokémon TCG Sets</h1>
      <CardGrid cards={sets ?? []} />
    </div>
  )
}

interface LoadingStateProps {
  message?: string
}

export function LoadingState({ message = "Loading..." }: LoadingStateProps) {
  return (
    <div className="text-center py-8 text-[var(--color-text-muted)]">
      {message}
    </div>
  )
}

interface ErrorStateProps {
  message?: string
}

export function ErrorState({ message = "Failed to load" }: ErrorStateProps) {
  return (
    <div className="text-center py-8 text-[var(--color-text-muted)]">
      {message}
    </div>
  )
}