"""
flexradio_client.py
-------------------
A Python client for the FlexRadio SmartSDR TCP/IP API.

Connects to a FLEX-6000/8000 series radio on port 4992,
sends commands, and streams status responses.

Built by JP Pacheco — based on field experience at FlexRadio Systems (2020–2022)
and the official SmartSDR TCP/IP API documentation.

API Reference: https://github.com/flexradio/smartsdr-api-docs/wiki/SmartSDR-TCPIP-API
"""

import socket
import threading
import time
import logging
from typing import Optional, Callable

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("flexradio")


# ── Constants ──────────────────────────────────────────────────────────────────
SMARTSDR_PORT = 4992
DEFAULT_TIMEOUT = 5.0
BUFFER_SIZE = 4096


# ── FlexRadio Client ───────────────────────────────────────────────────────────
class FlexRadioClient:
    """
    TCP/IP client for the SmartSDR API.

    Usage:
        radio = FlexRadioClient("192.168.1.100")
        radio.connect()
        radio.set_frequency(slice_id=0, freq_mhz=14.225)
        radio.set_mode(slice_id=0, mode="USB")
        radio.get_info()
        radio.disconnect()
    """

    def __init__(self, host: str, port: int = SMARTSDR_PORT, timeout: float = DEFAULT_TIMEOUT):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._sequence = 1
        self._running = False
        self._listener_thread: Optional[threading.Thread] = None
        self._response_callback: Optional[Callable[[str], None]] = None

    # ── Connection ─────────────────────────────────────────────────────────────

    def connect(self) -> bool:
        """Connect to the radio and start the response listener."""
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(self.timeout)
            self._sock.connect((self.host, self.port))
            self._running = True
            self._listener_thread = threading.Thread(
                target=self._listen, daemon=True
            )
            self._listener_thread.start()
            log.info(f"Connected to FlexRadio at {self.host}:{self.port}")
            return True
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            log.error(f"Connection failed: {e}")
            return False

    def disconnect(self):
        """Gracefully disconnect from the radio."""
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        log.info("Disconnected from FlexRadio.")

    def set_response_callback(self, callback: Callable[[str], None]):
        """Register a callback to receive all status/response lines from the radio."""
        self._response_callback = callback

    # ── Internal Listener ──────────────────────────────────────────────────────

    def _listen(self):
        """Background thread: reads lines from the radio and logs/dispatches them."""
        buffer = ""
        while self._running and self._sock:
            try:
                data = self._sock.recv(BUFFER_SIZE).decode("utf-8", errors="replace")
                if not data:
                    log.warning("Radio closed the connection.")
                    break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        log.debug(f"<< {line}")
                        if self._response_callback:
                            self._response_callback(line)
                        else:
                            self._handle_response(line)
            except socket.timeout:
                continue
            except OSError:
                break

    def _handle_response(self, line: str):
        """Default response handler — logs version, handles, messages, and status."""
        if line.startswith("V"):
            log.info(f"Radio protocol version: {line[1:]}")
        elif line.startswith("H"):
            log.info(f"Client handle assigned: {line[1:]}")
        elif line.startswith("M"):
            parts = line[1:].split("|", 1)
            msg_num = parts[0] if parts else "?"
            msg_text = parts[1] if len(parts) > 1 else ""
            severity = (int(msg_num, 16) >> 24) & 0x3
            levels = {0: "INFO", 1: "WARNING", 2: "ERROR", 3: "FATAL"}
            log.log(
                [logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL][severity],
                f"Radio message [{levels.get(severity, '?')}]: {msg_text}"
            )
        elif line.startswith("S"):
            log.info(f"Status: {line[1:]}")
        elif line.startswith("R"):
            log.info(f"Response: {line[1:]}")

    # ── Command Interface ──────────────────────────────────────────────────────

    def _send(self, command: str) -> int:
        """Send a sequenced command to the radio. Returns sequence number."""
        if not self._sock:
            log.error("Not connected — cannot send command.")
            return -1
        seq = self._sequence
        full_cmd = f"C{seq}|{command}\n"
        try:
            self._sock.sendall(full_cmd.encode("utf-8"))
            log.debug(f">> {full_cmd.strip()}")
            self._sequence += 1
        except OSError as e:
            log.error(f"Send failed: {e}")
            return -1
        return seq

    def get_info(self) -> int:
        """Request radio version and firmware info."""
        return self._send("version")

    def get_antenna_list(self) -> int:
        """Request list of available antennas."""
        return self._send("antenna list")

    def set_frequency(self, slice_id: int, freq_mhz: float) -> int:
        """
        Tune a slice receiver to a specific frequency.

        Args:
            slice_id: Slice index (0-based)
            freq_mhz: Frequency in MHz (e.g., 14.225 for 20m SSB)
        """
        return self._send(f"slice tune {slice_id} {freq_mhz:.6f}")

    def set_mode(self, slice_id: int, mode: str) -> int:
        """
        Set demodulation mode on a slice.

        Args:
            slice_id: Slice index (0-based)
            mode: Mode string — USB, LSB, AM, FM, CW, DIGU, DIGL, SAM, etc.
        """
        return self._send(f"slice set {slice_id} mode={mode.upper()}")

    def set_tx_power(self, power_watts: int) -> int:
        """
        Set transmit power level.

        Args:
            power_watts: Power in watts (1–100 for most FLEX-6000 models)
        """
        return self._send(f"transmit set rfpower={power_watts}")

    def enable_tx(self, enabled: bool = True) -> int:
        """Enable or disable transmit."""
        state = "1" if enabled else "0"
        return self._send(f"transmit set tx={state}")

    def get_slice_status(self, slice_id: int) -> int:
        """Request current status of a slice receiver."""
        return self._send(f"slice get {slice_id}")

    def subscribe_meters(self) -> int:
        """Subscribe to real-time meter streaming (SWR, power, temp, etc.)."""
        return self._send("sub meter all")

    def unsubscribe_meters(self) -> int:
        """Unsubscribe from meter streaming."""
        return self._send("unsub meter all")

    def raw(self, command: str) -> int:
        """Send a raw command string to the radio."""
        return self._send(command)


