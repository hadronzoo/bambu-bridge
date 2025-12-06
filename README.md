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

Change these two lines near the top of the script to match your actual interface names:
```python
SOURCE_IFACE = "lan1.50"   # interface where the printer lives
TARGET_IFACE = "lan1.10"   # interface where your PC/phone lives
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

#### Option C – Docker (if you prefer containers)
See `docker-run.sh` in this repo.

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
Bambu bridge started: lan1.50 → lan1.10 BROADCAST
Bambu printer (re)discovered: 192.168.50.42
[    1] 192.168.50.42:2021 → 255.255.255.255:2021 (429 bytes)
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
