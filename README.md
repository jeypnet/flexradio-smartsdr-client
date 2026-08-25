# flexradio-smartsdr-client

**Python client for the FlexRadio SmartSDR TCP/IP API**

A lightweight Python library and CLI tool for connecting to, controlling, and monitoring FLEX-6000 and FLEX-8000 series software-defined radios over TCP/IP.

---

## Background

At [FlexRadio Systems](https://flexradio.com) I worked pre-sale and post-sale technical engagements across defense, utilities, and emergency response customers. A recurring challenge was helping customers automate frequency management, monitor radio health, and integrate FlexRadio hardware into larger command and control workflows.

This client addresses that directly. It is a clean Python interface to the SmartSDR TCP/IP API that any operator or systems integrator can drop into their stack.

---

## What It Does

- **Auto-discovers** FlexRadio devices on the local network via UDP broadcast
- **Connects** to the radio over TCP port 4992 (the SmartSDR command interface)
- **Tunes** slice receivers to specific frequencies and modes
- **Monitors** real-time meter data (SWR, RF power, temperature)
- **Sends raw commands** for full API access
- **Streams status responses** with a callback interface for integration into larger systems

---

## Quickstart

```bash
git clone https://github.com/jeypnet/flexradio-smartsdr-client.git
cd flexradio-smartsdr-client
python flexradio_client.py --discover
```

No dependencies. Standard library only (`socket`, `threading`, `argparse`, `logging`).

---

## CLI

**Discover radios on the local network:**
```bash
python flexradio_client.py --discover
```

**Connect and tune a slice:**
```bash
python flexradio_client.py --host 192.168.1.50 --freq 14.225 --mode USB --slice 0
```

| Flag | Default | Meaning |
|---|---|---|
| `--host` | auto-discover | Radio IP address |
| `--freq` | `14.225` | Frequency in MHz |
| `--mode` | `USB` | USB, LSB, AM, FM, CW |
| `--slice` | `0` | Slice receiver ID |
| `--discover` | off | Run discovery only, then exit |

---

## Library Use

```python
from flexradio_client import FlexRadioClient, discover_radios

radios = discover_radios(timeout=3.0)
client = FlexRadioClient(radios[0]["ip"])

client.set_response_callback(lambda line: print("radio:", line))
client.connect()

client.set_frequency(slice_id=0, freq_mhz=14.225)
client.set_mode(slice_id=0, mode="USB")
client.subscribe_meters()

client.disconnect()
```

### API surface

| Method | Purpose |
|---|---|
| `discover_radios(timeout)` | UDP broadcast discovery on port 4992, returns radio info dicts |
| `connect()` / `disconnect()` | Open and close the TCP command session |
| `set_response_callback(fn)` | Register a callback fired on every status line the radio streams back |
| `set_frequency(slice_id, freq_mhz)` | Tune a slice receiver |
| `set_mode(slice_id, mode)` | Set demodulation mode |
| `set_tx_power(power_watts)` | Set transmit power |
| `enable_tx(enabled)` | Enable or disable transmit |
| `get_slice_status(slice_id)` | Query slice state |
| `subscribe_meters()` / `unsubscribe_meters()` | Start and stop the real-time meter stream |
| `get_info()` / `get_antenna_list()` | Radio identity and antenna configuration |
| `raw(command)` | Send any SmartSDR command directly |

Each call returns the sequence number SmartSDR assigns to the command, so responses can be correlated on the callback stream.

---

## Notes

Discovery listens for the SmartSDR discovery broadcast on UDP 4992 and parses the `key=value` pairs the radio advertises. The command session runs on TCP 4992 with a background listener thread, so status and meter updates arrive asynchronously while your code keeps issuing commands.

---

*Part of the [jeypnet](https://github.com/jeypnet) project portfolio.*
*Extra Class amateur radio operator. FlexRadio Systems alumnus.*
