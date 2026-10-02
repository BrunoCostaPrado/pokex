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

interface CardCardProps {
  card: CardLike
  to?: string
}

export function CardCard({ card, to }: CardCardProps) {
  const href =
    to ??
    (card.set
      ? `/sets/${card.set.name.toLowerCase().replace(/\s+/g, "-")}/${card.id}`
      : `/cards/${card.id}`)
  const imageUrl = card.logo_url ?? card.images?.small
  const seriesText = card.series ?? card.set?.name ?? "Unknown"
  const extraText = card.total_cards
    ? ` — ${card.total_cards} cards`
    : card.number
      ? ` — #${card.number} · ${card.rarity ?? "Common"}`
      : ""

  const cardContent = (
    <>
      {imageUrl && (
        <img src={imageUrl} alt={card.name} className="w-full h-24 object-contain mb-2" />
      )}
      <h3 className="font-medium text-sm">{card.name}</h3>
      <p className="text-xs text-[var(--color-text-muted)]">
        {seriesText}
        {extraText}
      </p>
    </>
  )

  return (
    <a
      href={href}
      className="block bg-[var(--color-surface)] rounded-lg border border-[var(--color-border)] p-4 hover:shadow-md transition-shadow"
    >
      {cardContent}
    </a>
  )
}
