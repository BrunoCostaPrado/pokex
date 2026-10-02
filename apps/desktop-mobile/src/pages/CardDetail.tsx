import { CardDetail } from "@pokex/ui"
import { invoke } from "@tauri-apps/api/core"
import { useParams } from "wouter"
import type { Card } from "../types/tauri"

export function CardDetailPage() {
  const params = useParams() as { id: string } | undefined
  const id = params?.id ?? ""

  const fetchCard = async (cardId: string) => {
    const card = await invoke<Card | null>("db_get_card", { id: cardId })
    if (!card) throw new Error("Card not found")
    return {
      id: card.id,
      name: card.name,
      number: card.number,
      rarity: card.rarity,
      images: card.images,
      set: card.set_id ? { id: card.set_id, name: card.set_id } : undefined,
      hp: card.hp?.toString(),
      types: card.types,
      attacks: undefined,
      weaknesses: undefined,
      resistances: undefined,
    }
  }

  return <CardDetail fetchCard={fetchCard} cardId={id} />
}
