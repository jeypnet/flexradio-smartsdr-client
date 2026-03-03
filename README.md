# flexradio-smartsdr-client

**Python client for the FlexRadio SmartSDR TCP/IP API**

A lightweight Python library and CLI tool for connecting to, controlling, and monitoring FLEX-6000 and FLEX-8000 series software-defined radios over TCP/IP.

Built by someone who sold these radios for two years — and spent a lot of time on the phone with engineers, defense operators, and emergency response teams making sure they actually worked.

---

## Background

During my time at [FlexRadio Systems](https://flexradio.com) (2020–2022), I worked pre- and post-sale technical engagements across defense, utilities, and emergency response customers. A recurring challenge was helping customers automate frequency management, monitor radio health, and integrate FlexRadio hardware into larger command and control workflows.

This client addresses that directly — a clean Python interface to the SmartSDR TCP/IP API that any operator or systems integrator can drop into their stack.

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
```bash# flexradio-smartsdr-client
