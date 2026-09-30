import { CardGrid, ErrorState, LoadingState } from "@pokex/ui"
import { Link } from "wouter"
import { useTauriQuery } from "../hooks/useTauriQuery"
import type { Set as TauriSet } from "../types/tauri"

function SetLink({ to, children }: { to: string; children: React.ReactNode }) {
  return <Link href={to}>{children}</Link>
}

export function SetsListPage() {
  const {
    data: sets,
    isLoading,
    error,
  } = useTauriQuery<TauriSet[]>(["sets"], "db_get_sets", { limit: 100, offset: 0 })

  if (isLoading) return <LoadingState message="Loading sets..." />
  if (error) return <ErrorState message="Failed to load sets" />

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Pokémon TCG Sets</h1>
      <CardGrid cards={sets ?? []} LinkComponent={SetLink} />
    </div>
  )
}
