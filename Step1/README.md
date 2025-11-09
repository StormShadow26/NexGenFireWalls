# Packet Capture and Analysis Tool

## Overview
This tool captures network packets from all interfaces on the server and processes them through multiple filtering stages.

## Packet Processing Pipeline

The packet flow follows this order:
1. **capture.c** - Captures packets from all network interfaces
2. **preprocess.h/c** - Collects statistics for ALL packets
3. **denylist.h/c** - Filters blocked IPs and ports
4. **rate_limit.h/c** - Prevents SYN flood attacks
5. **malformed.h/c** - Detects RFC-violating packets
6. **CSV Output** - Generates summary reports

```
Packet Flow:
┌──────────┐
│ capture  │ → All interfaces
└────┬─────┘
     │
     ▼
┌──────────┐
│preprocess│ → Stats for ALL packets
└────┬─────┘
     │
     ▼
┌──────────┐
│ denylist │ → Drop blocked IPs/ports → [CONSOLE]
└────┬─────┘
     │ (allowed)
     ▼
┌──────────┐
│rate_limit│ → Drop SYN floods → [CONSOLE]
└────┬─────┘
     │ (allowed)
     ▼
┌──────────┐
│malformed │ → Drop invalid packets → [CONSOLE + malformed.csv]
└────┬─────┘
     │ (valid)
     ▼
   [ACCEPT]
```

## Compilation

```bash
gcc -Wall -Wextra -std=gnu11 capture.c preprocess.c denylist.c rate_limit.c malformed.c malformed_log.c -o capture -lpcap -lpthread
```

## Configuration Files

### IP.txt
List of blocked IP addresses (one per line):
```
192.168.1.100
10.0.0.50
```

### Ports.txt
List of blocked ports (one per line):
```
23
1433
3306
```

## Usage

### Basic Usage
```bash
sudo ./capture
```

### Capture from Specific Interface
```bash
sudo ./capture -i eth0
```

### Capture N Packets
```bash
sudo ./capture -n 100
```

### Combined Options
```bash
sudo ./capture -i eth0 -n 50
```

## Command Line Options

- `-i <interface>` - Capture from specific network interface
- `-n <count>` - Capture N packets before stopping (default: 50)
- `-h` - Show help message

## Output Files

### summary_batch_1.csv
Contains aggregated statistics for valid packets:
- Source/Destination IPs
- Source/Destination ports
- Protocol (TCP/UDP/ICMP)
- Bytes sent/received
- Packets sent/received
- Elapsed time

### malformed.csv
Logs all malformed packets with:
- Timestamp (ISO format)
- Capture length
- Payload preview (hex)

## Console Output

Dropped packets are logged to console with detailed information:

### Denylist Drops
```
[DENYLIST DROP] 2025-11-08T21:12:34.123456  192.168.1.100 -> 10.0.0.1  TCP/12345 -> 443  reason=deny_ip
```

### Rate Limit Drops
```
[RATE-LIMIT DROP] 2025-11-08T21:12:34.123456  192.168.1.50:54321 -> 10.0.0.1:80  SYN flood detected
```

### Malformed Drops
```
[MALFORMED DROP] 2025-11-08T21:12:34.123456  192.168.1.75 -> 10.0.0.1  TCP/23456 -> 80  reason=bad_checksum
```

## Requirements

- Linux operating system
- libpcap development library
- pthread library
- Root/sudo privileges (for packet capture)

### Installing Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get install libpcap-dev
```

**CentOS/RHEL:**
```bash
sudo yum install libpcap-devel
```

## Module Descriptions

### capture.c
- Captures packets from all IP-capable interfaces
- Applies BPF filter to only capture packets destined to this host
- Multi-threaded (one thread per interface)
- Handles SIGINT/SIGTERM for graceful shutdown

### preprocess.c
- Aggregates per-flow statistics
- Tracks bidirectional traffic
- Counts bytes and packets sent/received
- Generates summary CSV at the end

### denylist.c
- Loads blocked IPs from IP.txt
- Loads blocked ports from Ports.txt
- Drops matching packets
- Logs drops to console with hex payload preview

### rate_limit.c
- Implements token bucket algorithm
- Detects SYN flood attacks
- Configurable rate and burst capacity
- Supports incoming/outgoing/both modes
- Logs drops to console

### malformed.c
- RFC compliance checks:
  - IP header validation (IHL, checksum, total length)
  - TCP header validation (offset, flags, checksum)
  - UDP header validation (length)
  - Fragmentation anomaly detection
  - Invalid flag combinations (SYN+FIN)
- Logs drops to console and CSV file

### malformed_log.c
- Thread-safe CSV writer for malformed packets
- Atomic file operations with fsync
- Hex dump of payload preview

## Troubleshooting

### Permission Denied
Run with sudo:
```bash
sudo ./capture
```

### No Packets Captured
- Check if interfaces are up: `ip link show`
- Verify BPF filter is not too restrictive
- Try specific interface with `-i` option

### Compilation Errors
Ensure all dependencies are installed:
```bash
gcc --version
pkg-config --exists libpcap && echo "libpcap found"
```

## License
This project is provided as-is for educational and security monitoring purposes.
