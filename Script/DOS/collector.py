#!/usr/bin/env python3
"""
collector.py - UPDATED to correctly parse 'xfer.src2dst_packets' and 'xfer.dst2src_packets'.

Usage:
  python3 collector.py ndpi_output_20251107_223619.json
  python3 collector.py /path/to/ndpi_json_dir

Behavior:
- Creates/ensures future-proof SQLite schema (ndpi.db).
- Parses JSON array or NDJSON safely.
- Normalizes flow ids (uuid5 for numeric/other).
- Computes flow_fingerprint and ja3/ja4 short hashes.
- Inserts flows, creates VPN/Tor alerts.
- Touches /tmp/ndpi_last_ingest after successful commit.
- Records blocked IPs to blocked_ips table when blocking via nft.
"""
import sys, os, json, sqlite3, glob, uuid, re, hashlib, time, subprocess
from typing import Iterable, Dict, Any, Optional
from collections import deque, defaultdict

DB_PATH = "ndpi.db"
BATCH_COMMIT = 200
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
VPN_NAMES = ("tor", "wireguard", "openvpn", "vpn", "tailscale", "forticlient", "ultrasurf", "wg", "wg0")

def find_json_input(path: str) -> Optional[str]:
    if os.path.isfile(path):
        return path
    if os.path.isdir(path):
        c = sorted(glob.glob(os.path.join(path, "ndpi_output_*.json")), key=os.path.getmtime)
        if c: return c[-1]
    c = sorted(glob.glob("ndpi_output_*.json"), key=os.path.getmtime)
    return c[-1] if c else None

def iter_json_objects(fn: str) -> Iterable[Dict[str,Any]]:
    with open(fn, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read().strip()
        if not text:
            return
        try:
            data = json.loads(text)
            if isinstance(data, list):
                for o in data: yield o
                return
            if isinstance(data, dict):
                if "flows" in data and isinstance(data["flows"], list):
                    for o in data["flows"]: yield o
                    return
                yield data
                return
        except Exception:
            pass
    with open(fn, "r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            ln = ln.strip()
            if not ln: continue
            try:
                yield json.loads(ln)
            except Exception:
                continue

def safe_get(d: Dict[str,Any], *keys, default=None):
    for k in keys:
        if k is None: continue
        if isinstance(k, str) and '.' in k:
            cur = d
            ok = True
            for part in k.split('.'):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    ok = False; break
            if ok: return cur
        else:
            if k in d: return d[k]
    return default

def normalize_flow_id(raw: Any) -> str:
    if raw is None: return str(uuid.uuid4())
    s = str(raw)
    if UUID_RE.match(s):
        return s
    try:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, s))
    except Exception:
        return str(uuid.uuid4())

def short_hash(s: Optional[str]) -> Optional[str]:
    if not s: return None
    h = hashlib.sha1(s.encode()).hexdigest()
    return h[:16]

# ---------- DDoS mitigation additions ----------
PKTS_WINDOW_SECONDS = 5      # sliding window length (seconds)
PKTS_THRESHOLD = 500         # packet events in window -> block
CONN_WINDOW_SECONDS = 5
CONN_THRESHOLD = 100         # new connection events in window -> block
BLOCK_TIMEOUT = "10m"        # for nftables timeout
BLOCK_TIMEOUT_SECONDS = 10 * 60  # keep a numeric default (10 minutes)

_pkt_times = defaultdict(deque)   # src_ip -> deque(timestamps)
_conn_times = defaultdict(deque)  # src_ip -> deque(timestamps)
_blocked = {}                      # src_ip -> expiry_timestamp (in-memory)

def _parse_timeout_seconds(t):
    if not t: return 0
    t = str(t)
    if t.endswith('m'): return int(t[:-1]) * 60
    if t.endswith('s'): return int(t[:-1])
    return int(t)

def ensure_blocked_table(conn):
    """Create blocked_ips table if not exists."""
    sql = """
    CREATE TABLE IF NOT EXISTS blocked_ips (
        ip TEXT PRIMARY KEY,
        blocked_at INTEGER NOT NULL,
        expires_at INTEGER NOT NULL,
        reason TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_blocked_ips_expires_at ON blocked_ips (expires_at);
    """
    conn.executescript(sql)
    conn.commit()

def db_record_block(conn, ip, reason=None, timeout_seconds=BLOCK_TIMEOUT_SECONDS):
    """Record blocked IP into blocked_ips table."""
    now = int(time.time())
    exp = now + int(timeout_seconds)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO blocked_ips (ip, blocked_at, expires_at, reason) VALUES (?,?,?,?)",
            (ip, now, exp, reason or "auto-ddos-block"),
        )
        conn.commit()
    except Exception as e:
        print("db_record_block failed:", e)

