import { SetDetail } from "@pokex/ui"
import { Link, useParams } from "wouter"
import { tauriCommand } from "../hooks/useTauriQuery"
import type { Card, Set as TauriSet } from "../types/tauri"

function SetLink({ to, children }: { to: string; children: React.ReactNode }) {
  return <Link href={to}>{children}</Link>
}

const fetchSet = async (id: string) => {
  const set = await tauriCommand<TauriSet | null>("db_get_set", { id })
  if (!set) throw new Error("Set not found")
  return {
    id: set.id,
    name: set.name,
    series: set.series ?? "",
    total_cards: set.total_cards,
    logo_url: set.logo_url,
    release_date: set.release_date,
  }
}
const fetchCards = (setId: string) =>
  tauriCommand<Card[]>("db_get_cards", { set_id: setId, limit: 1000, offset: 0 })

export function SetDetailPage() {
  const params = useParams() as { id: string } | undefined
  const id = params?.id ?? ""
  return (
    <SetDetail fetchSet={fetchSet} fetchCards={fetchCards} setId={id} LinkComponent={SetLink} />
  )
}
