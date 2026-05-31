#define _GNU_SOURCE

#include "utils.h"

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <pthread.h>
#include <sched.h>
#include <unistd.h>
#include <errno.h>
#include <time.h>
#include <numa.h>

static pthread_barrier_t alloc_barrier;
static pthread_barrier_t barrier;

static int stick_this_thread_to_core(int core_id)
{
    int num_cores = sysconf(_SC_NPROCESSORS_ONLN);
    if (core_id < 0 || core_id >= num_cores) {
        fprintf(stderr, "ERROR: core_id %d out of range [0, %d)\n",
                core_id, num_cores);
        return EINVAL;
    }
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(core_id, &cpuset);
    return pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);
}

static uint64_t bw_read(const uint64_t *buf, uint64_t n)
{
    uint64_t sum = 0;
    for (uint64_t i = 0; i < n; i++)
        sum += buf[i];
    asm volatile("" : "+r"(sum));
    return sum;
}

static void bw_write(uint64_t *buf, uint64_t n)
{
    for (uint64_t i = 0; i < n; i++)
        buf[i] = 0xDEADBEEFCAFEBABEULL;
    asm volatile("" : : "r"(buf) : "memory");
}

static void bw_copy(uint64_t *dst, const uint64_t *src, uint64_t n)
{
    for (uint64_t i = 0; i < n; i++)
        dst[i] = src[i];
    asm volatile("" : : "r"(dst), "r"(src) : "memory");
}

void *bw_thread(void *arg)
{
    header_t *h = (header_t *)arg;
    int ret;

    ret = stick_this_thread_to_core(h->thread_idx);
    if (ret != 0)
        fprintf(stderr, "WARNING: could not pin thread %d to core\n", h->thread_idx);

    int use_numa = (numa_available() >= 0);

    if (use_numa) {
        if (init_buf(h->buf_size, h->numa_node, &h->buf_a) != 0)
            exit(1);
        if (h->mode == MODE_COPY) {
            if (init_buf(h->buf_size, h->numa_node, &h->buf_b) != 0)
                exit(1);
        }
    } else {
        if (init_buf_reg_alloc(h->buf_size, &h->buf_a) != 0)
            exit(1);
        if (h->mode == MODE_COPY) {
            if (init_buf_reg_alloc(h->buf_size, &h->buf_b) != 0)
                exit(1);
        }
    }

    pthread_barrier_wait(&alloc_barrier);
    pthread_barrier_wait(&barrier);

    uint64_t n_elems = h->buf_size / sizeof(uint64_t);
    struct timespec t0, t1;

    clock_gettime(CLOCK_MONOTONIC, &t0);
    for (int iter = 0; iter < h->op_iter; iter++) {
        if (h->mode == MODE_READ)
            bw_read((const uint64_t *)h->buf_a, n_elems);
        else if (h->mode == MODE_WRITE)
            bw_write((uint64_t *)h->buf_a, n_elems);
        else
            bw_copy((uint64_t *)h->buf_a, (const uint64_t *)h->buf_b, n_elems);
    }
    clock_gettime(CLOCK_MONOTONIC, &t1);

    h->elapsed_sec = elapsed_seconds(&t0, &t1);
    uint64_t bytes = (h->mode == MODE_COPY)
        ? 2ULL * h->buf_size * (uint64_t)h->op_iter
        :        h->buf_size * (uint64_t)h->op_iter;
    h->gbps = (double)bytes / h->elapsed_sec / 1e9;

    printf("Thread %2d: %.2f GB/s  (%.3f s)\n",
           h->thread_idx, h->gbps, h->elapsed_sec);

    if (use_numa) {
        buf_free_numa(h->buf_a, h->buf_size);
        if (h->mode == MODE_COPY)
            buf_free_numa(h->buf_b, h->buf_size);
    } else {
        buf_free_aligned(h->buf_a);
        if (h->mode == MODE_COPY)
            buf_free_aligned(h->buf_b);
    }

    return NULL;
}

int main(int argc, char *argv[])
{
    header_t tmpl;
    parse_args(argc, argv, &tmpl);

    int N = (int)tmpl.num_thread;
    header_t  *headers    = malloc((size_t)N * sizeof(header_t));
    pthread_t *thread_arr = malloc((size_t)N * sizeof(pthread_t));
    if (!headers || !thread_arr) {
        fprintf(stderr, "malloc failed\n");
        return 1;
    }

    pthread_barrier_init(&alloc_barrier, NULL, (unsigned)N);
    pthread_barrier_init(&barrier,       NULL, (unsigned)N);

    for (int i = 0; i < N; i++) {
        memcpy(&headers[i], &tmpl, sizeof(header_t));
        headers[i].thread_idx = i;
        headers[i].halt       = 0;
        headers[i].buf_a      = NULL;
        headers[i].buf_b      = NULL;
    }

    for (int i = 0; i < N; i++)
        pthread_create(&thread_arr[i], NULL, bw_thread, &headers[i]);

    for (int i = 0; i < N; i++)
        pthread_join(thread_arr[i], NULL);

    if (N > 1) {
        double total_gbps = 0.0;
        for (int i = 0; i < N; i++)
            total_gbps += headers[i].gbps;
        const char *mode_str = (tmpl.mode == MODE_READ)  ? "read"  :
                               (tmpl.mode == MODE_WRITE) ? "write" : "copy";
        printf("Aggregate [%s, %d threads, %lu MB/thread, %d iters]: %.2f GB/s\n",
               mode_str, N, tmpl.buf_size >> 20, tmpl.op_iter, total_gbps);
    }

    pthread_barrier_destroy(&alloc_barrier);
    pthread_barrier_destroy(&barrier);
    free(headers);
    free(thread_arr);
    return 0;
}
