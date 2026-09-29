export interface Set {
  id: string
  name: string
  series?: string
  release_date?: string
  total_cards?: number
  logo_url?: string
  symbol_url?: string
  created_at?: string
  updated_at: string
  synced_at: string
}

export interface CardImages {
  small?: string
  large?: string
}

export interface Card {
  id: string
  set_id: string
  number: string
  name: string
  rarity?: string
  hp?: number
  types?: string[]
  subtypes?: string[]
  supertype?: string
  images?: CardImages
  tcgplayer_url?: string
  cardmarket_url?: string
  prices?: Record<string, { normal?: number; holo?: number; reverseHolo?: number }>
  created_at?: string
  updated_at: string
  synced_at: string
}

export interface CollectionCard {
  card_id: string
  quantity: number
  condition: string
  acquired_price?: number
  acquired_date?: string
  notes?: string
  created_at: string
  updated_at: string
}

export interface Setting {
  key: string
  value: string
}

export interface SyncStatus {
  sets: number
  cards: number
  last_synced_at?: string
}

export interface SyncResult {
  sets_synced: number
  cards_synced: number
}

export interface DbError {
  type: "Database" | "Serialization" | "NotFound"
  message: string
}
