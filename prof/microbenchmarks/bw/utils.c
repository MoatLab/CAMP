#define _GNU_SOURCE

#include "utils.h"

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <numa.h>

#define PAGE_SIZE 4096

static void touch_pages(char *ptr, uint64_t size)
{
    for (uint64_t i = 0; i < size; i += PAGE_SIZE)
        ptr[i] = 0;
}

int init_buf(uint64_t size, int node, char **ptr_out)
{
    void *ptr = numa_alloc_onnode((size_t)size, node);
    if (!ptr) {
        fprintf(stderr, "numa_alloc_onnode failed (size=%lu, node=%d)\n", size, node);
        return -1;
    }
    touch_pages((char *)ptr, size);
    *ptr_out = (char *)ptr;
    return 0;
}

int init_buf_reg_alloc(uint64_t size, char **ptr_out)
{
    void *ptr;
    int ret = posix_memalign(&ptr, ALIGN, (size_t)size);
    if (ret != 0) {
        fprintf(stderr, "posix_memalign failed: %s\n", strerror(ret));
        return -1;
    }
    touch_pages((char *)ptr, size);
    *ptr_out = (char *)ptr;
    return 0;
}

void buf_free_numa(char *ptr, uint64_t size)
{
    numa_free(ptr, (size_t)size);
}

void buf_free_aligned(char *ptr)
{
    free(ptr);
}

void print_usage(const char *prog)
{
    fprintf(stderr,
        "Usage: %s [-t threads] [-s size_MB] [-i iters] [-n numa_node] [-m r|w|c]\n"
        "  -t  number of threads            (default: %d)\n"
        "  -s  buffer size per thread in MB (default: %d)\n"
        "  -i  iterations                   (default: %d)\n"
        "  -n  NUMA node for allocation     (default: %d)\n"
        "  -m  access mode: r=read, w=write, c=copy (default: r)\n",
        prog,
        DEFAULT_THREADS,
        DEFAULT_BUF_SIZE_MB,
        DEFAULT_ITERATIONS,
        DEFAULT_NUMA_NODE);
}

int parse_args(int argc, char *argv[], header_t *tmpl)
{
    memset(tmpl, 0, sizeof(*tmpl));
    tmpl->num_thread = DEFAULT_THREADS;
    tmpl->buf_size   = (uint64_t)DEFAULT_BUF_SIZE_MB * (1ULL << 20);
    tmpl->op_iter    = DEFAULT_ITERATIONS;
    tmpl->numa_node  = DEFAULT_NUMA_NODE;
    tmpl->mode       = MODE_READ;

    int opt;
    while ((opt = getopt(argc, argv, "t:s:i:n:m:")) != -1) {
        switch (opt) {
        case 't':
            tmpl->num_thread = (uint64_t)atoi(optarg);
            if ((int)tmpl->num_thread <= 0) {
                fprintf(stderr, "Error: -t must be > 0\n");
                print_usage(argv[0]);
                exit(1);
            }
            break;
        case 's': {
            int mb = atoi(optarg);
            if (mb <= 0) {
                fprintf(stderr, "Error: -s must be > 0\n");
                print_usage(argv[0]);
                exit(1);
            }
            tmpl->buf_size = (uint64_t)mb * (1ULL << 20);
            break;
        }
        case 'i':
            tmpl->op_iter = atoi(optarg);
            if (tmpl->op_iter <= 0) {
                fprintf(stderr, "Error: -i must be > 0\n");
                print_usage(argv[0]);
                exit(1);
            }
            break;
        case 'n':
            tmpl->numa_node = atoi(optarg);
            break;
        case 'm':
            if (optarg[0] != 'r' && optarg[0] != 'w' && optarg[0] != 'c') {
                fprintf(stderr, "Error: -m must be r, w, or c\n");
                print_usage(argv[0]);
                exit(1);
            }
            tmpl->mode = (bw_mode_t)optarg[0];
            break;
        default:
            print_usage(argv[0]);
            exit(1);
        }
    }
    return 0;
}

double elapsed_seconds(struct timespec *start, struct timespec *end)
{
    return (double)(end->tv_sec  - start->tv_sec) +
           (double)(end->tv_nsec - start->tv_nsec) * 1e-9;
}
