import { CardDetail } from "@pokex/ui"
import { useParams } from "react-router-dom"

const BASE = "/api"

async function fetchCard(id: string) {
  const res = await fetch(`${BASE}/cards/${id}`)
  if (!res.ok) throw new Error("Failed to fetch card")
  return res.json()
}

export default function CardDetailPage() {
  const { id } = useParams<{ id: string }>()
  return <CardDetail fetchCard={fetchCard} cardId={id ?? ""} />
}