# ── Discovery (UDP Broadcast) ──────────────────────────────────────────────────

def discover_radios(timeout: float = 3.0) -> list[dict]:
    """
    Discover FlexRadio devices on the local network using UDP broadcast.

    The SmartSDR discovery protocol broadcasts on UDP port 4992.
    Returns a list of dicts with 'ip', 'model', and 'serial' keys.

    Args:
        timeout: How long to listen for discovery responses (seconds)

    Returns:
        List of discovered radio info dicts
    """
    discovered = []
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)
        sock.bind(("", SMARTSDR_PORT))
        log.info(f"Listening for FlexRadio discovery broadcasts for {timeout}s...")
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                data, addr = sock.recvfrom(BUFFER_SIZE)
                message = data.decode("utf-8", errors="replace").strip()
                log.info(f"Discovery response from {addr[0]}: {message}")
                info = {"ip": addr[0], "raw": message}
                # Parse key=value pairs from discovery packet
                for token in message.split(" "):
                    if "=" in token:
                        k, v = token.split("=", 1)
                        info[k.lower()] = v
                discovered.append(info)
            except socket.timeout:
                break
        sock.close()
    except OSError as e:
        log.error(f"Discovery failed: {e}")
    return discovered


# ── CLI Demo ───────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="FlexRadio SmartSDR Python Client — JP Pacheco / jeypnet"
    )
    parser.add_argument("--host", default=None, help="Radio IP address (skip to auto-discover)")
    parser.add_argument("--freq", type=float, default=14.225, help="Frequency in MHz (default: 14.225)")
    parser.add_argument("--mode", default="USB", help="Mode: USB, LSB, AM, FM, CW (default: USB)")
    parser.add_argument("--slice", type=int, default=0, help="Slice ID (default: 0)")
    parser.add_argument("--discover", action="store_true", help="Run discovery only")
    args = parser.parse_args()

    if args.discover or not args.host:
        log.info("Running network discovery...")
        radios = discover_radios()
        if not radios:
            log.warning("No radios found on network.")
            return
        for r in radios:
            print(f"  Found: {r}")
        if not args.host:
            args.host = radios[0]["ip"]
            log.info(f"Auto-selected: {args.host}")

    radio = FlexRadioClient(args.host)
    if not radio.connect():
        log.error("Could not connect. Check IP address and that SmartSDR is running.")
        return

    time.sleep(1)  # Let the listener receive the version/handle handshake

    log.info(f"Requesting radio info...")
    radio.get_info()
    time.sleep(0.5)

    log.info(f"Tuning slice {args.slice} to {args.freq} MHz, mode {args.mode}")
    radio.set_frequency(slice_id=args.slice, freq_mhz=args.freq)
    radio.set_mode(slice_id=args.slice, mode=args.mode)
    time.sleep(0.5)

    log.info("Requesting antenna list...")
    radio.get_antenna_list()
    time.sleep(0.5)

    log.info("Subscribing to meter stream (5 seconds)...")
    radio.subscribe_meters()
    time.sleep(5)
    radio.unsubscribe_meters()

    radio.disconnect()


if __name__ == "__main__":
    main()
