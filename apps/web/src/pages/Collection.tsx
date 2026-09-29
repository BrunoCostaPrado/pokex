import { Collection } from "@pokex/ui"

const BASE = "/api"

async function fetchCollection() {
  const res = await fetch(`${BASE}/collection`)
  if (!res.ok) throw new Error("Failed to fetch collection")
  return res.json()
}

export default function CollectionPage() {
  return <Collection fetchCollection={fetchCollection} />
}
