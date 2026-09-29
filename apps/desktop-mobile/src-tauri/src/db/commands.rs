use crate::db::models::*;
use crate::db::DbPool;
use libsql::params;
use tauri::State;
use thiserror::Error;

#[derive(Error, Debug, serde::Serialize)]
pub enum DbError {
    #[error("Database error: {0}")]
    Database(String),
    #[error("Serialization error: {0}")]
    Serialization(String),
    #[error("Not found: {0}")]
    NotFound(String),
}

impl From<libsql::Error> for DbError {
    fn from(err: libsql::Error) -> Self {
        DbError::Database(err.to_string())
    }
}

impl From<serde_json::Error> for DbError {
    fn from(err: serde_json::Error) -> Self {
        DbError::Serialization(err.to_string())
    }
}

type DbResult<T> = Result<T, DbError>;

fn get_pool(state: State<'_, DbPool>) -> DbResult<libsql::Connection> {
    state
        .inner()
        .connect()
        .map_err(|e| DbError::Database(e.to_string()))
}

#[tauri::command]
pub async fn db_get_sets(
    limit: Option<i32>,
    offset: Option<i32>,
    state: State<'_, DbPool>,
) -> DbResult<Vec<Set>> {
    let conn = get_pool(state)?;
    let limit = limit.unwrap_or(100);
    let offset = offset.unwrap_or(0);

    let mut rows = conn
        .query(
            "SELECT id, name, series, release_date, total_cards, logo_url, symbol_url, created_at, updated_at, synced_at FROM sets ORDER BY name LIMIT ? OFFSET ?",
            params![limit, offset],
        )
        .await?;

    let mut sets = Vec::new();
    while let Some(row) = rows.next().await? {
        sets.push(Set {
            id: row.get(0)?,
            name: row.get(1)?,
            series: row.get(2)?,
            release_date: row.get(3)?,
            total_cards: row.get(4)?,
            logo_url: row.get(5)?,
            symbol_url: row.get(6)?,
            created_at: row.get(7)?,
            updated_at: row.get(8)?,
            synced_at: row.get(9)?,
        });
    }
    Ok(sets)
}

#[tauri::command]
pub async fn db_get_set(id: String, state: State<'_, DbPool>) -> DbResult<Option<Set>> {
    let conn = get_pool(state)?;

    let mut rows = conn
        .query(
            "SELECT id, name, series, release_date, total_cards, logo_url, symbol_url, created_at, updated_at, synced_at FROM sets WHERE id = ?",
            params![id],
        )
        .await?;

    if let Some(row) = rows.next().await? {
        Ok(Some(Set {
            id: row.get(0)?,
            name: row.get(1)?,
            series: row.get(2)?,
            release_date: row.get(3)?,
            total_cards: row.get(4)?,
            logo_url: row.get(5)?,
            symbol_url: row.get(6)?,
            created_at: row.get(7)?,
            updated_at: row.get(8)?,
            synced_at: row.get(9)?,
        }))
    } else {
        Ok(None)
    }
}

#[tauri::command]
pub async fn db_get_cards(
    set_id: Option<String>,
    limit: Option<i32>,
    offset: Option<i32>,
    state: State<'_, DbPool>,
) -> DbResult<Vec<Card>> {
    let conn = get_pool(state)?;
    let limit = limit.unwrap_or(100);
    let offset = offset.unwrap_or(0);

    let mut rows = if let Some(set_id) = set_id {
        conn.query(
            "SELECT id, set_id, number, name, rarity, hp, types, subtypes, supertype, images, tcgplayer_url, cardmarket_url, prices, created_at, updated_at, synced_at FROM cards WHERE set_id = ? ORDER BY number LIMIT ? OFFSET ?",
            params![set_id, limit, offset],
        ).await?
    } else {
        conn.query(
            "SELECT id, set_id, number, name, rarity, hp, types, subtypes, supertype, images, tcgplayer_url, cardmarket_url, prices, created_at, updated_at, synced_at FROM cards ORDER BY name LIMIT ? OFFSET ?",
            params![limit, offset],
        ).await?
    };

    let mut cards = Vec::new();
    while let Some(row) = rows.next().await? {
        let types: Option<String> = row.get(6)?;
        let subtypes: Option<String> = row.get(7)?;
        let images: Option<String> = row.get(9)?;
        let prices: Option<String> = row.get(12)?;

        cards.push(Card {
            id: row.get(0)?,
            set_id: row.get(1)?,
            number: row.get(2)?,
            name: row.get(3)?,
            rarity: row.get(4)?,
            hp: row.get(5)?,
            types: types.and_then(|s| serde_json::from_str(&s).ok()),
            subtypes: subtypes.and_then(|s| serde_json::from_str(&s).ok()),
            supertype: row.get(8)?,
            images: images.and_then(|s| serde_json::from_str(&s).ok()),
            tcgplayer_url: row.get(10)?,
            cardmarket_url: row.get(11)?,
            prices: prices.and_then(|s| serde_json::from_str(&s).ok()),
            created_at: row.get(13)?,
            updated_at: row.get(14)?,
            synced_at: row.get(15)?,
        });
    }
    Ok(cards)
}

