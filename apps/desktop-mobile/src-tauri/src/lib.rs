mod api;
mod db;
mod sync;

use api::client::ApiClient;
use crate::db::commands::*;
use crate::sync::{sync_sets, sync_cards, full_sync, get_sync_status};
use moka::future::Cache;
use once_cell::sync::Lazy;
use std::sync::Arc;
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let db_pool = crate::db::init_db(app.handle()).map_err(|e| format!("Failed to initialize database: {}", e))?;
            app.manage(db_pool.clone());

            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                let api_url = get_api_url_from_db(db_pool)
                    .await
                    .unwrap_or_else(|| "http://10.0.2.2:8000".to_string());
                let api_client = Arc::new(ApiClient::new(api_url));
                app_handle.manage(api_client);
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            greet,
            db_get_sets,
            db_get_set,
            db_get_cards,
            db_get_card,
            db_upsert_set,
            db_upsert_card,
            db_collection_get,
            db_collection_add,
            db_collection_update,
            db_collection_remove,
            db_settings_get,
            db_settings_set,
            db_get_sync_status,
            sync_sets,
            sync_cards,
            full_sync,
            get_sync_status,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

static API_URL_CACHE: Lazy<Cache<String, String>> = Lazy::new(|| {
    Cache::builder()
        .max_capacity(1)
        .time_to_live(std::time::Duration::from_secs(300))
        .build()
});

async fn get_api_url_from_db(pool: crate::db::DbPool) -> Option<String> {
    const CACHE_KEY: &str = "api_url";

    if let Some(cached) = API_URL_CACHE.get(CACHE_KEY).await {
        return Some(cached);
    }

    let conn = pool.connect().ok()?;
    let mut rows = conn
        .query(
            "SELECT value FROM settings WHERE key = 'api_url'",
            libsql::params![],
        )
        .await
        .ok()?;
    if let Some(row) = rows.next().await.ok()? {
        let value: String = row.get(0).ok()?;
        API_URL_CACHE
            .insert(CACHE_KEY.to_string(), value.clone())
            .await;
        return Some(value);
    }
    None
}

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}
