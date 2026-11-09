/* Count malloc/calloc/realloc calls. Used with PYTHONMALLOC=malloc so CPython
 * object allocations reach the system allocator instead of pymalloc.
 * Loaded via LD_PRELOAD by bench_filter_allocs.py.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stddef.h>
#include <stdint.h>

static uint64_t g_count;
static int resolving;
static void *(*real_malloc)(size_t);
static void *(*real_calloc)(size_t, size_t);
static void *(*real_realloc)(void *, size_t);

/* dlsym may call malloc before the real symbols are bound. */
static char bootstrap[256 * 1024];
static size_t bootstrap_used;

static void *bootstrap_alloc(size_t n) {
    size_t aligned = (n + 15u) & ~(size_t)15u;
    if (bootstrap_used + aligned > sizeof bootstrap)
        return NULL;
    void *p = bootstrap + bootstrap_used;
    bootstrap_used += aligned;
    return p;
}

static void resolve(void) {
    resolving = 1;
    real_malloc = (void *(*)(size_t))dlsym(RTLD_NEXT, "malloc");
    real_calloc = (void *(*)(size_t, size_t))dlsym(RTLD_NEXT, "calloc");
    real_realloc = (void *(*)(void *, size_t))dlsym(RTLD_NEXT, "realloc");
    resolving = 0;
}

void *malloc(size_t n) {
    if (!real_malloc) {
        if (resolving)
            return bootstrap_alloc(n);
        resolve();
    }
    __atomic_fetch_add(&g_count, 1, __ATOMIC_RELAXED);
    return real_malloc(n);
}

void *calloc(size_t m, size_t n) {
    if (!real_calloc) {
        if (resolving) {
            void *p = bootstrap_alloc(m * n);
            if (p) {
                unsigned char *b = p;
                for (size_t i = 0; i < m * n; i++)
                    b[i] = 0;
            }
            return p;
        }
        resolve();
    }
    __atomic_fetch_add(&g_count, 1, __ATOMIC_RELAXED);
    return real_calloc(m, n);
}

void *realloc(void *p, size_t n) {
    if (!real_realloc) {
        if (resolving)
            return bootstrap_alloc(n);
        resolve();
    }
    __atomic_fetch_add(&g_count, 1, __ATOMIC_RELAXED);
    return real_realloc(p, n);
}

uint64_t stig_alloc_count(void) {
    return __atomic_load_n(&g_count, __ATOMIC_RELAXED);
}

void stig_alloc_reset(void) {
    __atomic_store_n(&g_count, 0, __ATOMIC_RELAXED);
}
