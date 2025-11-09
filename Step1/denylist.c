/*
 * denylist.c
 * Loads dangerous IPs & ports from IP.txt / Ports.txt and logs denied packets to stdout.
 */

#include "denylist.h"
#include <stdio.h>
#include <string.h>
#include <arpa/inet.h>
#include <netinet/ip.h>
#include <netinet/tcp.h>
#include <netinet/udp.h>
#include <net/ethernet.h>
#include <stdlib.h>
#include <time.h>
#include <ctype.h>

#define MAX_DENY_IPS   1024
#define MAX_DENY_PORTS 1024

static char deny_ips[MAX_DENY_IPS][INET_ADDRSTRLEN];
static int deny_ip_count = 0;
static uint16_t deny_ports[MAX_DENY_PORTS];
static int deny_port_count = 0;

/* Drop counters */
static int deny_ip_drops = 0;
static int deny_port_drops = 0;

/* Helper: trim newline and spaces (in-place) */
static void trim(char *s) {
    char *p = s;
    while (*p && isspace((unsigned char)*p)) p++;
    if (p != s) memmove(s, p, strlen(p) + 1);
    char *end = s + strlen(s) - 1;
    while (end >= s && isspace((unsigned char)*end)) { *end = '\0'; --end; }
}

/* Load IP list from IP.txt */
static void load_deny_ips(void) {
    FILE *f = fopen("IP.txt", "r");
    if (!f) {
        printf("[Denylist] Warning: IP.txt not found. No IPs loaded.\n");
        return;
    }
    char line[128];
    while (fgets(line, sizeof(line), f)) {
        trim(line);
        if (strlen(line) == 0) continue;
        if (deny_ip_count < MAX_DENY_IPS) {
            strncpy(deny_ips[deny_ip_count], line, INET_ADDRSTRLEN);
            deny_ips[deny_ip_count][INET_ADDRSTRLEN - 1] = '\0';
            deny_ip_count++;
        }
    }
    fclose(f);
    printf("[Denylist] Loaded %d blocked IP(s)\n", deny_ip_count);
}

/* Load port list from Ports.txt */
static void load_deny_ports(void) {
    FILE *f = fopen("Ports.txt", "r");
    if (!f) {
        printf("[Denylist] Warning: Ports.txt not found. No ports loaded.\n");
        return;
    }
    char line[64];
    while (fgets(line, sizeof(line), f)) {
        trim(line);
        if (strlen(line) == 0) continue;
        int port = atoi(line);
        if (port > 0 && port <= 65535 && deny_port_count < MAX_DENY_PORTS) {
            deny_ports[deny_port_count++] = (uint16_t)port;
        }
    }
    fclose(f);
    printf("[Denylist] Loaded %d blocked port(s)\n", deny_port_count);
}

/* small hex prefix (first n bytes) as space-separated hex in buffer */
static void hex_prefix_to_str(const u_char *data, size_t len, size_t prefix, char *out, size_t outlen) {
    size_t up = (len < prefix) ? len : prefix;
    size_t p = 0;
    for (size_t i = 0; i < up && p + 3 < outlen; ++i) {
        int w = snprintf(out + p, outlen - p, "%02x", data[i]);
        p += (w > 0) ? w : 0;
        if (i + 1 < up && p + 2 < outlen) {
            out[p++] = ' ';
        }
    }
    out[p] = '\0';
}

/* timestamp formatting like 2025-11-08T21:12:34.123456 */
static void timestamp_to_str(const struct pcap_pkthdr *h, char *out, size_t outlen) {
    struct tm tm;
    time_t tsec = h->ts.tv_sec;
    localtime_r(&tsec, &tm);
    char base[64];
    strftime(base, sizeof(base), "%Y-%m-%dT%H:%M:%S", &tm);
    snprintf(out, outlen, "%s.%06ld", base, (long)h->ts.tv_usec);
}

/* Determine if IP matches denylist */
static int is_denied_ip(const char *ip) {
    for (int i = 0; i < deny_ip_count; ++i)
        if (strcmp(ip, deny_ips[i]) == 0)
            return 1;
    return 0;
}

