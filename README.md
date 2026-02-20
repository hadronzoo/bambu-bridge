# Bambu Lab VLAN Discovery Bridge

**Makes your Bambu 3D printer appear automatically in Bambu Studio / OrcaSlicer — even when the printer and your PC are on different VLANs/subnets.**

Works in **LAN Mode** (cloud disabled)  
Zero configuration in the slicer — printer just shows up  
Forwards AMS humidity, nozzle temp, filament info, bed level, everything  
Tested on X1C, P1S, P1P, A1, A1 Mini (firmware 01.06 → 01.08+)

Bambu Lab uses a non-standard SSDP/broadcast discovery mechanism (ports 2021 + 1900) that **does not cross VLANs or subnets**. This tiny Python script listens on the printer's VLAN and safely re-broadcasts only the real Bambu discovery packets into the client's VLAN.

Result: your printer magically appears in the device list again — no manual IP entry not required.

## Why you need this

| Situation                                  | Without bridge               | With bridge                     |
|--------------------------------------------|------------------------------|---------------------------------|
| Printer on IoT VLAN, PC on trusted LAN     | Not discovered               | Auto-discovered                 |
| Printer in lab VLAN, workstation elsewhere | Not discovered               | Auto-discovered                 |
| LAN Mode enabled (cloud disabled)          | Discovery completely broken  | Works perfectly                 |
| Multiple printers on different VLANs       | Pain                         | All appear instantly            |

## How it works

- Runs a raw packet socket on the **printer-side** interface (`lan1.50` in the example)
- Filters aggressively (VLAN duplicate removal → IPv4 → UDP → ports 2021/1900 → Bambu magic string)
- Re-broadcasts **only** legitimate Bambu discovery packets into the **client-side** interface (`lan1.10` in the example)
- < 0.1 % CPU on a Raspberry Pi, zero configuration needed on the printer or slicer

## Installation

### 1. Prerequisites

- Linux system that can see both VLANs (common setups below)
- Python 3.8+
- Root (or `CAP_NET_RAW` capability)

### 2. Quick install (any Linux with both VLANs)

```bash
sudo mkdir -p /opt/bambu-bridge
sudo cp bambu-bridge.py /opt/bambu-bridge/
sudo chmod +x /opt/bambu-bridge/bambu-bridge.py

# Edit the two interface names near the top of the script
sudo nano /opt/bambu-bridge/bambu-bridge.py
```

Set your interface names via environment variables, or edit the defaults near the top of the script:
```bash
export SOURCE_IFACE="lan1.50"   # interface where the printer lives
export TARGET_IFACE="lan1.10"   # interface where your PC/phone lives
```

### 3. Run forever

#### Option A – systemd (Ubuntu, Debian, Fedora, Arch, TrueNAS Scale, Proxmox, etc.)
```bash
sudo cp bambu-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bambu-bridge.service
sudo systemctl status bambu-bridge.service
```

#### Option B – OpenWrt / OPNsense / router without systemd
```bash
nohup /usr/bin/python3 /opt/bambu-bridge/bambu-bridge.py --quiet &
# or add to /etc/rc.local, startup script, etc.
```

#### Option C – Docker

The image is published to GitHub Container Registry for `linux/amd64` and `linux/arm64`.

```bash
docker run -d \
  --name bambu-bridge \
  --restart unless-stopped \
  --network host \
  --cap-add NET_RAW \
  --cap-add NET_ADMIN \
  -e SOURCE_IFACE=lan1.50 \
  -e TARGET_IFACE=lan1.10 \
  ghcr.io/hadronzoo/bambu-bridge:latest
```

**Required flags:**

| Flag | Why |
|------|-----|
| `--network host` | The container must see the host's VLAN interfaces directly. Bridge/overlay networking will not work. |
| `--cap-add NET_RAW` | Required to open a raw packet socket for capturing broadcast traffic. |
| `--cap-add NET_ADMIN` | Required to bind sockets to specific network interfaces. |

**Environment variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `SOURCE_IFACE` | `lan1.50` | Network interface on the **printer** VLAN. |
| `TARGET_IFACE` | `lan1.10` | Network interface on the **client** VLAN (where Bambu Studio runs). |
| `LOG_LEVEL` | `INFO` | Standard Python log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |

**View logs:**

```bash
docker logs -f bambu-bridge
```

**Docker Compose example:**

```yaml
services:
  bambu-bridge:
    image: ghcr.io/hadronzoo/bambu-bridge:latest
    restart: unless-stopped
    network_mode: host
    cap_add:
      - NET_RAW
      - NET_ADMIN
    environment:
      - SOURCE_IFACE=lan1.50
      - TARGET_IFACE=lan1.10
```

### Common setups & interface names

| Platform             | Printer VLAN interface name examples       | Client VLAN interface name examples   |
|----------------------|--------------------------------------------|---------------------------------------|
| OpenWrt              | `lan1.50`, `br-lan.50`, `eth1.50`          | `lan1.10`, `br-lan.10`                |
| OPNsense / pfSense   | `igb1.50`, `vlan50`                        | `igb2.10`, `vlan10`                   |
| Ubiquiti UniFi       | `br50`, `vlan50`                           | `br10`, `vlan10`                      |
| Proxmox              | `vmbr50`, `vmbr0.50`                       | `vmbr10`                              |
| TrueNAS Scale        | `br50`, `vlan50`                           | `br10`                                |
| Generic Linux bridge | `br-iot`, `vlan50`                         | `br-lan`, `br-main`                   |

You can find the correct names with:
```bash
ip link show | grep vlan
ip addr show
```

### Optional: Run without full root (recommended for hardening)

Uncomment the capability lines in the `.service` file:
```ini
CapabilityBoundingSet=CAP_NET_RAW CAP_NET_ADMIN
AmbientCapabilities=CAP_NET_RAW CAP_NET_ADMIN
```
Then run the service as a normal user (e.g., `bambu`).

### Testing

```bash
sudo journalctl -u bambu-bridge -f
```

You should see lines like:
```
12:00:01 INFO: Bambu bridge started: lan1.50 -> lan1.10 BROADCAST
12:00:05 INFO: Bambu printer (re)discovered: 192.168.50.42
```

Open Bambu Studio / OrcaSlicer → your printer appears within 10 seconds.

## FAQ

**Q: Do I still need this if I use mDNS reflection?**  
A: Yes. Bambu printers do **not** use mDNS — only SSDP/broadcast. mDNS reflectors do nothing for them.

**Q: Will this break if I have multiple printers?**  
A: No — it forwards every printer on the source VLAN automatically.

**Q: Is it safe?**  
A: Yes — it only forwards packets containing the exact Bambu magic string. Nothing else leaks.

**Q: Can I reverse the direction (client → printer for M-SEARCH)?**  
A: Not needed — the printer announcements are sufficient for discovery in 99 % of cases.

## License
MIT
