FROM python:3.13-slim

WORKDIR /app

COPY bambu-bridge.py .

# Printer-side VLAN interface (where printers live)
ENV SOURCE_IFACE=lan1.50
# Client-side VLAN interface (where PCs/phones live)
ENV TARGET_IFACE=lan1.10
# Log verbosity: set to "quiet" or "verbose" (default: normal)
ENV LOG_LEVEL=""

ENTRYPOINT ["python3", "bambu-bridge.py"]
