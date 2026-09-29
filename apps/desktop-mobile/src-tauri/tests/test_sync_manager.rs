use chrono;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::RwLock;

struct MockSyncManager {
    last_sync: Arc<RwLock<Option<chrono::DateTime<chrono::Utc>>>>,
    pending_changes: Arc<RwLock<Vec<String>>>,
}

impl MockSyncManager {
    fn new() -> Self {
        Self {
            last_sync: Arc::new(RwLock::new(None)),
            pending_changes: Arc::new(RwLock::new(Vec::new())),
        }
    }

    async fn full_sync(&self) -> Result<(), String> {
        let mut last_sync = self.last_sync.write().await;
        *last_sync = Some(chrono::Utc::now());
        let mut pending = self.pending_changes.write().await;
        pending.clear();
        Ok(())
    }

    async fn incremental_sync(&self) -> Result<usize, String> {
        let pending = self.pending_changes.read().await;
        let count = pending.len();
        let mut last_sync = self.last_sync.write().await;
        *last_sync = Some(chrono::Utc::now());
        drop(pending);
        let mut pending = self.pending_changes.write().await;
        pending.clear();
        Ok(count)
    }

    async fn get_last_sync(&self) -> Option<chrono::DateTime<chrono::Utc>> {
        *self.last_sync.read().await
    }

    async fn add_pending_change(&self, change: String) {
        self.pending_changes.write().await.push(change);
    }

    async fn get_pending_count(&self) -> usize {
        self.pending_changes.read().await.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_full_sync_updates_timestamp() {
        let manager = MockSyncManager::new();

        assert!(manager.get_last_sync().await.is_none());

        manager.full_sync().await.unwrap();

        let last_sync = manager.get_last_sync().await;
        assert!(last_sync.is_some());
    }

    #[tokio::test]
    async fn test_incremental_sync_returns_change_count() {
        let manager = MockSyncManager::new();

        manager.add_pending_change("change1".to_string()).await;
        manager.add_pending_change("change2".to_string()).await;

        let count = manager.incremental_sync().await.unwrap();

        assert_eq!(count, 2);
        assert_eq!(manager.get_pending_count().await, 0);
    }

    #[tokio::test]
    async fn test_incremental_sync_empty() {
        let manager = MockSyncManager::new();

        let count = manager.incremental_sync().await.unwrap();

        assert_eq!(count, 0);
    }

    #[tokio::test]
    async fn test_full_sync_clears_pending() {
        let manager = MockSyncManager::new();

        manager.add_pending_change("change1".to_string()).await;
        manager.add_pending_change("change2".to_string()).await;

        manager.full_sync().await.unwrap();

        assert_eq!(manager.get_pending_count().await, 0);
    }

    #[tokio::test]
    async fn test_multiple_syncs_update_timestamp() {
        let manager = MockSyncManager::new();

        manager.full_sync().await.unwrap();
        let first_sync = manager.get_last_sync().await;

        tokio::time::sleep(Duration::from_millis(10)).await;

        manager.incremental_sync().await.unwrap();
        let second_sync = manager.get_last_sync().await;

        assert!(second_sync > first_sync);
    }

    #[tokio::test]
    async fn test_pending_changes_accumulate() {
        let manager = MockSyncManager::new();

        assert_eq!(manager.get_pending_count().await, 0);

        manager.add_pending_change("change1".to_string()).await;
        assert_eq!(manager.get_pending_count().await, 1);

        manager.add_pending_change("change2".to_string()).await;
        assert_eq!(manager.get_pending_count().await, 2);

        manager.incremental_sync().await.unwrap();
        assert_eq!(manager.get_pending_count().await, 0);
    }
}
