#ifndef DENYLIST_H
#define DENYLIST_H

#include <pcap.h>
#include <stdbool.h>

/* Initialize denylist (hardcoded, or later load from CSV) */
void denylist_init(void);

/* Return true == ALLOW, false == DENY (i.e., drop) */
bool check_denylist(const struct pcap_pkthdr *header, const u_char *packet);

/* Report statistics */
void denylist_report(void);

#endif /* DENYLIST_H */

