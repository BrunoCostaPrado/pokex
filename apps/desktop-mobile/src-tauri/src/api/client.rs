use crate::db::models::{CardImages, NewCard, NewSet};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct ApiClient {
    client: Client,
    base_url: String,
}

impl ApiClient {
    pub fn new(base_url: String) -> Self {
        Self {
            client: Client::new(),
            base_url,
        }
    }

    pub async fn get_sets(&self, limit: u32, skip: u32) -> Result<Vec<ApiSet>, ApiError> {
        let url = format!("{}/sets?limit={}&skip={}", self.base_url, limit, skip);
        let response = self.client.get(&url).send().await?;
        if !response.status().is_success() {
            return Err(ApiError::RequestFailed(response.status().to_string()));
        }
        Ok(response.json().await?)
    }

    pub async fn get_cards(
        &self,
        set_id: Option<&str>,
        limit: u32,
        skip: u32,
    ) -> Result<Vec<ApiCard>, ApiError> {
        let mut url = format!("{}/cards?limit={}&skip={}", self.base_url, limit, skip);
        if let Some(set_id) = set_id {
            url.push_str(&format!("&set_id={}", set_id));
        }
        let response = self.client.get(&url).send().await?;
        if !response.status().is_success() {
            return Err(ApiError::RequestFailed(response.status().to_string()));
        }
        Ok(response.json().await?)
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ApiSet {
    pub id: String,
    pub name: String,
    pub series: Option<String>,
    pub release_date: Option<String>,
    pub total_cards: Option<i32>,
    pub logo_url: Option<String>,
    pub symbol_url: Option<String>,
    pub created_at: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ApiCard {
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
    pub prices: Option<HashMap<String, PriceInfo>>,
    pub created_at: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PriceInfo {
    pub normal: Option<f64>,
    pub holo: Option<f64>,
    #[serde(rename = "reverseHolo")]
    pub reverse_holo: Option<f64>,
}

#[derive(Debug, thiserror::Error)]
pub enum ApiError {
    #[error("Request failed: {0}")]
    RequestFailed(String),
    #[error("Network error: {0}")]
    Network(#[from] reqwest::Error),
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

impl serde::Serialize for ApiError {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        #[derive(serde::Serialize)]
        #[serde(tag = "type")]
        enum ApiErrorSer<'a> {
            RequestFailed { message: &'a str },
            Network { message: String },
            Io { message: String },
            Serialization { message: String },
        }
        let ser = match self {
            ApiError::RequestFailed(s) => ApiErrorSer::RequestFailed { message: s },
            ApiError::Network(e) => ApiErrorSer::Network {
                message: e.to_string(),
            },
            ApiError::Io(e) => ApiErrorSer::Io {
                message: e.to_string(),
            },
            ApiError::Serialization(e) => ApiErrorSer::Serialization {
                message: e.to_string(),
            },
        };
        ser.serialize(serializer)
    }
}

impl From<ApiSet> for NewSet {
    fn from(s: ApiSet) -> Self {
        Self {
            id: s.id,
            name: s.name,
            series: s.series,
            release_date: s.release_date,
            total_cards: s.total_cards,
            logo_url: s.logo_url,
            symbol_url: s.symbol_url,
            created_at: s.created_at,
            updated_at: chrono::Utc::now().to_rfc3339(),
            synced_at: chrono::Utc::now().to_rfc3339(),
        }
    }
}

impl From<ApiCard> for NewCard {
    fn from(c: ApiCard) -> Self {
        let prices = c
            .prices
            .map(|p| serde_json::to_value(p).unwrap_or(serde_json::Value::Null));

        Self {
            id: c.id,
            set_id: c.set_id,
            number: c.number,
            name: c.name,
            rarity: c.rarity,
            hp: c.hp,
            types: c.types,
            subtypes: c.subtypes,
            supertype: c.supertype,
            images: c.images,
            tcgplayer_url: c.tcgplayer_url,
            cardmarket_url: c.cardmarket_url,
            prices,
            created_at: c.created_at,
            updated_at: chrono::Utc::now().to_rfc3339(),
            synced_at: chrono::Utc::now().to_rfc3339(),
        }
    }
}
