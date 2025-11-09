/*
 * preprocess.c
 * Aggregates per-(src,dst,srcport,dstport,proto) stats for PACKET_LIMIT packets.
 * After the batch, report_and_reset writes summary CSV and resets accumulators.
 */

#include "preprocess.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <arpa/inet.h>
#include <netinet/ip.h>
#include <netinet/tcp.h>
#include <netinet/udp.h>
#include <net/ethernet.h>
#include <sys/socket.h>
#include <netdb.h>
#include <errno.h>
#include <inttypes.h>
#include <time.h>

/* Globals (single definitions) */
int PACKET_LIMIT = 50;
int captured_count = 0;

/* Enhanced interaction structure for DDoS/DoS detection */
typedef struct {
    char src_ip[INET_ADDRSTRLEN];
    char dst_ip[INET_ADDRSTRLEN];
    uint16_t src_port;
    uint16_t dst_port;
    uint8_t proto;

    uint64_t bytes_sent;
    uint64_t bytes_received;
    uint32_t pkts_sent;
    uint32_t pkts_received;

    /* TCP flags counters for DoS detection */
    uint32_t syn_count;
    uint32_t ack_count;
    uint32_t fin_count;
    uint32_t rst_count;
    uint32_t psh_count;
    
    /* Packet size statistics */
    uint32_t min_pkt_size;
    uint32_t max_pkt_size;
    uint64_t total_pkt_size;
    
    /* Timing statistics */
    struct timeval first_ts;
    struct timeval last_ts;
    
    /* Additional metrics */
    uint32_t unique_seq_numbers; /* Approximate uniqueness */
    uint32_t retransmissions;     /* Potential retransmission count */
} interaction_t;

#define MAX_INTERACTIONS 1024
static interaction_t interactions[MAX_INTERACTIONS];
static int interaction_count = 0;

static int interaction_match(const interaction_t *ia,
                             const char *src_ip, const char *dst_ip,
                             uint16_t src_port, uint16_t dst_port, uint8_t proto) {
    return (strcmp(ia->src_ip, src_ip) == 0) &&
           (strcmp(ia->dst_ip, dst_ip) == 0) &&
           (ia->src_port == src_port) &&
           (ia->dst_port == dst_port) &&
           (ia->proto == proto);
}

static interaction_t *get_or_create_interaction(const char *src_ip, const char *dst_ip,
                                                uint16_t src_port, uint16_t dst_port, uint8_t proto,
                                                const struct timeval *ts) {
    for (int i = 0; i < interaction_count; ++i) {
        if (interaction_match(&interactions[i], src_ip, dst_ip, src_port, dst_port, proto))
            return &interactions[i];
    }
    if (interaction_count >= MAX_INTERACTIONS) return NULL;
    interaction_t *ia = &interactions[interaction_count++];
    strncpy(ia->src_ip, src_ip, INET_ADDRSTRLEN);
    ia->src_ip[INET_ADDRSTRLEN - 1] = '\0';
    strncpy(ia->dst_ip, dst_ip, INET_ADDRSTRLEN);
    ia->dst_ip[INET_ADDRSTRLEN - 1] = '\0';
    ia->src_port = src_port;
    ia->dst_port = dst_port;
    ia->proto = proto;
    ia->bytes_sent = ia->bytes_received = 0;
    ia->pkts_sent = ia->pkts_received = 0;
    
    /* Initialize TCP flags counters */
    ia->syn_count = ia->ack_count = ia->fin_count = ia->rst_count = ia->psh_count = 0;
    
    /* Initialize packet size stats */
    ia->min_pkt_size = 0xFFFFFFFF;
    ia->max_pkt_size = 0;
    ia->total_pkt_size = 0;
    
    /* Initialize additional metrics */
    ia->unique_seq_numbers = 0;
    ia->retransmissions = 0;
    
    ia->first_ts = *ts;
    ia->last_ts = *ts;
    return ia;
}

