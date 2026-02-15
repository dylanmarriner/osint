"""
Port Scanner Module — No API Keys Required

Async TCP port scanner with service banner grabbing and SSL certificate extraction.
Uses raw socket connections — no external APIs.
"""

import asyncio
import socket
import ssl
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# Top 100 most common TCP ports with service names
COMMON_PORTS: Dict[int, str] = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 111: "RPCBind", 135: "MSRPC", 139: "NetBIOS",
    143: "IMAP", 161: "SNMP", 162: "SNMP-Trap", 179: "BGP",
    389: "LDAP", 443: "HTTPS", 445: "SMB", 465: "SMTPS", 514: "Syslog",
    515: "LPD", 587: "SMTP-Submission", 631: "IPP", 636: "LDAPS",
    993: "IMAPS", 995: "POP3S", 1080: "SOCKS", 1433: "MSSQL", 1434: "MSSQL-UDP",
    1521: "Oracle", 1723: "PPTP", 2049: "NFS", 2082: "cPanel",
    2083: "cPanel-SSL", 2086: "WHM", 2087: "WHM-SSL", 2181: "ZooKeeper",
    3306: "MySQL", 3389: "RDP", 3690: "SVN", 4443: "HTTPS-Alt",
    5432: "PostgreSQL", 5672: "AMQP", 5900: "VNC", 5985: "WinRM",
    5986: "WinRM-SSL", 6379: "Redis", 6443: "Kubernetes-API",
    7001: "WebLogic", 8000: "HTTP-Alt", 8008: "HTTP-Alt2",
    8080: "HTTP-Proxy", 8443: "HTTPS-Alt2", 8888: "HTTP-Alt3",
    9090: "Prometheus", 9200: "Elasticsearch", 9300: "ES-Internal",
    9418: "Git", 11211: "Memcached", 15672: "RabbitMQ-Mgmt",
    27017: "MongoDB", 27018: "MongoDB-Shard", 28017: "MongoDB-Web",
}

# Quick scan — top 20 most targeted ports
QUICK_PORTS = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 993, 995,
               1433, 3306, 3389, 5432, 8080, 8443]


@dataclass
class PortResult:
    port: int
    state: str  # open, closed, filtered
    service: str = ""
    banner: str = ""
    ssl_info: Dict[str, Any] = field(default_factory=dict)
    response_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "port": self.port,
            "state": self.state,
            "service": self.service,
            "response_time_ms": round(self.response_time_ms, 2),
        }
        if self.banner:
            result["banner"] = self.banner
        if self.ssl_info:
            result["ssl_info"] = self.ssl_info
        return result


@dataclass
class ScanReport:
    target: str
    resolved_ip: str = ""
    scan_start: datetime = field(default_factory=datetime.utcnow)
    scan_end: Optional[datetime] = None
    open_ports: List[PortResult] = field(default_factory=list)
    filtered_ports: List[int] = field(default_factory=list)
    total_scanned: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "resolved_ip": self.resolved_ip,
            "scan_start": self.scan_start.isoformat(),
            "scan_end": self.scan_end.isoformat() if self.scan_end else None,
            "scan_duration_seconds": (self.scan_end - self.scan_start).total_seconds() if self.scan_end else None,
            "open_ports": [p.to_dict() for p in self.open_ports],
            "open_port_count": len(self.open_ports),
            "filtered_ports": self.filtered_ports,
            "total_scanned": self.total_scanned,
            "errors": self.errors,
        }


