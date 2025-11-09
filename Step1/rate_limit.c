/* rate_limit.c  (Updated)
 * Adds direction mode: incoming/outgoing/both.
 * Detects local IPv4 addresses at init (getifaddrs).
 * Default mode: RL_MODE_BOTH
 */

#include <time.h>
#include "rate_limit.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <arpa/inet.h>
#include <netinet/ip.h>
#include <netinet/tcp.h>
#include <net/ethernet.h>
#include <stdint.h>
#include <inttypes.h>
#include <stddef.h>
#include <stdbool.h>
#include <ifaddrs.h>
#include <net/if.h>
#include <unistd.h>

#define HASH_BUCKETS 4096
#define MAX_ENTRIES  65536
#define MAX_LOCAL_IPS 64

static double RATE_TOKENS_PER_SEC = 1;
static double BURST_CAPACITY      = 2;

/* direction mode, default BOTH */
static rl_mode_t rl_mode = RL_MODE_BOTH;

/* store local IPv4 addresses (network byte order) */
static uint32_t local_ips[MAX_LOCAL_IPS];
static int local_ip_count = 0;

/* same rl_entry implementation as before */
typedef struct rl_entry { uint32_t ip; double tokens; double last_ts; struct rl_entry *next; } rl_entry_t;
static rl_entry_t *buckets[HASH_BUCKETS];
static size_t entry_count = 0;
static uint64_t rl_allowed = 0;
static uint64_t rl_dropped = 0;

static double now_seconds(void) {
    struct timeval tv; gettimeofday(&tv, NULL);
    return (double)tv.tv_sec + (double)tv.tv_usec / 1e6;
}
static inline uint32_t ip_hash(uint32_t ip) {
    uint32_t x = ip; x ^= x >> 16; x *= 0x7feb352d; x ^= x >> 15; return x & (HASH_BUCKETS - 1);
}
static rl_entry_t *get_or_create_entry(uint32_t ip_net) {
    uint32_t idx = ip_hash(ip_net);
    for (rl_entry_t *cur = buckets[idx]; cur; cur = cur->next) if (cur->ip == ip_net) return cur;
    if (entry_count >= MAX_ENTRIES) return NULL;
    rl_entry_t *e = calloc(1, sizeof(rl_entry_t)); if (!e) return NULL;
    e->ip = ip_net; e->tokens = BURST_CAPACITY; e->last_ts = now_seconds();
    e->next = buckets[idx]; buckets[idx] = e; entry_count++; return e;
}

/* detect SYN without ACK and also return src/dst IPs (network order) */
static int is_tcp_syn_and_ips(const struct pcap_pkthdr *h, const u_char *pkt,
                              uint16_t *sp, uint16_t *dp, uint32_t *sip, uint32_t *dip)
{
    if (h->caplen < sizeof(struct ether_header)) return 0;
    const struct ether_header *eth = (const struct ether_header *)pkt;
    if (ntohs(eth->ether_type) != ETHERTYPE_IP) return 0;
    if (h->caplen < sizeof(struct ether_header) + sizeof(struct ip)) return 0;
    const struct ip *ip = (const struct ip *)(pkt + sizeof(struct ether_header));
    if (ip->ip_p != IPPROTO_TCP) return 0;
    size_t ihl = ip->ip_hl * 4; if (ihl < 20) return 0;
    size_t off = sizeof(struct ether_header) + ihl;
    if (h->caplen < off + sizeof(struct tcphdr)) return 0;
    const struct tcphdr *tcp = (const struct tcphdr *)(pkt + off);
    uint8_t flags = *((const uint8_t *)tcp + 13);
    int syn = flags & 0x02; int ack = flags & 0x10;
    if (!(syn && !ack)) return 0;
    if (sp) *sp = ntohs(tcp->th_sport);
    if (dp) *dp = ntohs(tcp->th_dport);
    if (sip) *sip = ip->ip_src.s_addr;
    if (dip) *dip = ip->ip_dst.s_addr;
    return 1;
}

/* check whether ip_net (network-order) is one of local IPs */
static bool is_local_ip(uint32_t ip_net) {
    for (int i = 0; i < local_ip_count; ++i) if (local_ips[i] == ip_net) return true;
    return false;
}

