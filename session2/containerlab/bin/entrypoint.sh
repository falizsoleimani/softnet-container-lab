#!/bin/bash
set -euo pipefail

HOSTNAME=$(hostname)
CFG_FILE="/etc/nodes/${HOSTNAME}.cfg"

echo "=== Auto-Configuring: ${HOSTNAME} ==="

if [[ -f "${CFG_FILE}" ]]; then
    source "${CFG_FILE}"
fi

ip link set lo up

# Force flush all existing IPs on eth1 and eth2 to prevent "File exists" error
ip addr flush dev eth1 || true
ip link set eth1 up
if [ -d /sys/class/net/eth2 ]; then
    ip addr flush dev eth2 || true
    ip link set eth2 up
fi

if [[ "${HOSTNAME}" == "router" ]]; then
    sysctl -w net.ipv4.ip_forward=1
    sysctl -w net.ipv4.conf.all.forwarding=1
    sysctl -w net.ipv6.conf.all.forwarding=1
    
    # Static IPs for Router (Gateways)
    ip addr add 192.168.1.1/24 dev eth1
    ip addr add 192.168.2.1/24 dev eth2
    ip -6 addr add fd00:1::1/64 dev eth1 nodad
    ip -6 addr add fd00:2::1/64 dev eth2 nodad
fi

if [[ -n "${NODE_IP:-}" ]]; then
    ip addr add "${NODE_IP}/${NODE_PREFIX}" dev eth1
    ip -6 addr add "${NODE_IP6}/${NODE_PREFIX6}" dev eth1 nodad
fi

if [[ -n "${PEER_IP:-}" ]]; then
    # Delete any existing default routes before adding the new one
    ip route del default || true
    ip route add default via "${PEER_IP}"
    ip -6 route del default || true
    ip -6 route add default via "${PEER_IP6}"
fi

echo "[OK] Configuration applied for ${HOSTNAME}."
