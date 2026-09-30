import { useQuery } from "@tanstack/react-query"
import { CardGrid } from "./CardGrid"
import { ErrorState, LoadingState } from "./SetsList"

interface LinkComponentProps {
  to: string
  children: React.ReactNode
  className?: string
}

interface CardData {
  id: string
  name: string
  number: string
  rarity?: string
  images?: {
    small?: string
    large?: string
  }
  set?: {
    id: string
    name: string
  }
}

interface CollectionProps {
  fetchCollection: () => Promise<CardData[]>
  LinkComponent?: React.ComponentType<LinkComponentProps>
}

export function Collection({ fetchCollection, LinkComponent }: CollectionProps) {
  const {
    data: cards,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["collection"],
    queryFn: fetchCollection,
  })

  if (isLoading) return <LoadingState message="Loading collection..." />
  if (error) return <ErrorState message="Failed to load collection" />

  const BrowseLink =
    LinkComponent ??
    ((props: LinkComponentProps) => (
      <a href={props.to} className={props.className}>
        {props.children}
      </a>
    ))

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">My Collection</h1>
      {cards?.length === 0 ? (
        <div className="text-center py-12 text-[var(--color-text-muted)]">
          <p className="text-xl mb-2">No cards in collection yet</p>
          <BrowseLink to="/sets" className="text-[var(--color-primary)] hover:underline">
            Browse sets to add cards
          </BrowseLink>
        </div>
      ) : (
        <CardGrid cards={cards ?? []} LinkComponent={LinkComponent} />
      )}
    </div>
  )
}
