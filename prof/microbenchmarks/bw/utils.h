#ifndef UTILS_H
#define UTILS_H

#define _GNU_SOURCE

#include <stdint.h>
#include <stdbool.h>
#include <time.h>

#define DEFAULT_BUF_SIZE_MB  1024
#define DEFAULT_THREADS      1
#define DEFAULT_ITERATIONS   5
#define DEFAULT_NUMA_NODE    0
#define ALIGN                64

typedef enum {
    MODE_READ  = 'r',
    MODE_WRITE = 'w',
    MODE_COPY  = 'c',
} bw_mode_t;

typedef struct {
    char        *buf_a;
    char        *buf_b;
    uint64_t     buf_size;
    int          thread_idx;
    uint64_t     num_thread;
    int          op_iter;
    int          numa_node;
    bw_mode_t    mode;
    double       elapsed_sec;
    double       gbps;
    volatile int halt;
} header_t;

int    init_buf(uint64_t size, int node, char **ptr_out);
int    init_buf_reg_alloc(uint64_t size, char **ptr_out);
void   buf_free_numa(char *ptr, uint64_t size);
void   buf_free_aligned(char *ptr);
void   print_usage(const char *prog);
int    parse_args(int argc, char *argv[], header_t *tmpl);
double elapsed_seconds(struct timespec *start, struct timespec *end);

#endif /* UTILS_H */