def db_cleanup_expired_blocks(conn):
    """Delete expired blocked_ips rows from DB."""
    now = int(time.time())
    try:
        cur = conn.execute("DELETE FROM blocked_ips WHERE expires_at <= ?", (now,))
        if cur.rowcount:
            conn.commit()
            print(f"cleanup: removed {cur.rowcount} expired blocked_ips rows")
    except Exception as e:
        print("db_cleanup_expired_blocks failed:", e)

def nft_block_ip(conn, ip, reason=None, timeout_str=BLOCK_TIMEOUT):
    """Add ip to nftables ddos_block set and record it in DB."""
    cmd = ["nft", "add", "element", "inet", "filter", "ddos_block", "{ %s timeout %s }" % (ip, timeout_str)]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] BLOCKED {ip} for {timeout_str}")
        sec = _parse_timeout_seconds(timeout_str)
        _blocked[ip] = time.time() + sec
        # record in DB
        try:
            db_record_block(conn, ip, reason=reason, timeout_seconds=sec if sec>0 else BLOCK_TIMEOUT_SECONDS)
        except Exception as e:
            print("warning: failed to record block in DB:", e)
        return True
    except subprocess.CalledProcessError as e:
        print("nft add element failed:", e)
        return False
    except Exception as e:
        print("Failed to block via nft:", e)
        return False

def _maybe_block_for_row(row, conn):
    """Update sliding windows for this row and block via nft+DB if thresholds exceeded."""
    src = row.get("src_ip")
    if not src: return
    now = time.time()

    # approximate packets seen in this row
    try:
        p_src = int(row.get("packets_src2dst") or 0)
        p_dst = int(row.get("packets_dst2src") or 0)
        pkt_count = max(1, p_src + p_dst)
    except Exception:
        pkt_count = 1

    q = _pkt_times[src]
    # cap per-row pushes to avoid huge loops
    for _ in range(min(pkt_count, 50)):
        q.append(now)
    while q and q[0] < now - PKTS_WINDOW_SECONDS:
        q.popleft()

    # heuristics for new connection
    is_new_conn = False
    try:
        if row.get('duration') in (None, 0):
            is_new_conn = True
    except Exception:
        pass
    if is_new_conn:
        cq = _conn_times[src]
        cq.append(now)
        while cq and cq[0] < now - CONN_WINDOW_SECONDS:
            cq.popleft()

    # expire in-memory blocks
    if src in _blocked and time.time() > _blocked[src]:
        del _blocked[src]

    if src in _blocked:
        return

    if len(q) >= PKTS_THRESHOLD or len(_conn_times[src]) >= CONN_THRESHOLD:
        # reason text for DB
        reason = f"pkts={len(q)} conn={len(_conn_times[src])}"
        nft_block_ip(conn, src, reason=reason, timeout_str=BLOCK_TIMEOUT)
# ---------- end additions ----------

def ensure_schema(conn):
    cur = conn.cursor()
    cur.executescript(open("schema_v1.sql","r").read() if os.path.exists("schema_v1.sql") else """
PRAGMA foreign_keys=ON;
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS meta_schema ( key TEXT PRIMARY KEY, value TEXT );
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
""")
    conn.commit()