static void update_interaction_with_packet(interaction_t *ia, int direction_src_to_dst, uint32_t pkt_wire_len,
                                           const struct timeval *ts, const struct tcphdr *tcp) {
    if (direction_src_to_dst) {
        ia->bytes_sent += pkt_wire_len;
        ia->pkts_sent += 1;
    } else {
        ia->bytes_received += pkt_wire_len;
        ia->pkts_received += 1;
    }
    
    /* Update packet size statistics */
    if (pkt_wire_len < ia->min_pkt_size) ia->min_pkt_size = pkt_wire_len;
    if (pkt_wire_len > ia->max_pkt_size) ia->max_pkt_size = pkt_wire_len;
    ia->total_pkt_size += pkt_wire_len;
    
    /* Extract TCP flags if available */
    if (tcp) {
        uint8_t flags = *((const uint8_t *)tcp + 13);
        if (flags & 0x02) ia->syn_count++;  /* SYN */
        if (flags & 0x10) ia->ack_count++;  /* ACK */
        if (flags & 0x01) ia->fin_count++;  /* FIN */
        if (flags & 0x04) ia->rst_count++;  /* RST */
        if (flags & 0x08) ia->psh_count++;  /* PSH */
    }
    
    if (timercmp(ts, &ia->first_ts, <)) ia->first_ts = *ts;
    if (timercmp(ts, &ia->last_ts, >)) ia->last_ts = *ts;
}

static double timeval_elapsed_seconds(const struct timeval *first, const struct timeval *last) {
    time_t sec = last->tv_sec - first->tv_sec;
    long usec = (long)last->tv_usec - (long)first->tv_usec;
    return (double)sec + ((double)usec / 1000000.0);
}

static const char *proto_str(uint8_t p) {
    switch (p) {
        case IPPROTO_TCP: return "TCP";
        case IPPROTO_UDP: return "UDP";
        case IPPROTO_ICMP: return "ICMP";
        default: return "OTHER";
    }
}

/* process_packet updates interactions */
void process_packet(const struct pcap_pkthdr *header, const u_char *packet) {
    captured_count++;

    if (header->caplen < sizeof(struct ether_header)) return;

    const struct ether_header *eth = (const struct ether_header *)packet;
    if (ntohs(eth->ether_type) != ETHERTYPE_IP) return;

    const struct ip *ip_hdr = (const struct ip *)(packet + sizeof(struct ether_header));
    size_t ip_hdr_bytes = (size_t)ip_hdr->ip_hl * 4;
    if (ip_hdr_bytes < 20) return;
    if (header->caplen < sizeof(struct ether_header) + ip_hdr_bytes) return;

    char src_ip[INET_ADDRSTRLEN], dst_ip[INET_ADDRSTRLEN];
    inet_ntop(AF_INET, &ip_hdr->ip_src, src_ip, sizeof(src_ip));
    inet_ntop(AF_INET, &ip_hdr->ip_dst, dst_ip, sizeof(dst_ip));

    uint8_t proto = ip_hdr->ip_p;
    const u_char *l4 = packet + sizeof(struct ether_header) + ip_hdr_bytes;
    size_t l4_len = header->caplen - (sizeof(struct ether_header) + ip_hdr_bytes);

    uint16_t src_port = 0, dst_port = 0;
    const struct tcphdr *tcp_hdr = NULL;
    
    if (proto == IPPROTO_TCP && l4_len >= sizeof(struct tcphdr)) {
        tcp_hdr = (const struct tcphdr *)l4;
        src_port = ntohs(tcp_hdr->th_sport);
        dst_port = ntohs(tcp_hdr->th_dport);
    } else if (proto == IPPROTO_UDP && l4_len >= sizeof(struct udphdr)) {
        const struct udphdr *udp = (const struct udphdr *)l4;
        src_port = ntohs(udp->uh_sport);
        dst_port = ntohs(udp->uh_dport);
    }

    /* find exact directional interaction */
    interaction_t *ia = NULL;
    for (int i = 0; i < interaction_count; ++i) {
        if (interaction_match(&interactions[i], src_ip, dst_ip, src_port, dst_port, proto)) {
            ia = &interactions[i];
            break;
        }
    }

    int direction_src_to_dst = 1;
    if (!ia) {
        /* try reverse */
        for (int i = 0; i < interaction_count; ++i) {
            if (interaction_match(&interactions[i], dst_ip, src_ip, dst_port, src_port, proto)) {
                ia = &interactions[i];
                direction_src_to_dst = 0;
                break;
            }
        }
    }

    if (!ia) {
        ia = get_or_create_interaction(src_ip, dst_ip, src_port, dst_port, proto, &header->ts);
        if (ia) update_interaction_with_packet(ia, 1, header->len, &header->ts, tcp_hdr);
    } else {
        update_interaction_with_packet(ia, direction_src_to_dst, header->len, &header->ts, tcp_hdr);
    }
}