#[tauri::command]
pub async fn db_get_card(id: String, state: State<'_, DbPool>) -> DbResult<Option<Card>> {
    let conn = get_pool(state)?;

    let mut rows = conn
        .query(
            "SELECT id, set_id, number, name, rarity, hp, types, subtypes, supertype, images, tcgplayer_url, cardmarket_url, prices, created_at, updated_at, synced_at FROM cards WHERE id = ?",
            params![id],
        )
        .await?;

    if let Some(row) = rows.next().await? {
        let types: Option<String> = row.get(6)?;
        let subtypes: Option<String> = row.get(7)?;
        let images: Option<String> = row.get(9)?;
        let prices: Option<String> = row.get(12)?;

        Ok(Some(Card {
            id: row.get(0)?,
            set_id: row.get(1)?,
            number: row.get(2)?,
            name: row.get(3)?,
            rarity: row.get(4)?,
            hp: row.get(5)?,
            types: types.and_then(|s| serde_json::from_str(&s).ok()),
            subtypes: subtypes.and_then(|s| serde_json::from_str(&s).ok()),
            supertype: row.get(8)?,
            images: images.and_then(|s| serde_json::from_str(&s).ok()),
            tcgplayer_url: row.get(10)?,
            cardmarket_url: row.get(11)?,
            prices: prices.and_then(|s| serde_json::from_str(&s).ok()),
            created_at: row.get(13)?,
            updated_at: row.get(14)?,
            synced_at: row.get(15)?,
        }))
    } else {
        Ok(None)
    }
}

