import { useQuery } from "@tanstack/react-query"
import { ErrorState, LoadingState } from "."

interface LinkComponentProps {
  to: string
  children: React.ReactNode
  className?: string
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
  hp?: string
  types?: string[]
  attacks?: Array<{
    name: string
    cost: string[]
    damage: string
    text: string
  }>
  weaknesses?: Array<{
    type: string
    value: string
  }>
  resistances?: Array<{
    type: string
    value: string
  }>
}

interface CardDetailProps {
  fetchCard: (id: string) => Promise<CardData>
  cardId: string
}

export function CardDetail({ fetchCard, cardId }: CardDetailProps) {
  const {
    data: card,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["card", cardId],
    queryFn: () => fetchCard(cardId),
  })

  if (isLoading) return <LoadingState message="Loading card details..." />
  if (error) return <ErrorState message="Failed to load card details" />
  if (!card) return <ErrorState message="Card not found" />

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
        <div className="flex flex-col md:flex-row gap-6">
          <div className="md:w-1/3">
            {card.images?.large && (
              <img
                src={card.images.large}
                alt={card.name}
                className="w-full rounded-lg shadow-lg"
              />
            )}
          </div>
          <div className="md:w-2/3">
            <h1 className="text-3xl font-bold">{card.name}</h1>
            <div className="flex flex-wrap gap-2 mt-2">
              <span className="px-2 py-1 bg-[var(--color-primary)]/10 text-[var(--color-primary)] rounded text-sm">
                #{card.number}
              </span>
              <span className="px-2 py-1 bg-[var(--color-secondary)]/10 text-[var(--color-secondary)] rounded text-sm">
                {card.rarity ?? "Common"}
              </span>
              {card.set && (
                <BackLink
                  to={`/sets/${card.set.id}`}
                  className="px-2 py-1 bg-[var(--color-border)] rounded text-sm hover:bg-[var(--color-border)]/80"
                >
                  {card.set.name}
                </BackLink>
              )}
            </div>
            {card.hp && <p className="mt-2 text-[var(--color-text-muted)]">HP: {card.hp}</p>}
            {card.types && card.types.length > 0 && (
              <p className="mt-2 text-[var(--color-text-muted)]">Types: {card.types.join(", ")}</p>
            )}
          </div>
        </div>
      </div>

      {card.attacks && card.attacks.length > 0 && (
        <div className="mb-6">
          <h2 className="text-xl font-bold mb-4">Attacks</h2>
          {card.attacks.map(attack => (
            <div
              key={attack.name}
              className="bg-white border border-[var(--color-border)] rounded-lg p-4 mb-2"
            >
              <div className="flex justify-between mb-2">
                <h3 className="font-medium">{attack.name}</h3>
                <span className="text-[var(--color-text-muted)]">{attack.damage}</span>
              </div>
              <p className="text-sm text-[var(--color-text-muted)]">
                Cost: {attack.cost.join(", ")}
              </p>
              <p className="text-sm mt-1">{attack.text}</p>
            </div>
          ))}
        </div>
      )}

      {(card.weaknesses?.length || card.resistances?.length) && (
        <div>
          <h2 className="text-xl font-bold mb-4">Weaknesses & Resistances</h2>
          <div className="grid grid-cols-2 gap-4">
            {card.weaknesses?.map(w => (
              <div
                key={`weakness-${w.type}-${w.value}`}
                className="bg-red-50 border border-red-200 rounded-lg p-3"
              >
                <p className="text-sm text-red-800">
                  Weakness: {w.type} ({w.value})
                </p>
              </div>
            ))}
            {card.resistances?.map(r => (
              <div
                key={`resistance-${r.type}-${r.value}`}
                className="bg-green-50 border border-green-200 rounded-lg p-3"
              >
                <p className="text-sm text-green-800">
                  Resistance: {r.type} ({r.value})
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