/* report_and_reset: produce enhanced CSV with DoS/DDoS detection features */
void report_and_reset(void) {
    printf("\n--- Batch Summary (first %d packets) ---\n", PACKET_LIMIT);
    printf("Enhanced CSV with %d flows for ML/DDoS detection\n", interaction_count);

    const char *fname = "summary_batch_1.csv";
    FILE *f = fopen(fname, "w");
    if (f) {
        /* Enhanced CSV header with DoS/DDoS detection features */
        fprintf(f, "src_ip,dst_ip,src_port,dst_port,protocol,"
                   "bytes_sent,bytes_received,pkts_sent,pkts_received,"
                   "duration_sec,avg_pkt_size,pkt_rate,"
                   "syn_count,ack_count,fin_count,rst_count,psh_count,"
                   "syn_ack_ratio,syn_fin_ratio,"
                   "min_pkt_size,max_pkt_size,"
                   "total_packets,total_bytes\n");
    } else {
        fprintf(stderr, "Warning: couldn't open %s: %s\n", fname, strerror(errno));
    }

    for (int i = 0; i < interaction_count; ++i) {
        interaction_t *ia = &interactions[i];
        double elapsed = timeval_elapsed_seconds(&ia->first_ts, &ia->last_ts);
        if (elapsed < 0.000001) elapsed = 0.000001; /* Avoid division by zero */
        
        uint32_t total_pkts = ia->pkts_sent + ia->pkts_received;
        uint64_t total_bytes = ia->bytes_sent + ia->bytes_received;
        double avg_pkt_size = total_pkts > 0 ? (double)ia->total_pkt_size / total_pkts : 0.0;
        double pkt_rate = elapsed > 0 ? (double)total_pkts / elapsed : 0.0;
        
        /* Calculate ratios for anomaly detection */
        double syn_ack_ratio = ia->ack_count > 0 ? (double)ia->syn_count / ia->ack_count : (ia->syn_count > 0 ? 999.0 : 0.0);
        double syn_fin_ratio = ia->fin_count > 0 ? (double)ia->syn_count / ia->fin_count : (ia->syn_count > 0 ? 999.0 : 0.0);
        
        /* Fix min_pkt_size if no packets */
        uint32_t min_size = (ia->min_pkt_size == 0xFFFFFFFF) ? 0 : ia->min_pkt_size;
        
        /* Print summary to console (reduced) */
        printf("%s,%s,%u,%u,%s,pkts=%u,bytes=%" PRIu64 ",rate=%.1f\n",
               ia->src_ip, ia->dst_ip, ia->src_port, ia->dst_port,
               proto_str(ia->proto), total_pkts, total_bytes, pkt_rate);
        
        if (f) {
            /* Write full detailed data to CSV */
            fprintf(f, "%s,%s,%u,%u,%s,"
                       "%" PRIu64 ",%" PRIu64 ",%u,%u,"
                       "%.6f,%.2f,%.2f,"
                       "%u,%u,%u,%u,%u,"
                       "%.3f,%.3f,"
                       "%u,%u,"
                       "%u,%" PRIu64 "\n",
                    ia->src_ip, ia->dst_ip, ia->src_port, ia->dst_port,
                    proto_str(ia->proto),
                    ia->bytes_sent, ia->bytes_received, ia->pkts_sent, ia->pkts_received,
                    elapsed, avg_pkt_size, pkt_rate,
                    ia->syn_count, ia->ack_count, ia->fin_count, ia->rst_count, ia->psh_count,
                    syn_ack_ratio, syn_fin_ratio,
                    min_size, ia->max_pkt_size,
                    total_pkts, total_bytes);
        }
    }

    if (f) fclose(f);
    printf("Wrote CSV to %s\n", fname);

    /* Reset */
    interaction_count = 0;
}

