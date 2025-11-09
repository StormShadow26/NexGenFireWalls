PRAGMA foreign_keys=ON;
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS meta_schema (
  key TEXT PRIMARY KEY,
  value TEXT
);
INSERT OR REPLACE INTO meta_schema(key,value) VALUES('schema_version','1');

CREATE TABLE IF NOT EXISTS flows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  flow_id TEXT,
  normalized_flow_id TEXT UNIQUE,
  capture_id TEXT,
  src_ip TEXT,
  src_port INTEGER,
  dst_ip TEXT,
  dst_port INTEGER,
  ip_proto INTEGER,
  ndpi_protocol TEXT,
  app_category TEXT,
  breed TEXT,
  encrypted INTEGER DEFAULT 0,
  first_seen REAL,
  last_seen REAL,
  duration REAL,
  packets_src2dst INTEGER,
  packets_dst2src INTEGER,
  bytes_src2dst INTEGER,
  bytes_dst2src INTEGER,
  sni TEXT,
  ja3 TEXT,
  ja3s TEXT,
  ja4 TEXT,
  ja3_hash TEXT,
  ja4_hash TEXT,
  tls_version TEXT,
  cert_fingerprint TEXT,
  ndpi_flow_risks TEXT,
  dns_hostnames TEXT,
  domain_entropy REAL,
  dns_num_queries INTEGER,
  flow_fingerprint TEXT,
  tags TEXT,
  metadata TEXT,
  raw_ndpi TEXT,
  created_at REAL DEFAULT (strftime('%s','now')),
  updated_at REAL DEFAULT (strftime('%s','now'))
);

CREATE INDEX IF NOT EXISTS idx_flows_first_seen ON flows(first_seen);
CREATE INDEX IF NOT EXISTS idx_flows_created_at ON flows(created_at);
CREATE INDEX IF NOT EXISTS idx_flows_normalized_flow_id ON flows(normalized_flow_id);
CREATE INDEX IF NOT EXISTS idx_flows_src_ip ON flows(src_ip);
CREATE INDEX IF NOT EXISTS idx_flows_dst_ip ON flows(dst_ip);
CREATE INDEX IF NOT EXISTS idx_flows_proto ON flows(ndpi_protocol);

CREATE TABLE IF NOT EXISTS alerts (
  alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
  normalized_flow_id TEXT,
  capture_id TEXT,
  rule_name TEXT,
  rule_version TEXT,
  severity TEXT,
  description TEXT,
  evidence TEXT,
  ts REAL DEFAULT (strftime('%s','now')),
  FOREIGN KEY(normalized_flow_id) REFERENCES flows(normalized_flow_id)
);

CREATE INDEX IF NOT EXISTS idx_alerts_flow ON alerts(normalized_flow_id);

CREATE TABLE IF NOT EXISTS host_baseline (
  host_ip TEXT PRIMARY KEY,
  avg_bytes REAL,
  avg_flows_per_min REAL,
  last_updated REAL DEFAULT (strftime('%s','now'))
);
