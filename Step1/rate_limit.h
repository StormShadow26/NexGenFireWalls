#ifndef RATE_LIMIT_H
#define RATE_LIMIT_H

#include <pcap.h>
#include <stdbool.h>

/* Mode for which direction to enforce limits */
typedef enum {
    RL_MODE_INCOMING = 0,
    RL_MODE_OUTGOING = 1,
    RL_MODE_BOTH     = 2
} rl_mode_t;

void rate_limit_init(void);
bool rate_limit_check(const struct pcap_pkthdr *header, const u_char *packet);
void rate_limit_set_params(double tokens_per_sec, double burst_capacity);

/* New: set mode to INCOMING / OUTGOING / BOTH (default BOTH) */
void rate_limit_set_mode(rl_mode_t m);

/* report stats */
void rate_limit_report(void);

#endif /* RATE_LIMIT_H */

