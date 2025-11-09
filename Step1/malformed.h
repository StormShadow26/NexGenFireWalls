#ifndef MALFORMED_H
#define MALFORMED_H

#include <pcap.h>
#include <stdbool.h>

/* existing API */
void malformed_init(void);
bool is_malformed(const struct pcap_pkthdr *h, const u_char *bytes);

/* report statistics */
void malformed_report(void);

/* new: log a malformed packet (thread-safe append to malformed.csv).
   Implementation provided in malformed_log.c below. */
void malformed_log_packet(const struct pcap_pkthdr *h, const u_char *bytes);

#endif /* MALFORMED_H */

