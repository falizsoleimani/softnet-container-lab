/* SPDX-License-Identifier: GPL-2.0 */

/*
 * E3 — Packet Size Analyzer using eBPF/XDP
 *
 * Basic goal:
 * Track average packet size in real time.
 *
 * For each incoming packet:
 * - calculate packet size
 * - count total packets
 * - sum total bytes
 * - track minimum packet size
 * - track maximum packet size
 * - pass the packet normally
 */

#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>

#ifndef lock_xadd
#define lock_xadd(ptr, val) ((void)__sync_fetch_and_add(ptr, val))
#endif

struct packet_stats {
    __u64 packets;
    __u64 bytes;
    __u64 min_size;
    __u64 max_size;
};

/*
 * One global statistics record is enough for the Basic level.
 * Key = 0
 * Value = struct packet_stats
 */
struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __type(key, __u32);
    __type(value, struct packet_stats);
    __uint(max_entries, 1);
} e3_stats SEC(".maps");

SEC("xdp")
int xdp_packet_size_analyzer(struct xdp_md *ctx)
{
    void *data = (void *)(long)ctx->data;
    void *data_end = (void *)(long)ctx->data_end;

    __u64 packet_size = (__u64)((char *)data_end - (char *)data);
    __u32 key = 0;

    struct packet_stats *stats;

    stats = bpf_map_lookup_elem(&e3_stats, &key);
    if (!stats)
        return XDP_ABORTED;

    lock_xadd(&stats->packets, 1);
    lock_xadd(&stats->bytes, packet_size);

    if (stats->min_size == 0 || packet_size < stats->min_size)
        stats->min_size = packet_size;

    if (packet_size > stats->max_size)
        stats->max_size = packet_size;

    return XDP_PASS;
}

char _license[] SEC("license") = "Dual BSD/GPL";
