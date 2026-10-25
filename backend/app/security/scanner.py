import socket
import struct
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel
from typing import Optional
from app.core.config import settings
from app.core.logging import logger

EICAR_SIGNATURE = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


class ScanStatus(str, Enum):
    UPLOADED = "UPLOADED"
    QUARANTINED = "QUARANTINED"
    SCANNING = "SCANNING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class ScanResult(BaseModel):
    status: ScanStatus
    details: str
    scan_timestamp: str
    is_clean: bool
    rejection_reason: Optional[str] = None


class AntivirusScanner:
    def __init__(self, host: str = settings.CLAMAV_HOST, port: int = settings.CLAMAV_PORT, enabled: bool = settings.CLAMAV_ENABLED):
        self.host = host
        self.port = port
        self.enabled = enabled

    def _scan_with_clamav(self, data: bytes) -> ScanResult:
        """Communicates with ClamAV daemon using the INSTREAM network socket protocol."""
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10.0)
                s.connect((self.host, self.port))
                # Send zINSTREAM\0
                s.sendall(b"zINSTREAM\0")

                # Stream file in chunks
                chunk_size = 2048
                for i in range(0, len(data), chunk_size):
                    chunk = data[i:i + chunk_size]
                    # Format: 4 bytes big-endian length + chunk
                    s.sendall(struct.pack("!I", len(chunk)) + chunk)
                # Terminate stream with zero length chunk
                s.sendall(struct.pack("!I", 0))

                response = b""
                while True:
                    recv_chunk = s.recv(1024)
                    if not recv_chunk:
                        break
                    response += recv_chunk

                resp_str = response.decode("utf-8", errors="ignore").strip()
                logger.info(f"ClamAV scan response: {resp_str}")

                if "FOUND" in resp_str:
                    return ScanResult(
                        status=ScanStatus.REJECTED,
                        details=resp_str,
                        scan_timestamp=now_iso,
                        is_clean=False,
                        rejection_reason=f"Malware detected by ClamAV: {resp_str}",
                    )
                elif "OK" in resp_str:
                    return ScanResult(
                        status=ScanStatus.ACCEPTED,
                        details="ClamAV Verified: Clean payload",
                        scan_timestamp=now_iso,
                        is_clean=True,
                    )
                else:
                    return ScanResult(
                        status=ScanStatus.QUARANTINED,
                        details=f"Unrecognized scanner output: {resp_str}",
                        scan_timestamp=now_iso,
                        is_clean=False,
                        rejection_reason="Scanner output inconclusive. Document quarantined.",
                    )
        except Exception as e:
            logger.warning(f"ClamAV daemon connection error: {e}. Preserving quarantine state.")
            return ScanResult(
                status=ScanStatus.QUARANTINED,
                details=f"Antivirus scanner daemon unavailable: {str(e)}. Preserved in quarantine.",
                scan_timestamp=now_iso,
                is_clean=False,
                rejection_reason="Scanner unavailable. Security policy requires document to remain quarantined.",
            )

    def scan_bytes(self, data: bytes, allow_simulation_pass: bool = False) -> ScanResult:
        """
        Executes malware scanning on uploaded file bytes.
        Statutory Security Guarantee:
        - If ClamAV is enabled, queries the live ClamAV daemon.
        - Checks for known malware signatures including EICAR standard test strings.
        - If the scanner is unavailable and simulation is not explicitly enabled for testing,
          the document remains QUARANTINED. It is never marked clean without scan completion.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Immediate signature check for EICAR test string
        if EICAR_SIGNATURE in data:
            logger.warning("EICAR test malware signature detected. Rejecting upload immediately.")
            return ScanResult(
                status=ScanStatus.REJECTED,
                details="EICAR test virus signature detected in stream.",
                scan_timestamp=now_iso,
                is_clean=False,
                rejection_reason="Malware test signature detected (EICAR).",
            )

        # 2. Live ClamAV scanner integration
        if self.enabled:
            return self._scan_with_clamav(data)

        # 3. Development / Local Environment mode
        if allow_simulation_pass:
            # Controlled safe test environment: verified byte signature and no virus
            return ScanResult(
                status=ScanStatus.ACCEPTED,
                details="Local Antivirus Simulation: Clean signature verified.",
                scan_timestamp=now_iso,
                is_clean=True,
            )

        # By default, when ClamAV is disabled and simulation is not allowed:
        return ScanResult(
            status=ScanStatus.QUARANTINED,
            details="Scanner service not connected. Document safely retained in quarantine.",
            scan_timestamp=now_iso,
            is_clean=False,
            rejection_reason="Antivirus scanning pending. Document not yet approved for user access.",
        )


scanner = AntivirusScanner()
