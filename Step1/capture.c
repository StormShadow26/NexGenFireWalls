/* capture.c  -- capture on all IP-capable interfaces, accept only packets destined to this host
 *
 * Two Parallel Pipelines:
 *   Pipeline 1 (Independent): preprocess (runs for ALL packets)
 *   Pipeline 2 (Sequential):  denylist -> rate_limit -> malformed
 *
 * Compile:
 *   gcc -Wall -Wextra -std=gnu11 capture.c preprocess.c denylist.c rate_limit.c malformed.c -o capture -lpcap -lpthread
 */

#define _DEFAULT_SOURCE

#include <pcap.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <pthread.h>
#include <ifaddrs.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <stdbool.h>

#include "preprocess.h"
#include "denylist.h"
#include "rate_limit.h"
#include "malformed.h"

/* forward declaration for the logging helper implemented separately */
void malformed_log_packet(const struct pcap_pkthdr *h, const u_char *bytes);

typedef struct {
    pcap_t *handle;
    char *devname;
} dev_thread_arg_t;

static pcap_t **global_handles = NULL;
static char  **global_names   = NULL;
static size_t global_handle_count = 0;
static pthread_t *threads = NULL;
static volatile sig_atomic_t stop_requested = 0;

/* datalink types where IPv4 dst-host BPF makes sense */
static bool datalink_supports_ip(int dlt) {
    switch (dlt) {
        case DLT_EN10MB:
        case DLT_RAW:
        case DLT_NULL:
        case DLT_LOOP:
        case DLT_LINUX_SLL:
            return true;
        default:
            return false;
    }
}

/* Skip problematic interfaces that generate malformed packets */
static bool should_skip_interface(const char *name) {
    if (!name) return true;
    
    /* Skip bluetooth interfaces */
    if (strstr(name, "bluetooth")) return true;
    
    /* Skip dbus interfaces */
    if (strstr(name, "dbus")) return true;
    
    /* Skip nflog and nfqueue */
    if (strstr(name, "nflog")) return true;
    if (strstr(name, "nfqueue")) return true;
    
    /* Skip any interface */
    if (strstr(name, "any")) return true;
    
    return false;
}

/* safe signal handler: mark stop and break loops for responsiveness */
static void int_handler(int signo) {
    (void)signo;
    stop_requested = 1;
    for (size_t i = 0; i < global_handle_count; ++i) {
        if (global_handles && global_handles[i]) pcap_breakloop(global_handles[i]);
    }
}

/* collect unique local IPv4 addresses */
static char **collect_local_ipv4(size_t *out_count) {
    struct ifaddrs *ifap = NULL;
    if (getifaddrs(&ifap) != 0) {
        *out_count = 0;
        return NULL;
    }
    char **addrs = NULL;
    size_t n = 0;
    for (struct ifaddrs *ifa = ifap; ifa; ifa = ifa->ifa_next) {
        if (!ifa->ifa_addr) continue;
        if (ifa->ifa_addr->sa_family == AF_INET) {
            struct sockaddr_in *sa = (struct sockaddr_in *)ifa->ifa_addr;
            char buf[INET_ADDRSTRLEN];
            if (inet_ntop(AF_INET, &sa->sin_addr, buf, sizeof(buf))) {
                bool dup = false;
                for (size_t i = 0; i < n; ++i) if (strcmp(addrs[i], buf) == 0) { dup = true; break; }
                if (!dup) {
                    char *s = strdup(buf);
                    if (!s) continue;
                    char **tmp = realloc(addrs, (n + 1) * sizeof(char *));
                    if (!tmp) { free(s); continue; }
                    addrs = tmp;
                    addrs[n++] = s;
                }
            }
        }
    }
    freeifaddrs(ifap);
    *out_count = n;
    return addrs;
}

/* Build "dst host A or dst host B ..." */
static char *build_dst_filter(char **addrs, size_t n) {
    if (n == 0) return NULL;
    size_t len = 0;
    for (size_t i = 0; i < n; ++i) len += strlen(addrs[i]) + 12;
    char *f = malloc(len + 1);
    if (!f) return NULL;
    f[0] = '\0';
    for (size_t i = 0; i < n; ++i) {
        if (i) strcat(f, " or ");
        strcat(f, "dst host ");
        strcat(f, addrs[i]);
    }
    return f;
}

