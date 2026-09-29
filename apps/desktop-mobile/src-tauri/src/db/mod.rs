pub mod commands;
pub mod models;
pub mod schema;

use libsql::{Builder, Database};
use std::sync::Arc;
use tauri::Manager;

pub type DbPool = Arc<Database>;

pub async fn init_db_async(db_url: &str) -> Result<DbPool, Box<dyn std::error::Error>> {
    let db = Builder::new_local(db_url).build().await?;

    let conn = db.connect()?;

    for migration in crate::db::schema::get_migrations() {
        conn.execute_batch(&migration.sql).await?;
    }

    let pool = Arc::new(db);
    Ok(pool)
}

pub fn init_db(app: &tauri::AppHandle) -> Result<DbPool, Box<dyn std::error::Error>> {
    let db_path = app
        .path()
        .app_data_dir()
        .map_err(|e| format!("Failed to get app data dir: {}", e))?
        .join("pokex.db");

    if let Some(parent) = db_path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Failed to create db dir: {}", e))?;
    }

    let db_url = format!("file:{}", db_path.to_string_lossy());
    tauri::async_runtime::block_on(init_db_async(&db_url))
}
