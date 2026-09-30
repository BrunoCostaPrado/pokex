import { CardCard } from "./CardCard"

interface CardLike {
  id: string
  logo_url?: string
  images?: { small?: string; large?: string }
  name: string
  series?: string
  set?: { name: string }
  total_cards?: number
  number?: string
  rarity?: string
}

interface LinkComponentProps {
  to: string
  children: React.ReactNode
  className?: string
}

interface CardGridProps {
  cards: CardLike[]
  LinkComponent?: React.ComponentType<LinkComponentProps>
}

export function CardGrid({ cards, LinkComponent }: CardGridProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {cards.map(card => (
        <CardCard key={card.id} card={card} LinkComponent={LinkComponent} />
      ))}
    </div>
  )
}
