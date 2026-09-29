use crate::api::client::ApiClient;
use crate::db::commands::{db_get_sync_status, db_upsert_card, db_upsert_set};
use crate::db::models::SyncStatus;
use crate::db::DbPool;
use std::sync::Arc;
use tauri::State;

pub struct SyncManager {
    api_client: Arc<ApiClient>,
}

impl SyncManager {
    pub fn new(api_client: Arc<ApiClient>) -> Self {
        Self { api_client }
    }

    pub async fn sync_sets(&self, db_pool: State<'_, DbPool>) -> Result<SyncResult, SyncError> {
        let mut total_synced = 0;
        let mut page = 0;
        let page_size = 100;

        loop {
            let sets = self
                .api_client
                .get_sets(page_size, page * page_size)
                .await?;
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

    pub async fn sync_cards(
        &self,
        set_id: Option<String>,
        db_pool: State<'_, DbPool>,
    ) -> Result<SyncResult, SyncError> {
        let mut total_synced = 0;
        let mut page = 0;
        let page_size = 100;

        loop {
            let cards = self
                .api_client
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

    pub async fn full_sync(&self, db_pool: State<'_, DbPool>) -> Result<SyncResult, SyncError> {
        let sets_result = self.sync_sets(db_pool.clone()).await?;
        let cards_result = self.sync_cards(None, db_pool.clone()).await?;

        Ok(SyncResult {
            sets_synced: sets_result.sets_synced,
            cards_synced: cards_result.cards_synced,
        })
    }

    pub async fn get_status(&self, db_pool: State<'_, DbPool>) -> Result<SyncStatus, SyncError> {
        Ok(db_get_sync_status(db_pool).await?)
    }
}

#[derive(Debug, serde::Serialize)]
pub struct SyncResult {
    pub sets_synced: u32,
    pub cards_synced: u32,
}

#[derive(Debug, thiserror::Error)]
pub enum SyncError {
    #[error("API error: {0}")]
    Api(#[from] crate::api::client::ApiError),
    #[error("Database error: {0}")]
    Database(#[from] crate::db::commands::DbError),
    #[error("Database error: {0}")]
    Libsql(#[from] libsql::Error),
}

impl serde::Serialize for SyncError {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        use serde::ser::SerializeStruct;
        let mut state = serializer.serialize_struct("SyncError", 2)?;
        state.serialize_field(
            "type",
            match self {
                SyncError::Api(_) => "Api",
                SyncError::Database(_) => "Database",
                SyncError::Libsql(_) => "Libsql",
            },
        )?;
        state.serialize_field("message", &self.to_string())?;
        state.end()
    }
}

#[tauri::command]
pub async fn sync_sets(
    api_client: State<'_, Arc<ApiClient>>,
    db_pool: State<'_, DbPool>,
) -> Result<SyncResult, SyncError> {
    let manager = SyncManager::new(api_client.inner().clone());
    manager.sync_sets(db_pool).await
}

#[tauri::command]
pub async fn sync_cards(
    api_client: State<'_, Arc<ApiClient>>,
    set_id: Option<String>,
    db_pool: State<'_, DbPool>,
) -> Result<SyncResult, SyncError> {
    let manager = SyncManager::new(api_client.inner().clone());
    manager.sync_cards(set_id, db_pool).await
}

#[tauri::command]
pub async fn full_sync(
    api_client: State<'_, Arc<ApiClient>>,
    db_pool: State<'_, DbPool>,
) -> Result<SyncResult, SyncError> {
    let manager = SyncManager::new(api_client.inner().clone());
    manager.full_sync(db_pool).await
}

#[tauri::command]
pub async fn get_sync_status(
    api_client: State<'_, Arc<ApiClient>>,
    db_pool: State<'_, DbPool>,
) -> Result<SyncStatus, SyncError> {
    let manager = SyncManager::new(api_client.inner().clone());
    manager.get_status(db_pool).await
}
