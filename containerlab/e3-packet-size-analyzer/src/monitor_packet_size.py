#!/usr/bin/env python3

import json
import os
import struct
import subprocess
import time

MAP_NAME = "e3_stats"


def bpftool_cmd():
    if os.geteuid() == 0:
        return ["bpftool"]
    return ["sudo", "bpftool"]


def run(cmd):
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout


def find_map_id():
    maps = json.loads(run(bpftool_cmd() + ["-j", "map", "show"]))

    for item in maps:
        if item.get("name") == MAP_NAME:
            return item.get("id")

    raise RuntimeError("Cannot find BPF map 'e3_stats'. Attach the XDP program first.")


def parse_value(value):
    if isinstance(value, dict):
        return {
            "packets": int(value.get("packets", 0)),
            "bytes": int(value.get("bytes", 0)),
            "min_size": int(value.get("min_size", 0)),
            "max_size": int(value.get("max_size", 0)),
        }

    if isinstance(value, list):
        raw = bytearray()

        for item in value:
            if isinstance(item, str):
                raw.append(int(item, 16))
            else:
                raw.append(int(item))

        while len(raw) < 32:
            raw.append(0)

        packets, total_bytes, min_size, max_size = struct.unpack("<QQQQ", raw[:32])

        return {
            "packets": packets,
            "bytes": total_bytes,
            "min_size": min_size,
            "max_size": max_size,
        }

    raise RuntimeError("Unsupported bpftool map value format")


def read_stats(map_id):
    dumped = json.loads(run(bpftool_cmd() + ["-j", "map", "dump", "id", str(map_id)]))

    if not dumped:
        return {
            "packets": 0,
            "bytes": 0,
            "min_size": 0,
            "max_size": 0,
        }

    return parse_value(dumped[0]["value"])


def clear_screen():
    os.system("clear")


def main():
    map_id = find_map_id()

    while True:
        stats = read_stats(map_id)

        packets = stats["packets"]
        total_bytes = stats["bytes"]
        min_size = stats["min_size"]
        max_size = stats["max_size"]

        average = 0
        if packets > 0:
            average = total_bytes / packets

        clear_screen()

        print("E3 — Packet Size Analyzer using eBPF/XDP")
        print("----------------------------------------")
        print(f"BPF map name:         {MAP_NAME}")
        print(f"BPF map id:           {map_id}")
        print()
        print(f"Total packets:        {packets}")
        print(f"Total bytes:          {total_bytes}")
        print(f"Average packet size:  {average:.2f} bytes")
        print(f"Minimum packet size:  {min_size} bytes")
        print(f"Maximum packet size:  {max_size} bytes")
        print()
        print("Press Ctrl+C to stop.")

        time.sleep(1)


if __name__ == "__main__":
    main()
