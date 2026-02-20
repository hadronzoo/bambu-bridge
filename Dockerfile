FROM python:3.13-slim

WORKDIR /app

COPY bambu-bridge.py .

# Printer-side VLAN interface (where printers live)
ENV SOURCE_IFACE=lan1.50
# Client-side VLAN interface (where PCs/phones live)
ENV TARGET_IFACE=lan1.10
# Standard Python log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
ENV LOG_LEVEL=INFO

ENTRYPOINT ["python3", "bambu-bridge.py"]
