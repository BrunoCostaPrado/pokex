import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { tauriCommand } from "../hooks/useTauriQuery"
import type { Setting, SyncResult, SyncStatus } from "../types/tauri"

export function Settings() {
  const queryClient = useQueryClient()

  const { data: settings = [] } = useQuery({
    queryKey: ["settings"],
    queryFn: () => tauriCommand<Setting[]>("db_settings_get"),
  })

  const { data: syncStatus } = useQuery({
    queryKey: ["syncStatus"],
    queryFn: () => tauriCommand<SyncStatus>("db_get_sync_status"),
  })

  const settingsMap = new Map<string, string>(settings.map(s => [s.key, s.value]))

  const updateSetting = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      tauriCommand<void>("db_settings_set", { key, value }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["settings"] }),
  })

  const syncSets = useMutation({
    mutationFn: () => tauriCommand<SyncResult>("sync_sets"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["syncStatus"] })
      queryClient.invalidateQueries({ queryKey: ["sets"] })
    },
  })

  const syncCards = useMutation({
    mutationFn: () => tauriCommand<SyncResult>("sync_cards"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["syncStatus"] })
      queryClient.invalidateQueries({ queryKey: ["cards"] })
    },
  })

  const fullSync = useMutation({
    mutationFn: () => tauriCommand<SyncResult>("full_sync"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["syncStatus"] })
      queryClient.invalidateQueries({ queryKey: ["sets"] })
      queryClient.invalidateQueries({ queryKey: ["cards"] })
    },
  })

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-4">Database</h2>
        <div className="bg-white rounded-lg border border-[var(--color-border)] p-4 space-y-4">
          <div>
            <h3 className="font-medium mb-2">Sync Status</h3>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-[var(--color-text-muted)]">Sets</p>
                <p className="font-bold">{syncStatus?.sets ?? 0}</p>
              </div>
              <div>
                <p className="text-[var(--color-text-muted)]">Cards</p>
                <p className="font-bold">{syncStatus?.cards ?? 0}</p>
              </div>
              <div>
                <p className="text-[var(--color-text-muted)]">Last Synced</p>
                <p className="font-bold">{syncStatus?.last_synced_at ?? "Never"}</p>
              </div>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => syncSets.mutate()}
              disabled={syncSets.isPending}
              className="px-4 py-2 bg-[var(--color-primary)] text-white rounded-md text-sm hover:opacity-80 disabled:opacity-50"
            >
              {syncSets.isPending ? "Syncing Sets..." : "Sync Sets"}
            </button>
            <button
              type="button"
              onClick={() => syncCards.mutate()}
              disabled={syncCards.isPending}
              className="px-4 py-2 bg-[var(--color-primary)] text-white rounded-md text-sm hover:opacity-80 disabled:opacity-50"
            >
              {syncCards.isPending ? "Syncing Cards..." : "Sync Cards"}
            </button>
            <button
              type="button"
              onClick={() => fullSync.mutate()}
              disabled={fullSync.isPending}
              className="px-4 py-2 bg-[var(--color-primary)] text-white rounded-md text-sm hover:opacity-80 disabled:opacity-50"
            >
              {fullSync.isPending ? "Full Sync..." : "Full Sync"}
            </button>
          </div>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-4">App Settings</h2>
        <div className="bg-white rounded-lg border border-[var(--color-border)] p-4 space-y-4">
          {Array.from(settingsMap.entries()).map(([key, value]) => (
            <div key={key} className="flex items-center justify-between">
              <label className="text-sm" htmlFor={key}>
                {key.replace(/_/g, " ")}
              </label>
              <input
                type="text"
                id={key}
                value={value}
                onChange={e => updateSetting.mutate({ key, value: e.target.value })}
                className="flex-1 ml-4 px-3 py-1 border border-[var(--color-border)] rounded text-sm"
              />
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
