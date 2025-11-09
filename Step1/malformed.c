/*
 * malformed.c
 * Performs RFC-sanity checks and prints malformed packet drops to stdout.
 *
 * - Includes <stddef.h> for offsetof
 * - Uses bool consistently and matches malformed.h prototype
 */

#include "malformed.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <arpa/inet.h>
#include <netinet/ip.h>
#include <netinet/tcp.h>
#include <netinet/udp.h>
#include <net/ethernet.h>
#include <stdint.h>
#include <time.h>
#include <errno.h>
#include <stddef.h>   /* offsetof */
#include <stdbool.h>

/* Drop counter */
static int malformed_drops = 0;

/* timestamp formatting */
static void timestamp_to_str(const struct pcap_pkthdr *h, char *out, size_t outlen) {
    struct tm tm;
    time_t tsec = h->ts.tv_sec;
    localtime_r(&tsec, &tm);
    char base[64];
    strftime(base, sizeof(base), "%Y-%m-%dT%H:%M:%S", &tm);
    snprintf(out, outlen, "%s.%06ld", base, (long)h->ts.tv_usec);
}

/* hex prefix */
static void hex_prefix_to_str(const u_char *data, size_t len, size_t prefix, char *out, size_t outlen) {
    size_t up = (len < prefix) ? len : prefix;
    size_t p = 0;
    for (size_t i = 0; i < up && p + 3 < outlen; ++i) {
        int w = snprintf(out + p, outlen - p, "%02x", data[i]);
        p += (w > 0) ? w : 0;
        if (i + 1 < up && p + 2 < outlen) out[p++] = ' ';
    }
    out[p] = '\0';
}

/* print malformed drop */
static void print_malformed(const struct pcap_pkthdr *header, const char *src_ip, const char *dst_ip,
                            uint16_t src_port, uint16_t dst_port, const char *proto_str, const char *reason,
                            const u_char *payload, size_t payload_len) {
    malformed_drops++;  /* Increment counter */
    char tsbuf[64];
    timestamp_to_str(header, tsbuf, sizeof(tsbuf));
    char hexbuf[256];
    hex_prefix_to_str(payload, payload_len, 24, hexbuf, sizeof(hexbuf));

    printf("❌ [MALFORMED DROP] %s | %s:%u → %s:%u | proto=%s | reason=%s | payload=%s\n",
           tsbuf, src_ip, (unsigned)src_port, dst_ip, (unsigned)dst_port, proto_str, reason, hexbuf);
}

/* checksum calc (RFC 1071) */
static uint16_t checksum_calc(const uint8_t *data, size_t len) {
    uint32_t sum = 0;
    const uint16_t *ptr = (const uint16_t *)data;
    while (len > 1) {
        sum += ntohs(*ptr++);
        len -= 2;
    }
    if (len == 1) {
        uint8_t last = *((const uint8_t *)ptr);
        sum += (uint32_t)last << 8;
    }
    while (sum >> 16) sum = (sum & 0xffff) + (sum >> 16);
    return (uint16_t)(~sum & 0xffff);
}

/* ip checksum verify (best-effort) */
static bool ip_checksum_ok(const struct ip *ip_hdr) {
    size_t ihl_bytes = (size_t)ip_hdr->ip_hl * 4;
    if (ihl_bytes < 20) return false;
    uint8_t *buf = malloc(ihl_bytes);
    if (!buf) return true; /* conservatively treat as OK if memory fails */
    memcpy(buf, ip_hdr, ihl_bytes);
    buf[10] = 0; buf[11] = 0;
    uint16_t cs = checksum_calc(buf, ihl_bytes);
    free(buf);
    uint16_t orig = ntohs(ip_hdr->ip_sum);
    return cs == orig;
}

