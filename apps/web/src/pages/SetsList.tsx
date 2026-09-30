import { SetsList } from "@pokex/ui"
import { Link } from "react-router-dom"

const BASE = "/api"

function SetLink({ to, children }: { to: string; children: React.ReactNode }) {
  return <Link to={to}>{children}</Link>
}

async function fetchSets(skip = 0, limit = 100) {
  const res = await fetch(`${BASE}/sets?skip=${skip}&limit=${limit}`)
  if (!res.ok) throw new Error("Failed to fetch sets")
  return res.json()
}

export default function SetsListPage() {
  return <SetsList fetchSets={fetchSets} LinkComponent={SetLink} />
}
