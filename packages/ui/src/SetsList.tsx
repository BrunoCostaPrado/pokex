import { useQuery } from "@tanstack/react-query"
import { CardCard, ErrorState, LoadingState } from "."

interface SetData {
  id: string
  logo_url?: string
  name: string
  series: string
  total_cards?: number
}

export function SetsList() {
  const {
    data: sets,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["sets", 0, 100],
    queryFn: () => fetch("/api/sets?skip=0&limit=100").then(r => r.json()),
  })

  if (isLoading) return <LoadingState message="Loading sets..." />
  if (error) return <ErrorState message="Failed to load sets" />

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Pokémon TCG Sets</h1>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {sets?.map((set: SetData) => (
          <CardCard key={set.id} card={set} />
        ))}
      </div>
    </div>
  )
}