/* basic tcp checksum check (best-effort, returns true if matches or cannot compute) */
static bool tcp_checksum_ok(const struct ip *ip_hdr, const u_char *l4ptr, size_t l4_len) {
    if (l4_len < sizeof(struct tcphdr)) return true;
    uint16_t tcp_len = (uint16_t)l4_len;
    size_t buf_len = 12 + tcp_len;
    uint8_t *buf = malloc(buf_len);
    if (!buf) return true;
    /* pseudo header */
    memcpy(buf + 0, &ip_hdr->ip_src.s_addr, 4);
    memcpy(buf + 4, &ip_hdr->ip_dst.s_addr, 4);
    buf[8] = 0;
    buf[9] = ip_hdr->ip_p;
    uint16_t tcp_len_be = htons(tcp_len);
    memcpy(buf + 10, &tcp_len_be, 2);
    memcpy(buf + 12, l4ptr, tcp_len);

    /* compute offset of checksum field inside the TCP header within the constructed buffer */
    size_t tcp_ckoff = 12 + offsetof(struct tcphdr, th_sum);
    if (tcp_ckoff + 1 >= buf_len) { free(buf); return true; }
    buf[tcp_ckoff] = 0; buf[tcp_ckoff+1] = 0;

    uint16_t cs = checksum_calc(buf, buf_len);
    const struct tcphdr *tcp = (const struct tcphdr *)l4ptr;
    uint16_t orig = ntohs(tcp->th_sum);
    free(buf);
    return cs == orig;
}

/* fragmentation anomaly check */
static bool fragmentation_anomaly(const struct ip *ip_hdr, const struct pcap_pkthdr *header, const u_char *packet) {
    uint16_t ip_off = ntohs(ip_hdr->ip_off);
    uint16_t frag_offset = ip_off & IP_OFFMASK;
    uint16_t more_frags = ip_off & IP_MF;
    if (frag_offset == 0 && !more_frags) return false;
    size_t ip_hdr_len = (size_t)ip_hdr->ip_hl * 4;
    size_t l4_offset = sizeof(struct ether_header) + ip_hdr_len;
    if (header->caplen <= l4_offset) {
        return true;
    }
    return false;
}

/* initialize (no-op but kept for symmetry) */
void malformed_init(void) {
    /* nothing to init */
}

