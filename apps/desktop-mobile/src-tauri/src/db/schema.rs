#[allow(dead_code)]
pub struct Migration {
    pub version: u32,
    pub description: &'static str,
    pub sql: &'static str,
    pub kind: MigrationKind,
}

#[allow(dead_code)]
pub enum MigrationKind {
    Up,
    Down,
}

pub fn get_migrations() -> Vec<Migration> {
    vec![
        Migration {
            version: 1,
            description: "create_sets_table",
            sql: r#"
                CREATE TABLE IF NOT EXISTS sets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    series TEXT,
                    release_date TEXT,
                    total_cards INTEGER,
                    logo_url TEXT,
                    symbol_url TEXT,
                    created_at TEXT,
                    updated_at TEXT NOT NULL,
                    synced_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_sets_name ON sets(name);
            "#,
            kind: MigrationKind::Up,
        },
        Migration {
            version: 2,
            description: "create_cards_table",
            sql: r#"
                CREATE TABLE IF NOT EXISTS cards (
                    id TEXT PRIMARY KEY,
                    set_id TEXT NOT NULL,
                    number TEXT NOT NULL,
                    name TEXT NOT NULL,
                    rarity TEXT,
                    hp INTEGER,
                    types TEXT,
                    subtypes TEXT,
                    supertype TEXT,
                    images TEXT,
                    tcgplayer_url TEXT,
                    cardmarket_url TEXT,
                    prices TEXT,
                    created_at TEXT,
                    updated_at TEXT NOT NULL,
                    synced_at TEXT NOT NULL,
                    FOREIGN KEY (set_id) REFERENCES sets(id)
                );
                CREATE INDEX IF NOT EXISTS idx_cards_set_id ON cards(set_id);
                CREATE INDEX IF NOT EXISTS idx_cards_name ON cards(name);
            "#,
            kind: MigrationKind::Up,
        },
        Migration {
            version: 3,
            description: "create_collection_table",
            sql: r#"
                CREATE TABLE IF NOT EXISTS collection (
                    card_id TEXT PRIMARY KEY,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    condition TEXT NOT NULL DEFAULT 'near_mint',
                    acquired_price REAL,
                    acquired_date TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (card_id) REFERENCES cards(id)
                );
            "#,
            kind: MigrationKind::Up,
        },
        Migration {
            version: 4,
            description: "create_settings_table",
            sql: r#"
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            "#,
            kind: MigrationKind::Up,
        },
        Migration {
            version: 5,
            description: "insert_default_settings",
            sql: r#"
                INSERT OR IGNORE INTO settings (key, value) VALUES
                    ('offline_mode', 'true'),
                    ('auto_sync', 'false'),
                    ('api_url', 'http://10.0.2.2:8000'),
                    ('recognition_url', 'http://10.0.2.2:8000'),
                    ('sync_interval_minutes', '60');
            "#,
            kind: MigrationKind::Up,
        },
    ]
}
