import { Collection } from "@pokex/ui"
import { invoke } from "@tauri-apps/api/core"
import { Link } from "wouter"
import type { Card, CollectionCard } from "../types/tauri"

function CollectionLink({ to, children }: { to: string; children: React.ReactNode }) {
  return <Link href={to}>{children}</Link>
}

export function CollectionPage() {
  const fetchCollection = async () => {
    const [collectionCards, allCards] = await Promise.all([
      invoke<CollectionCard[]>("db_collection_get"),
      invoke<Card[]>("db_get_cards", { limit: 1000, offset: 0 }),
    ])
    const cardsMap = new Map<string, Card>(allCards.map(c => [c.id, c]))

    return collectionCards
      .map(cc => {
        const card = cardsMap.get(cc.card_id)
        if (!card) return null
        return {
          id: card.id,
          name: card.name,
          number: card.number,
          rarity: card.rarity,
          images: card.images,
          set: card.set_id ? { id: card.set_id, name: card.set_id } : undefined,
          hp: card.hp?.toString(),
          types: card.types,
        }
      })
      .filter((c): c is NonNullable<typeof c> => c !== null)
  }

  return <Collection fetchCollection={fetchCollection} LinkComponent={CollectionLink} />
}
