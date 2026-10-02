import { useQuery } from "@tanstack/react-query"
import { CardCard, ErrorState, LoadingState } from "."

interface LinkComponentProps {
  to: string
  children: React.ReactNode
  className?: string
}

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
  const {
    data: set,
    isLoading: setLoading,
    error: setError,
  } = useQuery({
    queryKey: ["set", setId],
    queryFn: () => fetchSet(setId),
  })

  const {
    data: cards,
    isLoading: cardsLoading,
    error: cardsError,
  } = useQuery({
    queryKey: ["cards", setId],
    queryFn: () => fetchCards(setId),
    enabled: !!setId,
  })

  if (setLoading || cardsLoading) return <LoadingState message="Loading set details..." />
  if (setError || cardsError) return <ErrorState message="Failed to load set details" />
  if (!set) return <ErrorState message="Set not found" />

  const BackLink = (props: LinkComponentProps) => (
    <a href={props.to} className={props.className}>
      {props.children}
    </a>
  )

  return (
    <div>
      <div className="mb-6">
        <BackLink
          to="/sets"
          className="text-[var(--color-text-muted)] hover:underline mb-4 inline-block"
        >
          ← Back to Sets
        </BackLink>
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
        {cards?.map(card => (
          <CardCard key={card.id} card={card} />
        ))}
      </div>
    </div>
  )
}
