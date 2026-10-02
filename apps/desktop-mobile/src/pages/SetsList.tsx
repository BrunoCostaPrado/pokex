import { CardCard } from "@pokex/ui"
import { invoke } from "@tauri-apps/api/core"
import { useEffect, useState } from "react"
import type { Set as TauriSet } from "../types/tauri"

export function SetsListPage() {
  const [sets, setSets] = useState<TauriSet[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    invoke<TauriSet[]>("db_get_sets", { limit: 100, offset: 0 })
      .then(data => {
        if (mounted) {
          setSets(data)
          setIsLoading(false)
        }
      })
      .catch(err => {
        if (mounted) {
          setError(err.message)
          setIsLoading(false)
        }
      })
    return () => {
      mounted = false
    }
  }, [])

  if (isLoading)
    return <div className="text-center py-8 text-[var(--color-text-muted)]">Loading sets...</div>
  if (error)
    return (
      <div className="text-center py-8 text-[var(--color-text-muted)]">Failed to load sets</div>
    )

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Pokémon TCG Sets</h1>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {sets.map(set => (
          <CardCard key={set.id} card={set} />
        ))}
      </div>
    </div>
  )
}