class PortScanner:
    """Async TCP port scanner with banner grabbing and SSL analysis."""

    def __init__(self, timeout: float = 3.0, max_concurrent: int = 100):
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.logger = logging.getLogger(f"{__name__}.PortScanner")

    async def scan(self, target: str, ports: Optional[List[int]] = None,
                   quick: bool = False, grab_banners: bool = True,
                   progress_callback=None) -> ScanReport:
        """Scan target for open ports with optional banner grabbing."""
        report = ScanReport(target=target)

        # Resolve hostname to IP
        try:
            report.resolved_ip = socket.gethostbyname(target)
        except socket.gaierror as e:
            report.errors.append(f"DNS resolution failed: {e}")
            return report

        # Determine port list
        if ports:
            scan_ports = ports
        elif quick:
            scan_ports = QUICK_PORTS
        else:
            scan_ports = list(COMMON_PORTS.keys())

        report.total_scanned = len(scan_ports)
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def scan_port(port: int) -> Optional[PortResult]:
            async with semaphore:
                return await self._check_port(report.resolved_ip, port, grab_banners)

        # Scan all ports concurrently
        tasks = []
        for i, port in enumerate(scan_ports):
            if progress_callback and i % 10 == 0:
                progress_callback(f"Port scan: {i}/{len(scan_ports)}", int((i / len(scan_ports)) * 100))
            tasks.append(scan_port(port))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, PortResult):
                if result.state == "open":
                    report.open_ports.append(result)
                elif result.state == "filtered":
                    report.filtered_ports.append(result.port)
            elif isinstance(result, Exception):
                report.errors.append(str(result))

        # Sort open ports by port number
        report.open_ports.sort(key=lambda p: p.port)
        report.scan_end = datetime.utcnow()

        return report

    async def _check_port(self, ip: str, port: int, grab_banner: bool) -> PortResult:
        """Check if a single port is open and optionally grab its banner."""
        service_name = COMMON_PORTS.get(port, "unknown")
        start = asyncio.get_event_loop().time()

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=self.timeout
            )
            elapsed = (asyncio.get_event_loop().time() - start) * 1000

            result = PortResult(
                port=port, state="open", service=service_name,
                response_time_ms=elapsed
            )

            if grab_banner:
                # Try to grab banner
                banner = await self._grab_banner(reader, writer, port)
                if banner:
                    result.banner = banner

                # Try SSL if it's a known SSL port
                if port in (443, 465, 636, 993, 995, 8443, 2083, 2087):
                    ssl_info = await self._get_ssl_info(ip, port)
                    if ssl_info:
                        result.ssl_info = ssl_info

            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

            return result

        except asyncio.TimeoutError:
            return PortResult(port=port, state="filtered", service=service_name)
        except ConnectionRefusedError:
            return PortResult(port=port, state="closed", service=service_name)
        except OSError:
            return PortResult(port=port, state="filtered", service=service_name)

    async def _grab_banner(self, reader, writer, port: int) -> str:
        """Grab service banner from an open port."""
        try:
            # For HTTP ports, send a request
            if port in (80, 8080, 8000, 8008, 8888):
                writer.write(b"HEAD / HTTP/1.1\r\nHost: target\r\nConnection: close\r\n\r\n")
                await writer.drain()
            elif port == 25 or port == 587:
                pass  # SMTP sends banner automatically
            elif port in (110, 143, 993, 995):
                pass  # POP3/IMAP send banner automatically
            elif port == 21:
                pass  # FTP sends banner automatically

            # Read response with timeout
            data = await asyncio.wait_for(reader.read(1024), timeout=2.0)
            banner = data.decode("utf-8", errors="replace").strip()
            # Limit banner length
            return banner[:500] if banner else ""

        except Exception:
            return ""

    async def _get_ssl_info(self, host: str, port: int) -> Optional[Dict[str, Any]]:
        """Extract SSL/TLS certificate information."""
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port, ssl=ctx),
                timeout=self.timeout
            )

            ssl_obj = writer.get_extra_info("ssl_object")
            if ssl_obj:
                cert = ssl_obj.getpeercert(binary_form=False)
                if not cert:
                    # Try binary form
                    cert_bin = ssl_obj.getpeercert(binary_form=True)
                    writer.close()
                    return {"raw_cert_available": True, "version": ssl_obj.version()}

                info = {
                    "version": ssl_obj.version(),
                    "cipher": ssl_obj.cipher(),
                    "subject": dict(x[0] for x in cert.get("subject", ())),
                    "issuer": dict(x[0] for x in cert.get("issuer", ())),
                    "serial_number": cert.get("serialNumber"),
                    "not_before": cert.get("notBefore"),
                    "not_after": cert.get("notAfter"),
                    "san": [entry[1] for entry in cert.get("subjectAltName", ())],
                }

                writer.close()
                return info

            writer.close()
            return None

        except Exception:
            return None

    async def scan_port_range(self, target: str, start_port: int, end_port: int,
                               progress_callback=None) -> ScanReport:
        """Scan a custom port range."""
        ports = list(range(start_port, end_port + 1))
        return await self.scan(target, ports=ports, progress_callback=progress_callback)