/* main malformed test: returns true == malformed (drop), false == ok */
bool is_malformed(const struct pcap_pkthdr *header, const u_char *packet) {
    if (header->caplen < sizeof(struct ether_header)) {
        print_malformed(header, "N/A", "N/A", 0, 0, "ETH", "too_short", packet, header->caplen);
        return true;
    }

    const struct ether_header *eth = (const struct ether_header *)packet;
    uint16_t ethertype = ntohs(eth->ether_type);
    if (ethertype != ETHERTYPE_IP) return false;

    if (header->caplen < sizeof(struct ether_header) + sizeof(struct ip)) {
        print_malformed(header, "N/A", "N/A", 0, 0, "IP", "truncated_ip_hdr", packet + sizeof(struct ether_header), header->caplen - sizeof(struct ether_header));
        return true;
    }

    const struct ip *ip_hdr = (const struct ip *)(packet + sizeof(struct ether_header));
    size_t ihl_bytes = (size_t)ip_hdr->ip_hl * 4;
    if (ihl_bytes < 20) {
        char src[INET_ADDRSTRLEN], dst[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &ip_hdr->ip_src, src, sizeof(src));
        inet_ntop(AF_INET, &ip_hdr->ip_dst, dst, sizeof(dst));
        print_malformed(header, src, dst, 0, 0, "IP", "invalid_ihl", packet + sizeof(struct ether_header), header->caplen - sizeof(struct ether_header));
        return true;
    }

    uint16_t total_len = ntohs(ip_hdr->ip_len);
    size_t wire_ip_bytes = header->caplen - sizeof(struct ether_header);
    if (total_len < ihl_bytes || wire_ip_bytes < ihl_bytes) {
        char src[INET_ADDRSTRLEN], dst[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &ip_hdr->ip_src, src, sizeof(src));
        inet_ntop(AF_INET, &ip_hdr->ip_dst, dst, sizeof(dst));
        print_malformed(header, src, dst, 0, 0, "IP", "truncated_total", packet + sizeof(struct ether_header), wire_ip_bytes);
        return true;
    }

    if (!ip_checksum_ok(ip_hdr)) {
        char src[INET_ADDRSTRLEN], dst[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &ip_hdr->ip_src, src, sizeof(src));
        inet_ntop(AF_INET, &ip_hdr->ip_dst, dst, sizeof(dst));
        print_malformed(header, src, dst, 0, 0, "IP", "bad_checksum", packet + sizeof(struct ether_header), ihl_bytes);
        return true;
    }

    if (fragmentation_anomaly(ip_hdr, header, packet)) {
        char src[INET_ADDRSTRLEN], dst[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &ip_hdr->ip_src, src, sizeof(src));
        inet_ntop(AF_INET, &ip_hdr->ip_dst, dst, sizeof(dst));
        print_malformed(header, src, dst, 0, 0, "IP", "frag_anomaly", packet + sizeof(struct ether_header), header->caplen - sizeof(struct ether_header));
        return true;
    }

    /* L4 examine */
    size_t l4_offset = sizeof(struct ether_header) + ihl_bytes;
    size_t l4_len = (header->caplen > l4_offset) ? (header->caplen - l4_offset) : 0;
    const u_char *l4ptr = packet + l4_offset;
    uint16_t src_port = 0, dst_port = 0;
    if (ip_hdr->ip_p == IPPROTO_TCP) {
        if (l4_len < sizeof(struct tcphdr)) {
            char src[INET_ADDRSTRLEN], dst[INET_ADDRSTRLEN];
            inet_ntop(AF_INET, &ip_hdr->ip_src, src, sizeof(src));
            inet_ntop(AF_INET, &ip_hdr->ip_dst, dst, sizeof(dst));
            print_malformed(header, src, dst, 0, 0, "TCP", "tcp_truncated", l4ptr, l4_len);
            return true;
        }
        const struct tcphdr *tcp = (const struct tcphdr *)l4ptr;
        src_port = ntohs(tcp->th_sport);
        dst_port = ntohs(tcp->th_dport);
        unsigned int th_off = (unsigned int)tcp->th_off * 4;
        if (th_off < 20 || l4_len < th_off) {
            char src[INET_ADDRSTRLEN], dst[INET_ADDRSTRLEN];
            inet_ntop(AF_INET, &ip_hdr->ip_src, src, sizeof(src));
            inet_ntop(AF_INET, &ip_hdr->ip_dst, dst, sizeof(dst));
            print_malformed(header, src, dst, src_port, dst_port, "TCP", "tcp_off_invalid", l4ptr, l4_len);
            return true;
        }
        /* flags sanity: SYN+FIN */
        uint8_t flags = *((uint8_t *)tcp + 13);
        if ((flags & 0x01) && (flags & 0x02)) {
            char src[INET_ADDRSTRLEN], dst[INET_ADDRSTRLEN];
            inet_ntop(AF_INET, &ip_hdr->ip_src, src, sizeof(src));
            inet_ntop(AF_INET, &ip_hdr->ip_dst, dst, sizeof(dst));
            print_malformed(header, src, dst, src_port, dst_port, "TCP", "syn_fin", l4ptr, l4_len);
            return true;
        }
        if (!tcp_checksum_ok(ip_hdr, l4ptr, l4_len)) {
            char src[INET_ADDRSTRLEN], dst[INET_ADDRSTRLEN];
            inet_ntop(AF_INET, &ip_hdr->ip_src, src, sizeof(src));
            inet_ntop(AF_INET, &ip_hdr->ip_dst, dst, sizeof(dst));
            print_malformed(header, src, dst, src_port, dst_port, "TCP", "tcp_cksum_bad", l4ptr, l4_len);
            return true;
        }
    } else if (ip_hdr->ip_p == IPPROTO_UDP) {
        if (l4_len < sizeof(struct udphdr)) {
            char src[INET_ADDRSTRLEN], dst[INET_ADDRSTRLEN];
            inet_ntop(AF_INET, &ip_hdr->ip_src, src, sizeof(src));
            inet_ntop(AF_INET, &ip_hdr->ip_dst, dst, sizeof(dst));
            print_malformed(header, src, dst, 0, 0, "UDP", "udp_truncated", l4ptr, l4_len);
            return true;
        }
        const struct udphdr *udp = (const struct udphdr *)l4ptr;
        src_port = ntohs(udp->uh_sport);
        dst_port = ntohs(udp->uh_dport);
        uint16_t udplen = ntohs(udp->uh_ulen);
        if (udplen < sizeof(struct udphdr) || l4_len < udplen) {
            char src[INET_ADDRSTRLEN], dst[INET_ADDRSTRLEN];
            inet_ntop(AF_INET, &ip_hdr->ip_src, src, sizeof(src));
            inet_ntop(AF_INET, &ip_hdr->ip_dst, dst, sizeof(dst));
            print_malformed(header, src, dst, src_port, dst_port, "UDP", "udp_len_invalid", l4ptr, l4_len);
            return true;
        }
    }

    return false; /* passed checks */
}

/* Report malformed statistics */
void malformed_report(void) {
    printf("\n📊 [MALFORMED STATISTICS]\n");
    printf("   Malformed packets detected: %d\n", malformed_drops);
}

