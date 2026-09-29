import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { CardGrid } from "./CardGrid"

interface CardData {
  id: string
  name: string
  number: string
  rarity?: string
  images?: {
    small?: string
    large?: string
  }
  set?: {
    id: string
    name: string
  }
}

interface CollectionProps {
  fetchCollection: () => Promise<CardData[]>
}

export function Collection({ fetchCollection }: CollectionProps) {
  const { data: cards, isLoading, error } = useQuery({
    queryKey: ["collection"],
    queryFn: fetchCollection,
  })

  if (isLoading) return <LoadingState message="Loading collection..." />
  if (error) return <ErrorState message="Failed to load collection" />

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">My Collection</h1>
      {cards?.length === 0 ? (
        <div className="text-center py-12 text-[var(--color-text-muted)]">
          <p className="text-xl mb-2">No cards in collection yet</p>
          <Link to="/sets" className="text-[var(--color-primary)] hover:underline">
            Browse sets to add cards
          </Link>
        </div>
      ) : (
        <CardGrid cards={cards ?? []} LinkComponent={Link} />
      )}
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