/* callback: Two parallel pipelines
 *
 * Pipeline 1 (INDEPENDENT - Always runs):
 *   - process_packet() - Collects stats for ALL packets
 *
 * Pipeline 2 (SEQUENTIAL - Filtering chain):
 *   - check_denylist() - If fails, drop and return
 *   - rate_limit_check() - If fails, drop and return
 *   - is_malformed() - If fails, drop and return
 *   - If passes all filters, packet is accepted
 */
static void pcap_callback(u_char *user, const struct pcap_pkthdr *h, const u_char *bytes) {
    (void)user;
    if (!h || !bytes) return;

    /* PIPELINE 1: Preprocess (ALWAYS RUNS - Independent of filtering) */
    process_packet(h, bytes);

    /* Check if we reached packet limit (based on total packets processed) */
    if (captured_count >= PACKET_LIMIT) {
        stop_requested = 1;
        for (size_t i = 0; i < global_handle_count; ++i) {
            if (global_handles && global_handles[i]) pcap_breakloop(global_handles[i]);
        }
        return;
    }

    /* PIPELINE 2: Filtering Chain (denylist → rate_limit → malformed) */
    
    /* Filter 1: Denylist check */
    if (!check_denylist(h, bytes)) {
        /* Dropped by denylist - console message already printed */
        return;
    }

    /* Filter 2: Rate limit check */
    if (!rate_limit_check(h, bytes)) {
        /* Dropped by rate limiter - console message already printed */
        return;
    }

    /* Filter 3: Malformed check */
    if (is_malformed(h, bytes)) {
        /* Dropped by malformed check - console message already printed */
        return;
    }

    /* Packet ACCEPTED - passed all filters */
}

/* per-handle thread */
static void *device_thread(void *arg) {
    dev_thread_arg_t *darg = (dev_thread_arg_t *)arg;
    pcap_t *handle = darg->handle;
    const char *name = darg->devname ? darg->devname : "unknown";
    int rc = pcap_loop(handle, 0, pcap_callback, NULL);
    if (rc == -1) {
        fprintf(stderr, "[%s] pcap_loop error: %s\n", name, pcap_geterr(handle));
    }
    free(darg->devname);
    free(darg);
    return NULL;
}

