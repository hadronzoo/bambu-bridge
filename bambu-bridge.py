#!/usr/bin/env python3
"""
Bambu Lab VLAN Discovery Bridge
===============================

Forwards real Bambu printer discovery broadcasts from one
VLAN to another, enabling full LAN-mode detection and
AMS/filament/nozzle/humidity sync across isolated networks.

Copyright (c) John Clark 2025
License: MIT
"""

import argparse
import logging
import os
import signal
import socket
import struct
import sys
from typing import Set

# config
SOURCE_IFACE = os.environ.get("SOURCE_IFACE", "lan1.50")   # Printer-side VLAN interface
TARGET_IFACE = os.environ.get("TARGET_IFACE", "lan1.10")   # Client-side VLAN interface

BAMBU_PORTS: Set[int] = {2021, 1900}
BROADCAST_ADDR = "255.255.255.255"
BAMBU_MAGIC = b"urn:bambulab-com:device:3dprinter"

# logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger("bambu-bridge")

# add status level
logging.STATUS = 25
logging.addLevelName(logging.STATUS, "STATUS")
logging.Logger.status = lambda self, msg, *a, **kw: self.log(logging.STATUS, msg, *a, **kw)

capture_socket: socket.socket | None = None

def hexdump(data: bytes) -> str:
    """Return traditional hex + ASCII dump."""
    lines = []
    for offset in range(0, len(data), 16):
        chunk = data[offset:offset + 16]
        hex_part = " ".join(f"{b:02x}" for b in chunk).ljust(47)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{offset:04x}  {hex_part}  {ascii_part}")
    return "\n".join(lines)

def signal_handler(signum, frame) -> None:
    logger.status("Shutting down gracefully...")
    if capture_socket:
        capture_socket.close()
    sys.exit(0)

def main() -> None:
    global capture_socket

    parser = argparse.ArgumentParser(
        description="Bambu Lab VLAN Discovery Bridge — forwards printer broadcasts"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-q", "--quiet",   action="store_true", help="Suppress all output except critical errors and status messages")
    group.add_argument("-v", "--verbose", action="store_true", help="Show detailed packet information including full hex dump")
    args = parser.parse_args()

    # set logging level (CLI flags take precedence over LOG_LEVEL env var)
    log_level_env = os.environ.get("LOG_LEVEL", "").lower()
    if args.quiet:
        logger.setLevel(logging.STATUS)  # status level is always visible
    elif args.verbose:
        logger.setLevel(logging.DEBUG)
    elif log_level_env == "quiet":
        logger.setLevel(logging.STATUS)
    elif log_level_env == "verbose":
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    signal.signal(signal.SIGINT,  signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        capture_socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
        capture_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, SOURCE_IFACE.encode())
    except PermissionError:
        logger.critical("Must run as root (raw socket requires CAP_NET_RAW)")
        sys.exit(1)
    except OSError as e:
        logger.critical("Cannot bind to interface '%s': %s", SOURCE_IFACE, e)
        sys.exit(1)

    logger.status("Bambu bridge started: %s -> %s BROADCAST", SOURCE_IFACE, TARGET_IFACE)
    logger.status("Press Ctrl+C to stop")

    count = 0
    last_printer_ip = None

    while True:
        try:
            pkt, addr = capture_socket.recvfrom(65536)
        except OSError:
            break

        # only accept packets that arrive on the VLAN interface we actually bound to
        if addr[0] != SOURCE_IFACE:
            continue

        # ipv4 filter
        if len(pkt) < 42 or struct.unpack("!H", pkt[12:14])[0] != 0x0800:
            continue

        # udp filter
        if pkt[23] != 17:
            continue

        # port filter
        iph = struct.unpack("!BBHHHBBH4s4s", pkt[14:34])
        ihl = (iph[0] & 0xF) * 4
        udp_off = 14 + ihl
        if len(pkt) < udp_off + 8:
            continue

        src_port, dst_port = struct.unpack("!HH", pkt[udp_off:udp_off+4])
        if dst_port not in BAMBU_PORTS:
            continue

        # filter for bambu payload
        payload = pkt[udp_off + 8:]
        if BAMBU_MAGIC not in payload:
            continue

        # status: printer (re)discovered
        src_ip = socket.inet_ntoa(iph[8])
        if src_ip != last_printer_ip:
            logger.status("Bambu printer (re)discovered: %s", src_ip)
            last_printer_ip = src_ip

        count += 1
        logger.info("[%5d] %s:%d -> %s:%d (%d bytes)", count, src_ip, src_port, BROADCAST_ADDR, dst_port, len(payload))

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("\n%s", hexdump(payload))

        # forward
        try:
            sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sender.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sender.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, TARGET_IFACE.encode())
            sender.sendto(payload, (BROADCAST_ADDR, dst_port))
            sender.close()
        except Exception as e:
            logger.error("Failed to forward packet from %s:%d: %s", src_ip, src_port, e)
            continue


if __name__ == "__main__":
    main()