#[tauri::command]
pub async fn db_upsert_set(set: NewSet, state: State<'_, DbPool>) -> DbResult<()> {
    let conn = get_pool(state)?;

    conn.execute(
        r#"
        INSERT INTO sets (id, name, series, release_date, total_cards, logo_url, symbol_url, created_at, updated_at, synced_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            series = excluded.series,
            release_date = excluded.release_date,
            total_cards = excluded.total_cards,
            logo_url = excluded.logo_url,
            symbol_url = excluded.symbol_url,
            updated_at = excluded.updated_at,
            synced_at = excluded.synced_at
        "#,
        params![
            set.id,
            set.name,
            set.series,
            set.release_date,
            set.total_cards,
            set.logo_url,
            set.symbol_url,
            set.created_at,
            set.updated_at,
            set.synced_at
        ],
    )
    .await?;

    Ok(())
}

#[tauri::command]
pub async fn db_upsert_card(card: NewCard, state: State<'_, DbPool>) -> DbResult<()> {
    let conn = get_pool(state)?;

    let types_json = serde_json::to_string(&card.types)?;
    let subtypes_json = serde_json::to_string(&card.subtypes)?;
    let images_json = serde_json::to_string(&card.images)?;
    let prices_json = serde_json::to_string(&card.prices)?;

    conn.execute(
        r#"
        INSERT INTO cards (id, set_id, number, name, rarity, hp, types, subtypes, supertype, images, tcgplayer_url, cardmarket_url, prices, created_at, updated_at, synced_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            set_id = excluded.set_id,
            number = excluded.number,
            name = excluded.name,
            rarity = excluded.rarity,
            hp = excluded.hp,
            types = excluded.types,
            subtypes = excluded.subtypes,
            supertype = excluded.supertype,
            images = excluded.images,
            tcgplayer_url = excluded.tcgplayer_url,
            cardmarket_url = excluded.cardmarket_url,
            prices = excluded.prices,
            updated_at = excluded.updated_at,
            synced_at = excluded.synced_at
        "#,
        params![
            card.id,
            card.set_id,
            card.number,
            card.name,
            card.rarity,
            card.hp,
            types_json,
            subtypes_json,
            card.supertype,
            images_json,
            card.tcgplayer_url,
            card.cardmarket_url,
            prices_json,
            card.created_at,
            card.updated_at,
            card.synced_at
        ],
    )
    .await?;

    Ok(())
}

#[tauri::command]
pub async fn db_collection_get(state: State<'_, DbPool>) -> DbResult<Vec<CollectionCard>> {
    let conn = get_pool(state)?;

    let mut rows = conn
        .query(
            "SELECT card_id, quantity, condition, acquired_price, acquired_date, notes, created_at, updated_at FROM collection ORDER BY updated_at DESC",
            params![],
        )
        .await?;

    let mut collection = Vec::new();
    while let Some(row) = rows.next().await? {
        collection.push(CollectionCard {
            card_id: row.get(0)?,
            quantity: row.get(1)?,
            condition: row.get(2)?,
            acquired_price: row.get(3)?,
            acquired_date: row.get(4)?,
            notes: row.get(5)?,
            created_at: row.get(6)?,
            updated_at: row.get(7)?,
        });
    }
    Ok(collection)
}

#[tauri::command]
pub async fn db_collection_add(
    card_id: String,
    quantity: i32,
    condition: String,
    acquired_price: Option<f64>,
    acquired_date: Option<String>,
    notes: Option<String>,
    state: State<'_, DbPool>,
) -> DbResult<()> {
    let conn = get_pool(state)?;
    let now = chrono::Utc::now().to_rfc3339();

    conn.execute(
        r#"
        INSERT INTO collection (card_id, quantity, condition, acquired_price, acquired_date, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(card_id) DO UPDATE SET
            quantity = excluded.quantity,
            condition = excluded.condition,
            acquired_price = excluded.acquired_price,
            acquired_date = excluded.acquired_date,
            notes = excluded.notes,
            updated_at = excluded.updated_at
        "#,
        params![
            card_id,
            quantity,
            condition,
            acquired_price,
            acquired_date,
            notes,
            now.clone(),
            now
        ],
    )
    .await?;

    Ok(())
}

#[tauri::command]
pub async fn db_collection_update(
    card_id: String,
    quantity: Option<i32>,
    condition: Option<String>,
    acquired_price: Option<f64>,
    acquired_date: Option<String>,
    notes: Option<String>,
    state: State<'_, DbPool>,
) -> DbResult<()> {
    let conn = get_pool(state)?;
    let now = chrono::Utc::now().to_rfc3339();

    // Fetch current values for fields not being updated
    let mut rows = conn
        .query(
            "SELECT quantity, condition, acquired_price, acquired_date, notes FROM collection WHERE card_id = ?",
            params![card_id.clone()],
        )
        .await?;

    let (curr_qty, curr_cond, curr_price, curr_date, curr_notes) =
        if let Some(row) = rows.next().await? {
            (
                row.get::<i32>(0).unwrap_or(1),
                row.get::<String>(1)
                    .unwrap_or_else(|_| "near_mint".to_string()),
                row.get::<Option<f64>>(2).unwrap_or(None),
                row.get::<Option<String>>(3).unwrap_or(None),
                row.get::<Option<String>>(4).unwrap_or(None),
            )
        } else {
            return Err(DbError::NotFound(
                "Card not found in collection".to_string(),
            ));
        };

    let qty = quantity.unwrap_or(curr_qty);
    let cond = condition.unwrap_or(curr_cond);
    let price = acquired_price.or(curr_price);
    let date = acquired_date.or(curr_date);
    let nts = notes.or(curr_notes);

    conn.execute(
        "UPDATE collection SET quantity = ?, condition = ?, acquired_price = ?, acquired_date = ?, notes = ?, updated_at = ? WHERE card_id = ?",
        params![qty, cond, price, date, nts, now, card_id],
    )
    .await?;

    Ok(())
}

#[tauri::command]
pub async fn db_collection_remove(card_id: String, state: State<'_, DbPool>) -> DbResult<()> {
    let conn = get_pool(state)?;

    conn.execute("DELETE FROM collection WHERE card_id = ?", params![card_id])
        .await?;

    Ok(())
}

#[tauri::command]
pub async fn db_settings_get(state: State<'_, DbPool>) -> DbResult<Vec<Setting>> {
    let conn = get_pool(state)?;

    let mut rows = conn
        .query("SELECT key, value FROM settings", params![])
        .await?;

    let mut settings = Vec::new();
    while let Some(row) = rows.next().await? {
        settings.push(Setting {
            key: row.get(0)?,
            value: row.get(1)?,
        });
    }
    Ok(settings)
}

#[tauri::command]
pub async fn db_settings_set(key: String, value: String, state: State<'_, DbPool>) -> DbResult<()> {
    let conn = get_pool(state)?;

    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        params![key, value],
    )
    .await?;

    Ok(())
}

#[tauri::command]
pub async fn db_get_sync_status(state: State<'_, DbPool>) -> DbResult<SyncStatus> {
    let conn = get_pool(state)?;

    let sets_count: i64 = conn
        .query("SELECT COUNT(*) FROM sets", params![])
        .await?
        .next()
        .await?
        .and_then(|row| row.get(0).ok())
        .unwrap_or(0);

    let cards_count: i64 = conn
        .query("SELECT COUNT(*) FROM cards", params![])
        .await?
        .next()
        .await?
        .and_then(|row| row.get(0).ok())
        .unwrap_or(0);

    let last_synced: Option<String> = conn
        .query("SELECT MAX(synced_at) FROM sets", params![])
        .await?
        .next()
        .await?
        .and_then(|row| row.get(0).ok());

    Ok(SyncStatus {
        sets: sets_count,
        cards: cards_count,
        last_synced_at: last_synced,
    })
}
