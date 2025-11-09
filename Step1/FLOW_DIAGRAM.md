# Packet Processing Flow Diagram

## Detailed Processing Pipeline

```
                    ┌────────────────────────────────────┐
                    │      NETWORK INTERFACES            │
                    │  (eth0, wlan0, lo, etc.)           │
                    └──────────────┬─────────────────────┘
                                   │
                                   │ Raw Packets
                                   ▼
                    ┌────────────────────────────────────┐
                    │         capture.c                   │
                    │  - BPF Filter (dst host = local)   │
                    │  - Multi-threaded capture          │
                    │  - Signal handling (Ctrl+C)        │
                    └──────────────┬─────────────────────┘
                                   │
                                   │ All Captured Packets
                                   ▼
                    ┌────────────────────────────────────┐
                    │      STAGE 1: PREPROCESSING         │
                    │         preprocess.c                │
                    │  ✓ Collect stats for ALL packets   │
                    │  ✓ Per-flow aggregation             │
                    │  ✓ Bidirectional tracking          │
                    └──────────────┬─────────────────────┘
                                   │
                                   │ All Packets (stats recorded)
                                   ▼
                    ┌────────────────────────────────────┐
                    │       STAGE 2: DENYLIST             │
                    │          denylist.c                 │
                    │  Check IP.txt & Ports.txt           │
                    └──────────────┬─────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                 DENIED                       ALLOWED
                    │                             │
                    ▼                             ▼
         ┌──────────────────────┐   ┌────────────────────────────────┐
         │  [CONSOLE OUTPUT]     │   │    STAGE 3: RATE LIMITING      │
         │  [DENYLIST DROP]      │   │       rate_limit.c             │
         │  Timestamp            │   │  Token Bucket Algorithm        │
         │  Src -> Dst           │   │  SYN Flood Detection          │
         │  Ports                │   └──────────────┬─────────────────┘
         │  Reason               │                  │
         │  Payload hex          │   ┌──────────────┴──────────────┐
         └───────────────────────┘   │                             │
                                  RATE LIMITED                  ALLOWED
                                     │                             │
                                     ▼                             ▼
                          ┌──────────────────────┐   ┌────────────────────────────────┐
                          │  [CONSOLE OUTPUT]     │   │  STAGE 4: MALFORMED CHECK      │
                          │  [RATE-LIMIT DROP]    │   │        malformed.c             │
                          │  Timestamp            │   │  RFC Compliance Checks:        │
                          │  Src:Port -> Dst:Port │   │  - IP header validation        │
                          │  Reason: SYN_RATE     │   │  - TCP/UDP checksums          │
                          │  Tokens remaining     │   │  - Invalid flags (SYN+FIN)    │
                          └───────────────────────┘   │  - Fragment anomalies         │
                                                      └──────────────┬─────────────────┘
                                                                     │
                                                      ┌──────────────┴──────────────┐
                                                      │                             │
                                                  MALFORMED                      VALID
                                                      │                             │
                                                      ▼                             ▼
                                           ┌──────────────────────┐   ┌────────────────────┐
                                           │  [CONSOLE OUTPUT]     │   │   PACKET ACCEPTED  │
                                           │  [MALFORMED DROP]     │   │                    │
                                           │  Timestamp            │   │  ✓ Counted in      │
                                           │  Src -> Dst           │   │    preprocess stats│
                                           │  Ports                │   │                    │
                                           │  Reason: bad_checksum │   │  ✓ Forwarded to    │
                                           │  Payload hex          │   │    application     │
                                           └───────────┬───────────┘   └────────────────────┘
                                                       │
                                                       ▼
                                           ┌──────────────────────┐
                                           │  [CSV FILE]           │
                                           │  malformed.csv        │
                                           │  - Timestamp (ISO)    │
                                           │  - Capture length     │
                                           │  - Payload preview    │
                                           └───────────────────────┘


                                    ┌────────────────────────────────────┐
                                    │       FINAL OUTPUT                  │
                                    └────────────────────────────────────┘
                                                       │
                                        ┌──────────────┴──────────────┐
                                        │                             │
                                        ▼                             ▼
                           ┌────────────────────────┐   ┌────────────────────────┐
                           │  summary_batch_1.csv    │   │   CONSOLE LOGS         │
                           │  ────────────────────   │   │  ──────────────────    │
                           │  Per-flow statistics:   │   │  All dropped packets:  │
                           │  - Src/Dst IPs          │   │  - Denylist drops      │
                           │  - Src/Dst Ports        │   │  - Rate limit drops    │
                           │  - Protocol             │   │  - Malformed drops     │
                           │  - Bytes sent/received  │   │                        │
                           │  - Packets sent/received│   │  Real-time monitoring  │
                           │  - Duration             │   │  of security events    │
                           └────────────────────────┘   └────────────────────────┘
```

## Key Features

### 1. **Complete Coverage**
   - ALL packets are processed by preprocess.c (even if later dropped)
   - Statistics include both valid and invalid traffic

### 2. **Multi-Layer Filtering**
   - Layer 1: Denylist (IP/Port blacklist)
   - Layer 2: Rate Limiting (DoS prevention)
   - Layer 3: RFC Validation (malformed packet detection)

### 3. **Comprehensive Logging**
   - Console: Real-time drop notifications
   - CSV: Persistent logs for analysis
   - Metrics: Aggregated traffic statistics

### 4. **Security Focus**
   - BPF filtering (only local traffic)
   - Multi-threaded for performance
   - Thread-safe file operations
   - Graceful shutdown handling

## Output Examples

### Console Output for Dropped Packet
```
[DENYLIST DROP] 2025-11-08T21:12:34.123456  192.168.1.100 -> 10.0.0.1  192.168.1.100/12345 -> 10.0.0.1/443  proto=TCP  reason=deny_ip  payload="45 00 00 3c 1c 46 40 00 40 06 b1 e6..."
```

### CSV Output (summary_batch_1.csv)
```csv
src_ip,dst_ip,src_port,dst_port,protocol,bytes_sent,bytes_received,pkts_sent,pkts_received,elapsed_seconds
192.168.1.50,10.0.0.1,54321,80,TCP,1500,3000,10,15,2.456789
```

### CSV Output (malformed.csv)
```csv
timestamp,caplen,payload_preview
2025-11-08T21:12:34.123456Z,66,"45 00 00 3c 1c 46 40 00 40 06 00 00 c0 a8 01 32..."
```

## Statistics

After capture completes:
- Total packets captured: N
- Valid packets: X
- Dropped by denylist: Y
- Dropped by rate limiter: Z
- Malformed packets: M

Where: N = X + Y + Z + M (all packets accounted for)