/* Determine if port matches denylist */
static int is_denied_port(uint16_t port) {
    for (int i = 0; i < deny_port_count; ++i)
        if (port == deny_ports[i])
            return 1;
    return 0;
}

/* Public init: load lists */
void denylist_init(void) {
    deny_ip_count = deny_port_count = 0;
    load_deny_ips();
    load_deny_ports();
}

/* print drop info to terminal */
static void print_deny(const struct pcap_pkthdr *header, const char *src_ip, const char *dst_ip,
                       uint16_t src_port, uint16_t dst_port, const char *proto_str, const char *reason,
                       const u_char *payload, size_t payload_len) {
    char tsbuf[64];
    timestamp_to_str(header, tsbuf, sizeof(tsbuf));
    char hexbuf[256];
    hex_prefix_to_str(payload, payload_len, 24, hexbuf, sizeof(hexbuf));

    printf("🚫 [DENYLIST DROP] %s | %s:%u → %s:%u | proto=%s | reason=%s | payload=%s\n",
           tsbuf, src_ip, (unsigned)src_port, dst_ip, (unsigned)dst_port,
           proto_str, reason, hexbuf);
}

/* check_denylist: returns true to allow, false to drop (and print) */
bool check_denylist(const struct pcap_pkthdr *header, const u_char *packet) {
    if (header->caplen < sizeof(struct ether_header))
        return true;

    const struct ether_header *eth = (const struct ether_header *)packet;
    if (ntohs(eth->ether_type) != ETHERTYPE_IP)
        return true; // only IPv4 checks here

    const struct ip *ip_hdr = (const struct ip *)(packet + sizeof(struct ether_header));
    char src_ip[INET_ADDRSTRLEN], dst_ip[INET_ADDRSTRLEN];
    inet_ntop(AF_INET, &ip_hdr->ip_src, src_ip, sizeof(src_ip));
    inet_ntop(AF_INET, &ip_hdr->ip_dst, dst_ip, sizeof(dst_ip));

    uint16_t dst_port = 0, src_port = 0;
    uint8_t proto = ip_hdr->ip_p;
    size_t ip_hdr_bytes = (size_t)ip_hdr->ip_hl * 4;
    const u_char *l4 = packet + sizeof(struct ether_header) + ip_hdr_bytes;
    size_t l4_len = (header->caplen > (sizeof(struct ether_header) + ip_hdr_bytes)) ?
                    (header->caplen - (sizeof(struct ether_header) + ip_hdr_bytes)) : 0;

    if (proto == IPPROTO_TCP && l4_len >= sizeof(struct tcphdr)) {
        const struct tcphdr *tcp = (const struct tcphdr *)l4;
        dst_port = ntohs(tcp->th_dport);
        src_port = ntohs(tcp->th_sport);
    } else if (proto == IPPROTO_UDP && l4_len >= sizeof(struct udphdr)) {
        const struct udphdr *udp = (const struct udphdr *)l4;
        dst_port = ntohs(udp->uh_dport);
        src_port = ntohs(udp->uh_sport);
    }

    /* IP-based deny */
    if (is_denied_ip(src_ip) || is_denied_ip(dst_ip)) {
        deny_ip_drops++;
        print_deny(header, src_ip, dst_ip, src_port, dst_port,
                   (proto == IPPROTO_TCP) ? "TCP" : (proto == IPPROTO_UDP) ? "UDP" : "IP",
                   "deny_ip", l4, l4_len);
        return false;
    }

    /* Port-based deny */
    if (dst_port != 0 && is_denied_port(dst_port)) {
        deny_port_drops++;
        print_deny(header, src_ip, dst_ip, src_port, dst_port,
                   (proto == IPPROTO_TCP) ? "TCP" : (proto == IPPROTO_UDP) ? "UDP" : "IP",
                   "deny_port", l4, l4_len);
        return false;
    }

    return true; /* allowed */
}

/* Report denylist statistics */
void denylist_report(void) {
    printf("\n📊 [DENYLIST STATISTICS]\n");
    printf("   Blocked by IP: %d packets\n", deny_ip_drops);
    printf("   Blocked by Port: %d packets\n", deny_port_drops);
    printf("   Total blocked: %d packets\n", deny_ip_drops + deny_port_drops);
}

