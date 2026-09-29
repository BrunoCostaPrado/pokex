import { Collection } from "@pokex/ui"
import { tauriCommand } from "../hooks/useTauriQuery"
import type { Card, CollectionCard } from "../types/tauri"

export function CollectionPage() {
  const fetchCollection = async () => {
    const collectionCards = await tauriCommand<CollectionCard[]>("db_collection_get")
    const allCards = await tauriCommand<Card[]>("db_get_cards", { limit: 1000, offset: 0 })
    const cardsMap = new Map<string, Card>(allCards.map((c) => [c.id, c]))

    return collectionCards
      .map((cc) => {
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

  return <Collection fetchCollection={fetchCollection} />
}