/* populate local IPv4 addrs at init */
static void populate_local_ips(void) {
    local_ip_count = 0;
    struct ifaddrs *ifap, *ifa;
    if (getifaddrs(&ifap) != 0) return;
    for (ifa = ifap; ifa && local_ip_count < MAX_LOCAL_IPS; ifa = ifa->ifa_next) {
        if (!ifa->ifa_addr) continue;
        if (ifa->ifa_addr->sa_family == AF_INET) {
            struct sockaddr_in *sa = (struct sockaddr_in *)ifa->ifa_addr;
            uint32_t a = sa->sin_addr.s_addr;
            /* ignore loopback unless you want to limit loopback traffic too */
            if ((ifa->ifa_flags & IFF_LOOPBACK) && 0) continue;
            local_ips[local_ip_count++] = a;
        }
    }
    freeifaddrs(ifap);
}

/* timestamp helpers */
static void ts_str(const struct pcap_pkthdr *h, char *out, size_t len) {
    time_t t = h->ts.tv_sec; struct tm *ti = localtime(&t); char base[64];
    if (ti) strftime(base, sizeof(base), "%Y-%m-%dT%H:%M:%S", ti); else snprintf(base, sizeof(base), "unknown");
    snprintf(out, len, "%s.%06ld", base, (long)h->ts.tv_usec);
}

/* hex snippet */
static void hex_prefix(const u_char *d, size_t n, char *o, size_t L) {
    size_t up = n < 24 ? n : 24, p = 0;
    for (size_t i = 0; i < up && p + 3 < L; ++i) {
        p += snprintf(o + p, L - p, "%02x", d[i]);
        if (i + 1 < up && p + 2 < L) o[p++] = ' ';
    }
    o[p] = 0;
}

/* public API implementations */
void rate_limit_init(void) {
    memset(buckets, 0, sizeof(buckets));
    entry_count = 0;
    rl_allowed = rl_dropped = 0;
    populate_local_ips();
    /* default rl_mode (BOTH) already set statically */
}

void rate_limit_set_params(double rate, double burst) {
    if (rate > 0) RATE_TOKENS_PER_SEC = rate;
    if (burst > 0) BURST_CAPACITY = burst;
}

void rate_limit_set_mode(rl_mode_t m) {
    rl_mode = m;
}

void rate_limit_report(void) {
    fprintf(stderr, "[RATE-LIMIT] entries=%zu allowed=%" PRIu64 " dropped=%" PRIu64 " local_ips=%d mode=%d\n",
            entry_count, rl_allowed, rl_dropped, local_ip_count, (int)rl_mode);
}

/* main check: respects rl_mode */
bool rate_limit_check(const struct pcap_pkthdr *h, const u_char *pkt) {
    uint16_t sp=0, dp=0; uint32_t sip=0, dip=0;
    if (!is_tcp_syn_and_ips(h, pkt, &sp, &dp, &sip, &dip)) { rl_allowed++; return true; }

    /* determine direction: if dip is local => packet destined to us => incoming;
       if sip is local => packet originates from local => outgoing.
       Note: on promiscuous interfaces, you may see both directions for same host. */
    bool pkt_incoming = is_local_ip(dip);
    bool pkt_outgoing = is_local_ip(sip);

    /* decide if we should enforce rate-limit on this packet according to mode */
    bool enforce = false;
    if (rl_mode == RL_MODE_BOTH) enforce = true;
    else if (rl_mode == RL_MODE_INCOMING && pkt_incoming) enforce = true;
    else if (rl_mode == RL_MODE_OUTGOING && pkt_outgoing) enforce = true;

    if (!enforce) { rl_allowed++; return true; }

    /* use source IP as the key (same as before) */
    rl_entry_t *e = get_or_create_entry(sip);
    if (!e) { rl_allowed++; return true; }

    double now = now_seconds();
    double add = (now - e->last_ts) * RATE_TOKENS_PER_SEC;
    if (add > 0) {
        e->tokens += add;
        if (e->tokens > BURST_CAPACITY) e->tokens = BURST_CAPACITY;
        e->last_ts = now;
    }

    if (e->tokens >= 1.0) { e->tokens -= 1.0; rl_allowed++; return true; }

    /* drop and print */
    rl_dropped++;
    char ts[64], src[INET_ADDRSTRLEN], dst[INET_ADDRSTRLEN], hx[128];
    ts_str(h, ts, sizeof(ts));
    struct in_addr a; a.s_addr = sip; inet_ntop(AF_INET, &a, src, sizeof(src));
    a.s_addr = dip; inet_ntop(AF_INET, &a, dst, sizeof(dst));
    hex_prefix(pkt, h->caplen, hx, sizeof(hx));

    printf("⚡ [RATE-LIMIT DROP] %s | %s:%u → %s:%u | tokens=%.2f/%.1f | reason=SYN_FLOOD\n",
           ts, src, sp, dst, dp, e->tokens, BURST_CAPACITY);

    return false;
}

