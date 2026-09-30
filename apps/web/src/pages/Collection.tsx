import { Collection } from "@pokex/ui"
import { Link } from "react-router-dom"

const BASE = "/api"

function CollectionLink({ to, children }: { to: string; children: React.ReactNode }) {
  return <Link to={to}>{children}</Link>
}

async function fetchCollection() {
  const res = await fetch(`${BASE}/collection`)
  if (!res.ok) throw new Error("Failed to fetch collection")
  return res.json()
}

export default function CollectionPage() {
  return <Collection fetchCollection={fetchCollection} LinkComponent={CollectionLink} />
}