def transform(obj: Dict[str,Any], capture_id: Optional[str]) -> Dict[str,Any]:
    row = {}
    raw_flow_id = safe_get(obj, "flow_id", "flowId", "id", "flowIdHex", "flowid")
    row['flow_id'] = raw_flow_id
    row['normalized_flow_id'] = normalize_flow_id(raw_flow_id)
    row['capture_id'] = capture_id
    row['src_ip'] = safe_get(obj, "src_ip", "src", "source", "sa", "srcIp", "ip_src") or safe_get(obj,"source_ip")
    row['src_port'] = safe_get(obj, "src_port", "sport", "source_port")
    row['dst_ip'] = safe_get(obj, "dst_ip", "dst", "destination", "da", "dstIp") or safe_get(obj,"dest_ip")
    row['dst_port'] = safe_get(obj, "dst_port", "dport", "destination_port")
    row['ip_proto'] = safe_get(obj, "ip_proto", "proto_ip") or None
    row['ndpi_protocol'] = safe_get(obj, "proto", "ndpi_protocol", "protocol", "nDPIProtocol") or None
    row['app_category'] = safe_get(obj, "category", "app_category")
    row['breed'] = safe_get(obj, "breed")
    enc = safe_get(obj, "encrypted", "is_encrypted")
    if isinstance(enc, bool): row['encrypted'] = 1 if enc else 0
    else:
        stack = str(safe_get(obj,"stack", "proto_stack") or "")
        row['encrypted'] = 1 if "encrypt" in stack.lower() or "tls" in stack.lower() else 0
    row['first_seen'] = safe_get(obj, "first_seen", "firstSeen", "start_time", "ts")
    row['last_seen'] = safe_get(obj, "last_seen", "lastSeen", "end_time")
    row['duration'] = safe_get(obj, "duration")
    
    # --- START OF FIX: Using the correct nested keys from your JSON ---
    # Your JSON uses 'xfer.src2dst_packets' and 'xfer.dst2src_packets'
    row['packets_src2dst'] = safe_get(obj, "xfer.src2dst_packets", "packets_c2s","pkts_c2s","packets_src2dst") or 0
    row['packets_dst2src'] = safe_get(obj, "xfer.dst2src_packets", "packets_s2c","pkts_s2c","packets_dst2src") or 0
    
    # Also updating bytes fields to use the correct nested keys
    row['bytes_src2dst'] = safe_get(obj, "xfer.src2dst_bytes", "bytes_c2s", "bytes_src2dst") or 0
    row['bytes_dst2src'] = safe_get(obj, "xfer.dst2src_bytes", "bytes_s2c", "bytes_dst2src") or 0
    # --- END OF FIX ---
    
    row['sni'] = safe_get(obj, "sni","hostname","tls.sni","http.host")
    row['ja3'] = safe_get(obj,"ja3","ja3_fingerprint")
    row['ja3s'] = safe_get(obj,"ja3s","ja3s_fingerprint")
    row['ja4'] = safe_get(obj,"ja4")
    row['ja3_hash'] = short_hash(row['ja3'])
    row['ja4_hash'] = short_hash(row['ja4'])
    row['tls_version'] = safe_get(obj,"tls_version")
    row['cert_fingerprint'] = safe_get(obj,"cert_fingerprint","tls_cert_hash","cert_hash")
    risks = safe_get(obj, "ndpi_flow_risks", "flow_risks", "risks")
    try:
        row['ndpi_flow_risks'] = json.dumps(risks) if risks is not None else None
    except Exception:
        row['ndpi_flow_risks'] = str(risks) if risks is not None else None
    dns = safe_get(obj, "dns_hostnames","dns","dns_query","hostnames")
    try:
        if dns is None: row['dns_hostnames'] = None
        elif isinstance(dns,(list,tuple)): row['dns_hostnames']=json.dumps(dns)
        elif isinstance(dns,str): row['dns_hostnames']=json.dumps([h.strip() for h in dns.split(",") if h.strip()])
        else: row['dns_hostnames']=json.dumps(dns)
    except Exception:
        row['dns_hostnames']=None
    row['domain_entropy'] = safe_get(obj,"domain_entropy","entropy")
    row['dns_num_queries'] = safe_get(obj,"dns_num_queries","dns_queries")
    # flow fingerprint
    s = f"{row.get('src_ip') or ''}:{row.get('src_port') or ''}|{row.get('dst_ip') or ''}:{row.get('dst_port') or ''}|{int(row.get('first_seen') or 0)}"
    row['flow_fingerprint'] = hashlib.sha1(s.encode()).hexdigest()
    row['metadata'] = json.dumps({k:v for k,v in obj.items() if k not in ('flow_id',)})
    try:
        raw_text = json.dumps(obj, ensure_ascii=False)
        row['raw_ndpi'] = raw_text[:10000] if len(raw_text)>10000 else raw_text
    except Exception:
        row['raw_ndpi'] = None
    return row

def detect_vpn_tor(row: Dict[str,Any]) -> Optional[Dict[str,str]]:
    proto = (row.get("ndpi_protocol") or "").lower()
    breed = (row.get("breed") or "").lower()
    cat = (row.get("app_category") or "").lower()
    for name in VPN_NAMES:
        if name in proto or name in breed or name in cat:
            return {"rule": "VPN/Tor Protocol", "severity":"High", "description": f"Matched '{name}' in proto/breed/category"}
    sni = (row.get("sni") or "")
    if isinstance(sni,str) and "torproject" in sni.lower():
        return {"rule":"VPN/Tor SNI","severity":"High","description":f"SNI contains torproject: {sni}"}
    risks = row.get("ndpi_flow_risks")
    if risks:
        try:
            rs = json.dumps(json.loads(risks)).lower() if isinstance(risks,str) else str(risks).lower()
            if any(x in rs for x in ("tor","vpn","tailscale","wireguard")):
                return {"rule":"VPN/Tor flow_risks","severity":"High","description":"flow_risks mention VPN/Tor"}
        except Exception:
            pass
    return None

