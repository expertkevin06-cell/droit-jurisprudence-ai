CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'admin',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    expires_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS access_requests (
    id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    contact TEXT,
    message TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    reviewed_at TEXT,
    reviewed_by TEXT,
    decision_reason TEXT
);

CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    target_request_id TEXT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    sent INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    actor TEXT,
    action TEXT,
    target TEXT,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS legal_sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    type TEXT NOT NULL,
    trust_level INTEGER NOT NULL,
    primary_source INTEGER DEFAULT 0,
    description TEXT
);

CREATE TABLE IF NOT EXISTS case_law (
    id TEXT PRIMARY KEY,
    court TEXT,
    decision_date TEXT,
    reference TEXT,
    themes TEXT NOT NULL,
    actors TEXT NOT NULL,
    summary TEXT NOT NULL,
    url TEXT,
    source_id TEXT,
    verified INTEGER DEFAULT 0
);
