import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"

interface SetData {
  id: string
  name: string
  series: string
  total_cards?: number
  logo_url?: string
  release_date?: string
}

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

interface SetDetailProps {
  fetchSet: (id: string) => Promise<SetData>
  fetchCards: (setId: string) => Promise<CardData[]>
  setId: string
}

export function SetDetail({ fetchSet, fetchCards, setId }: SetDetailProps) {
  const { data: set, isLoading: setLoading, error: setError } = useQuery({
    queryKey: ["set", setId],
    queryFn: () => fetchSet(setId),
  })

  const { data: cards, isLoading: cardsLoading, error: cardsError } = useQuery({
    queryKey: ["cards", setId],
    queryFn: () => fetchCards(setId),
    enabled: !!setId,
  })

  if (setLoading || cardsLoading) return <LoadingState message="Loading set details..." />
  if (setError || cardsError) return <ErrorState message="Failed to load set details" />
  if (!set) return <ErrorState message="Set not found" />

  return (
    <div>
      <div className="mb-6">
        <Link to="/sets" className="text-[var(--color-text-muted)] hover:underline mb-4 inline-block">
          ← Back to Sets
        </Link>
        <div className="flex items-start gap-4">
          {set.logo_url && (
            <img src={set.logo_url} alt={set.name} className="w-32 h-32 object-contain" />
          )}
          <div>
            <h1 className="text-3xl font-bold">{set.name}</h1>
            <p className="text-[var(--color-text-muted)]">{set.series}</p>
            <p className="text-sm text-[var(--color-text-muted)]">
              {set.total_cards ?? "?"} cards · Released {set.release_date ?? "Unknown"}
            </p>
          </div>
        </div>
      </div>

      <h2 className="text-xl font-bold mb-4">Cards</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {cards?.map((card) => (
          <Link key={card.id} to={`/cards/${card.id}`} className="block bg-white rounded-lg border border-[var(--color-border)] p-4 hover:shadow-md transition-shadow">
            {card.images?.small && (
              <img src={card.images.small} alt={card.name} className="w-full h-32 object-contain mb-2" />
            )}
            <h3 className="font-medium text-sm">{card.name}</h3>
            <p className="text-xs text-[var(--color-text-muted)]">#{card.number} · {card.rarity ?? "Common"}</p>
          </Link>
        ))}
      </div>
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