def insert_row(conn, row):
    cur = conn.cursor()
    cur.execute("""
    INSERT OR IGNORE INTO flows (
      flow_id, normalized_flow_id, capture_id, src_ip, src_port, dst_ip, dst_port, ip_proto,
      ndpi_protocol, app_category, breed, encrypted, first_seen, last_seen, duration,
      packets_src2dst, packets_dst2src, bytes_src2dst, bytes_dst2src, sni, ja3, ja3s, ja4,
      ja3_hash, ja4_hash, tls_version, cert_fingerprint, ndpi_flow_risks, dns_hostnames,
      domain_entropy, dns_num_queries, flow_fingerprint, metadata, raw_ndpi, created_at
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, strftime('%s','now'))
    """, (
        row.get('flow_id'), row.get('normalized_flow_id'), row.get('capture_id'),
        row.get('src_ip'), row.get('src_port'), row.get('dst_ip'), row.get('dst_port'),
        row.get('ip_proto'), row.get('ndpi_protocol'), row.get('app_category'), row.get('breed'),
        1 if row.get('encrypted') else 0,
        row.get('first_seen'), row.get('last_seen'), row.get('duration'),
        # Note: These values now come from 'xfer.src2dst_packets' etc., or default to 0
        row.get('packets_src2dst'), row.get('packets_dst2src'),
        row.get('bytes_src2dst'), row.get('bytes_dst2src'),
        row.get('sni'), row.get('ja3'), row.get('ja3s'), row.get('ja4'),
        row.get('ja3_hash'), row.get('ja4_hash'), row.get('tls_version'), row.get('cert_fingerprint'),
        row.get('ndpi_flow_risks'), row.get('dns_hostnames'),
        row.get('domain_entropy'), row.get('dns_num_queries'),
        row.get('flow_fingerprint'), row.get('metadata'), row.get('raw_ndpi')
    ))
    if cur.rowcount:
        alert = detect_vpn_tor(row)
        if alert:
            cur.execute("INSERT INTO alerts (normalized_flow_id, capture_id, rule_name, rule_version, severity, description, evidence, ts) VALUES (?,?,?,?,?,?,?,strftime('%s','now'))",
                        (row.get('normalized_flow_id'), row.get('capture_id'), alert['rule'], 'v1', alert['severity'], alert['description'], json.dumps({"proto": row.get('ndpi_protocol')})))
    return

def process_file(fn: str, conn):
    print("Processing", fn)
    capture_id = os.path.splitext(os.path.basename(fn))[0]
    count = 0
    cur_batch = 0
    for obj in iter_json_objects(fn):
        try:
            row = transform(obj, capture_id)
        except Exception as e:
            continue
        try:
            # run DDoS detector first (this may block immediately and record to DB)
            _maybe_block_for_row(row, conn)
            insert_row(conn, row)
            count += 1
            cur_batch += 1
            print("✓ ingested", row.get('normalized_flow_id'))
        except Exception as e:
            print("Insert error:", e)
        if cur_batch >= BATCH_COMMIT:
            conn.commit()
            # cleanup expired DB blocked rows periodically
            try:
                db_cleanup_expired_blocks(conn)
            except Exception:
                pass
            cur_batch = 0
    conn.commit()
    # final cleanup pass after processing file
    try:
        db_cleanup_expired_blocks(conn)
    except Exception as e:
        print("cleanup failed:", e)
    print("Finished processing", fn, "-> flows added:", count)
    return count

def main():
    if len(sys.argv) < 2:
        print("Usage: collector.py <file_or_dir>")
        sys.exit(1)
    path = sys.argv[1]
    found = find_json_input(path)
    if not found:
        print("No JSON found for:", path); sys.exit(2)
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    ensure_schema(conn)
    # ensure blocked_ips table exists
    ensure_blocked_table(conn)
    try:
        # Before re-ingesting, it is highly recommended to clear old, bad data.
        # Example: conn.execute("DELETE FROM flows;")
        # conn.commit()
        
        added = process_file(found, conn)
        try:
            open("/tmp/ndpi_last_ingest","w").close()
        except Exception:
            pass
        cur = conn.cursor()
        total = cur.execute("SELECT COUNT(*) FROM flows").fetchone()[0]
        print("✅ Total flows in DB:", total)
    finally:
        conn.close()

if __name__ == "__main__":
    main()