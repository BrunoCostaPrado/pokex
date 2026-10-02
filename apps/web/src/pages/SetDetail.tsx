import { SetDetail } from "@pokex/ui"
import { useParams } from "react-router-dom"

const BASE = "/api"

async function fetchSet(id: string) {
  const res = await fetch(`${BASE}/sets/${id}`)
  if (!res.ok) throw new Error("Set not found")
  return res.json()
}

async function fetchCards(setId: string) {
  const qs = new URLSearchParams()
  qs.set("set_id", setId)
  qs.set("limit", "1000")
  const res = await fetch(`${BASE}/cards?${qs}`)
  if (!res.ok) throw new Error("Failed to fetch cards")
  return res.json()
}

export default function SetDetailPage() {
  const { id } = useParams<{ id: string }>()
  return <SetDetail fetchSet={fetchSet} fetchCards={fetchCards} setId={id ?? ""} />
}
