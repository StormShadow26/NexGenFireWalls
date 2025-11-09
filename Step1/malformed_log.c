/* malformed_log.c
 *
 * Simple thread-safe appender for malformed packets.
 * Each line: timestamp (ISO), caplen, payload_hex (first N bytes)
 */

#define _POSIX_C_SOURCE 200809L
#define _DEFAULT_SOURCE
#include "malformed.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <time.h>
#include <sys/time.h>
#include <sys/types.h>
#include <unistd.h>
#include <errno.h>
#include <pcap.h>

static pthread_mutex_t malformed_lock = PTHREAD_MUTEX_INITIALIZER;

/* hex dump of up to N bytes into buf (buf must be at least 3*N+1) */
static void hexdump_prefix(const u_char *bytes, size_t n, char *buf, size_t bufsz) {
    size_t pos = 0;
    for (size_t i = 0; i < n && pos + 3 < bufsz; ++i) {
        int wrote = snprintf(buf + pos, bufsz - pos, "%02x ", bytes[i]);
        if (wrote < 0) break;
        pos += (size_t)wrote;
    }
    if (pos > 0 && pos < bufsz) buf[pos - 1] = '\0'; /* remove trailing space */
    else if (pos < bufsz) buf[pos] = '\0';
}

/* timestamp ISO */
static void format_ts_iso(const struct pcap_pkthdr *h, char *out, size_t outlen) {
    struct tm tm;
    time_t sec = h->ts.tv_sec;
    gmtime_r(&sec, &tm);
    snprintf(out, outlen, "%04d-%02d-%02dT%02d:%02d:%02d.%06uZ",
             tm.tm_year+1900, tm.tm_mon+1, tm.tm_mday,
             tm.tm_hour, tm.tm_min, tm.tm_sec,
             (unsigned)h->ts.tv_usec);
}

/* Append one line describing the malformed packet.
   Fields: timestamp, caplen, first_payload_hex */
void malformed_log_packet(const struct pcap_pkthdr *h, const u_char *bytes) {
    if (!h || !bytes) return;

    char ts[64];
    format_ts_iso(h, ts, sizeof(ts));

    /* keep small payload preview */
    const size_t PREVIEW = 32;
    char hexbuf[3 * (PREVIEW + 1)];
    size_t to_copy = h->caplen < PREVIEW ? h->caplen : PREVIEW;
    hexdump_prefix(bytes, to_copy, hexbuf, sizeof(hexbuf));

    /* open, append, flush, fsync */
    pthread_mutex_lock(&malformed_lock);

    FILE *f = fopen("malformed.csv.tmp", "a");
    if (!f) {
        /* try to create new file with header */
        f = fopen("malformed.csv.tmp", "w");
        if (!f) {
            fprintf(stderr, "[malformed_log] fopen failed: %s\n", strerror(errno));
            pthread_mutex_unlock(&malformed_lock);
            return;
        }
        fprintf(f, "timestamp,caplen,payload_preview\n");
    }

    if (f) {
        fprintf(f, "%s,%u,\"%s\"\n", ts, (unsigned)h->caplen, hexbuf);
        fflush(f);
        int fd = fileno(f);
        if (fd >= 0) fsync(fd);
        fclose(f);
    }
    /* rename to final file (idempotent) */
    rename("malformed.csv.tmp", "malformed.csv");

    pthread_mutex_unlock(&malformed_lock);
}

