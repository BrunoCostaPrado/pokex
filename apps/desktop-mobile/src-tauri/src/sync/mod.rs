use crate::api::client::ApiClient;
use crate::db::commands::{db_get_sync_status, db_upsert_card, db_upsert_set};
use crate::db::models::SyncStatus;
use crate::db::DbPool;
use serde::Serialize;
use std::sync::Arc;
use tauri::State;

#[derive(Debug, Serialize)]
pub struct SyncResult {
    pub sets_synced: u32,
    pub cards_synced: u32,
}

#[derive(Debug, thiserror::Error, Serialize)]
#[serde(tag = "type")]
pub enum SyncError {
    #[error("API error: {0}")]
    #[serde(serialize_with = "serialize_error")]
    Api(#[from] crate::api::client::ApiError),
    #[error("Database error: {0}")]
    #[serde(serialize_with = "serialize_error")]
    Database(#[from] crate::db::commands::DbError),
    #[error("Database error: {0}")]
    #[serde(serialize_with = "serialize_error")]
    Libsql(#[from] libsql::Error),
}

fn serialize_error<S, E>(e: &E, serializer: S) -> Result<S::Ok, S::Error>
where
    S: serde::Serializer,
    E: std::error::Error,
{
    serializer.serialize_str(&e.to_string())
}

async fn sync_sets_internal(
    api_client: &ApiClient,
    db_pool: State<'_, DbPool>,
) -> Result<SyncResult, SyncError> {
    let mut total_synced = 0;
    let mut page = 0;
    let page_size = 100;

    loop {
        let sets = api_client.get_sets(page_size, page * page_size).await?;
        if sets.is_empty() {
            break;
        }

        for set in sets {
            let new_set: crate::db::models::NewSet = set.into();
            db_upsert_set(new_set, db_pool.clone()).await?;
            total_synced += 1;
        }

        page += 1;
    }

    Ok(SyncResult {
        sets_synced: total_synced,
        cards_synced: 0,
    })
}

async fn sync_cards_internal(
    api_client: &ApiClient,
    set_id: Option<String>,
    db_pool: State<'_, DbPool>,
) -> Result<SyncResult, SyncError> {
    let mut total_synced = 0;
    let mut page = 0;
    let page_size = 100;

    loop {
        let cards = api_client
            .get_cards(set_id.as_deref(), page_size, page * page_size)
            .await?;
        if cards.is_empty() {
            break;
        }

        for card in cards {
            let new_card: crate::db::models::NewCard = card.into();
            db_upsert_card(new_card, db_pool.clone()).await?;
            total_synced += 1;
        }

        page += 1;
    }

    Ok(SyncResult {
        sets_synced: 0,
        cards_synced: total_synced,
    })
}

async fn full_sync_internal(
    api_client: &ApiClient,
    db_pool: State<'_, DbPool>,
) -> Result<SyncResult, SyncError> {
    let sets_result = sync_sets_internal(api_client, db_pool.clone()).await?;
    let cards_result = sync_cards_internal(api_client, None, db_pool.clone()).await?;

    Ok(SyncResult {
        sets_synced: sets_result.sets_synced,
        cards_synced: cards_result.cards_synced,
    })
}

#[tauri::command]
pub async fn sync_sets(
    api_client: State<'_, Arc<ApiClient>>,
    db_pool: State<'_, DbPool>,
) -> Result<SyncResult, SyncError> {
    sync_sets_internal(&api_client, db_pool).await
}

#[tauri::command]
pub async fn sync_cards(
    api_client: State<'_, Arc<ApiClient>>,
    set_id: Option<String>,
    db_pool: State<'_, DbPool>,
) -> Result<SyncResult, SyncError> {
    sync_cards_internal(&api_client, set_id, db_pool).await
}

#[tauri::command]
pub async fn full_sync(
    api_client: State<'_, Arc<ApiClient>>,
    db_pool: State<'_, DbPool>,
) -> Result<SyncResult, SyncError> {
    full_sync_internal(&api_client, db_pool).await
}

#[tauri::command]
pub async fn get_sync_status(
    _api_client: State<'_, Arc<ApiClient>>,
    db_pool: State<'_, DbPool>,
) -> Result<SyncStatus, SyncError> {
    Ok(db_get_sync_status(db_pool).await?)
}