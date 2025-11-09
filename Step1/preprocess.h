#ifndef PREPROCESS_H
#define PREPROCESS_H

#include <pcap.h>

/* exported globals */
extern int PACKET_LIMIT;     /* set by capture.c via -n */
extern int captured_count;  /* incremented by process_packet */

/* called by capture.c for each packet */
void process_packet(const struct pcap_pkthdr *h, const u_char *bytes);

/* called at program end (or to force flush/write CSV) */
void report_and_reset(void);

#endif /* PREPROCESS_H */

