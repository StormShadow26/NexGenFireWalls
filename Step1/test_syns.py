#!/usr/bin/env python3
# test_syns.py -- send bursts of SYNs to trigger rate-limiter
from scapy.all import IP, TCP, send
import time, sys

# target: use your machine IP here (e.g. 192.168.1.10) or 127.0.0.1 for loopback
target = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
src_base = "10.0.0."   # used to create multiple different source IPs
sport = 12345
dport = 80

def send_burst(spoofed_src, count=200, fast=True):
    pkt = IP(src=spoofed_src, dst=target)/TCP(sport=sport, dport=dport, flags="S")
    if fast:
        for i in range(count):
            send(pkt, verbose=False)
    else:
        for i in range(count):
            send(pkt, verbose=False)
            time.sleep(0.01)

if __name__ == "__main__":
    print("Sending outgoing-like SYNs (source = local IPs) ...")
    # generate spoofed sources that look remote to trigger incoming drops when your capture sees them as incoming
    for i in range(1,6):
        s = src_base + str(10 + i)
        send_burst(s, count=120)   # 120 SYNs from same src -> should trip rate limiter
    print("Done.")

