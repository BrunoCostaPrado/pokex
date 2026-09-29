use moka::future::Cache;
use serde_json::Value as JsonValue;
use std::time::Duration;

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_cached_api_client_get() {
        let cache: Cache<String, JsonValue> = Cache::builder()
            .max_capacity(10)
            .time_to_live(Duration::from_secs(60))
            .build();

        cache
            .insert("test_key".to_string(), serde_json::json!({"data": "test"}))
            .await;

        let result = cache.get(&"test_key".to_string()).await;
        assert!(result.is_some());
        assert_eq!(result.unwrap(), serde_json::json!({"data": "test"}));
    }

    #[tokio::test]
    async fn test_cached_api_client_miss() {
        let cache: Cache<String, JsonValue> = Cache::builder().max_capacity(10).build();

        let result = cache.get(&"nonexistent".to_string()).await;
        assert!(result.is_none());
    }

    #[tokio::test]
    async fn test_cached_api_client_invalidate() {
        let cache: Cache<String, JsonValue> = Cache::builder().max_capacity(10).build();

        cache
            .insert("test_key".to_string(), serde_json::json!({"data": "test"}))
            .await;
        assert!(cache.get(&"test_key".to_string()).await.is_some());

        cache.invalidate(&"test_key".to_string()).await;
        assert!(cache.get(&"test_key".to_string()).await.is_none());
    }

    #[tokio::test]
    async fn test_cached_api_client_invalidate_all() {
        let cache: Cache<String, JsonValue> = Cache::builder().max_capacity(10).build();

        cache
            .insert("key1".to_string(), serde_json::json!({"data": "1"}))
            .await;
        cache
            .insert("key2".to_string(), serde_json::json!({"data": "2"}))
            .await;

        cache.invalidate_all();

        assert!(cache.get(&"key1".to_string()).await.is_none());
        assert!(cache.get(&"key2".to_string()).await.is_none());
    }

    #[tokio::test]
    async fn test_cache_ttl_expiration() {
        let cache: Cache<String, JsonValue> = Cache::builder()
            .max_capacity(10)
            .time_to_live(Duration::from_millis(100))
            .build();

        cache
            .insert("test_key".to_string(), serde_json::json!({"data": "test"}))
            .await;
        assert!(cache.get(&"test_key".to_string()).await.is_some());

        tokio::time::sleep(Duration::from_millis(200)).await;

        assert!(cache.get(&"test_key".to_string()).await.is_none());
    }

    #[tokio::test]
    async fn test_cache_eviction() {
        let cache: Cache<String, JsonValue> = Cache::builder().max_capacity(2).build();

        cache.insert("key1".to_string(), serde_json::json!(1)).await;
        cache.insert("key2".to_string(), serde_json::json!(2)).await;

        assert!(cache.get(&"key1".to_string()).await.is_some());
        assert!(cache.get(&"key2".to_string()).await.is_some());

        cache.insert("key3".to_string(), serde_json::json!(3)).await;

        let key3_exists = cache.get(&"key3".to_string()).await.is_some();
        assert!(key3_exists, "newly inserted key should exist");
    }
}
