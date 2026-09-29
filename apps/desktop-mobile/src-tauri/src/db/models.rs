use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Set {
    pub id: String,
    pub name: String,
    pub series: Option<String>,
    pub release_date: Option<String>,
    pub total_cards: Option<i32>,
    pub logo_url: Option<String>,
    pub symbol_url: Option<String>,
    pub created_at: Option<String>,
    pub updated_at: String,
    pub synced_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Card {
    pub id: String,
    pub set_id: String,
    pub number: String,
    pub name: String,
    pub rarity: Option<String>,
    pub hp: Option<i32>,
    pub types: Option<Vec<String>>,
    pub subtypes: Option<Vec<String>>,
    pub supertype: Option<String>,
    pub images: Option<CardImages>,
    pub tcgplayer_url: Option<String>,
    pub cardmarket_url: Option<String>,
    pub prices: Option<serde_json::Value>,
    pub created_at: Option<String>,
    pub updated_at: String,
    pub synced_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CardImages {
    pub small: Option<String>,
    pub large: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CollectionCard {
    pub card_id: String,
    pub quantity: i32,
    pub condition: String,
    pub acquired_price: Option<f64>,
    pub acquired_date: Option<String>,
    pub notes: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Setting {
    pub key: String,
    pub value: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncStatus {
    pub sets: i64,
    pub cards: i64,
    pub last_synced_at: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct NewSet {
    pub id: String,
    pub name: String,
    pub series: Option<String>,
    pub release_date: Option<String>,
    pub total_cards: Option<i32>,
    pub logo_url: Option<String>,
    pub symbol_url: Option<String>,
    pub created_at: Option<String>,
    pub updated_at: String,
    pub synced_at: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct NewCard {
    pub id: String,
    pub set_id: String,
    pub number: String,
    pub name: String,
    pub rarity: Option<String>,
    pub hp: Option<i32>,
    pub types: Option<Vec<String>>,
    pub subtypes: Option<Vec<String>>,
    pub supertype: Option<String>,
    pub images: Option<CardImages>,
    pub tcgplayer_url: Option<String>,
    pub cardmarket_url: Option<String>,
    pub prices: Option<serde_json::Value>,
    pub created_at: Option<String>,
    pub updated_at: String,
    pub synced_at: String,
}