int main(int argc, char **argv) {
    char errbuf[PCAP_ERRBUF_SIZE];
    int opt;
    char *single_dev = NULL;
    double dummy_r = -1.0, dummy_b = -1.0; 
    (void)dummy_r;
    (void)dummy_b;/* left in case you want rate-limit flags later */

    while ((opt = getopt(argc, argv, "i:n:r:b:h")) != -1) {
        switch (opt) {
            case 'i': single_dev = optarg; break;
            case 'n': PACKET_LIMIT = atoi(optarg); if (PACKET_LIMIT <= 0) PACKET_LIMIT = 1; break;
            case 'r': dummy_r = atof(optarg); break;
            case 'b': dummy_b = atof(optarg); break;
            case 'h':
            default:
                fprintf(stderr, "Usage: %s [-i interface] [-n packet_limit]\n", argv[0]);
                return 1;
        }
    }

    /* init modules */
    denylist_init();
    rate_limit_init();
    malformed_init();

    /* collect local IPv4 addresses */
    size_t addr_count = 0;
    char **local_addrs = collect_local_ipv4(&addr_count);
    char *filter_expr = build_dst_filter(local_addrs, addr_count);
    if (filter_expr) printf("Applying BPF filter: %s\n", filter_expr);
    else printf("No local IPv4 found — capturing all packets on IP-capable interfaces.\n");

    /* get device list */
    pcap_if_t *alldevs = NULL;
    if (pcap_findalldevs(&alldevs, errbuf) == -1) {
        fprintf(stderr, "pcap_findalldevs failed: %s\n", errbuf);
        goto cleanup_addrs;
    }
    if (!alldevs) {
        fprintf(stderr, "No devices found\n");
        goto cleanup_addrs;
    }

    /* count candidates */
    size_t possible = 0;
    for (pcap_if_t *d = alldevs; d; d = d->next) {
        if (single_dev && strcmp(single_dev, d->name) != 0) continue;
        if (!single_dev && should_skip_interface(d->name)) continue;
        ++possible;
    }
    if (possible == 0) {
        fprintf(stderr, "No matching devices\n");
        goto cleanup_devs;
    }

    global_handles = calloc(possible, sizeof(pcap_t *));
    global_names   = calloc(possible, sizeof(char *));
    threads        = calloc(possible, sizeof(pthread_t));
    if (!global_handles || !global_names || !threads) {
        fprintf(stderr, "Out of memory\n");
        goto cleanup_devs;
    }

    /* open handles and set per-handle filter where applicable */
    size_t idx = 0;
    for (pcap_if_t *d = alldevs; d; d = d->next) {
        if (single_dev && strcmp(single_dev, d->name) != 0) continue;
        if (!single_dev && should_skip_interface(d->name)) {
            fprintf(stderr, "Skipping interface: %s (known problematic)\n", d->name);
            continue;
        }

        pcap_t *handle = pcap_open_live(d->name, 65536, 1, 1000, errbuf);
        if (!handle) {
            fprintf(stderr, "pcap_open_live(%s) failed: %s\n", d->name, errbuf);
            continue;
        }

        int dlt = pcap_datalink(handle);
        if (!datalink_supports_ip(dlt)) {
            /* skip non-IP datalinks (avoids pcap_compile failures) */
            fprintf(stderr, "Skipping %s: unsupported datalink=%d\n", d->name, dlt);
            pcap_close(handle);
            continue;
        }
        
        if (filter_expr) {
            struct bpf_program fp;
            bpf_u_int32 net = 0, mask = 0;
            if (pcap_lookupnet(d->name, &net, &mask, errbuf) == -1) {
                mask = 0xFFFFFFFF;
            }
            if (pcap_compile(handle, &fp, filter_expr, 1, mask) == 0) {
                if (pcap_setfilter(handle, &fp) != 0) {
                    fprintf(stderr, "pcap_setfilter failed on %s: %s\n", d->name, pcap_geterr(handle));
                }
                pcap_freecode(&fp);
            } else {
                fprintf(stderr, "pcap_compile failed on %s: %s -- continuing without filter\n", d->name, pcap_geterr(handle));
            }
        }

        global_handles[idx] = handle;
        global_names[idx] = strdup(d->name ? d->name : "unknown");
        if (!global_names[idx]) global_names[idx] = strdup("unknown");
        ++idx;
    }
    global_handle_count = idx;

    if (global_handle_count == 0) {
        fprintf(stderr, "No suitable handles opened\n");
        goto cleanup_handles;
    }

    /* install signals */
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = int_handler;
    sigaction(SIGINT, &sa, NULL);
    sigaction(SIGTERM, &sa, NULL);

    printf("Starting capture on %zu interface(s). Packet limit=%d\n", global_handle_count, PACKET_LIMIT);

    /* launch threads */
    size_t started = 0;
    for (size_t i = 0; i < global_handle_count; ++i) {
        dev_thread_arg_t *darg = calloc(1, sizeof(dev_thread_arg_t));
        if (!darg) continue;
        darg->handle = global_handles[i];
        darg->devname = strdup(global_names[i]);
        if (!darg->devname) darg->devname = strdup("unknown");
        if (pthread_create(&threads[started], NULL, device_thread, darg) != 0) {
            fprintf(stderr, "Failed to create thread for %s\n", darg->devname);
            free(darg->devname);
            free(darg);
            continue;
        }
        ++started;
    }

    for (size_t i = 0; i < started; ++i) pthread_join(threads[i], NULL);

    printf("\n═══════════════════════════════════════════════════════════════\n");
    printf("Finished capture. Processed packets: %d\n", captured_count);
    printf("═══════════════════════════════════════════════════════════════\n");
    
    /* Print all filter statistics */
    denylist_report();
    rate_limit_report();
    malformed_report();
    
    /* Print preprocessing summary and CSV */
    report_and_reset();

cleanup_handles:
    for (size_t i = 0; i < global_handle_count; ++i) {
        if (global_handles[i]) pcap_close(global_handles[i]);
    }
    for (size_t i = 0; i < global_handle_count; ++i) free(global_names[i]);
    free(global_handles);
    free(global_names);
    free(threads);

cleanup_devs:
    if (alldevs) pcap_freealldevs(alldevs);

cleanup_addrs:
    if (local_addrs) {
        for (size_t i = 0; i < addr_count; ++i) free(local_addrs[i]);
        free(local_addrs);
    }
    if (filter_expr) free(filter_expr);

    return 0;
}

