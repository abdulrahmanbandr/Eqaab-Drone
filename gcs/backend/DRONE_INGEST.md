# Switching the GCS from simulator to the real on-board Pi

The GCS backend is a **message broker**: it receives drone messages, persists them, and
relays them to frontend clients unchanged. In development it generates those messages with
an in-process simulator. The real Raspberry Pi edge node (`/onboard`) is a **drop-in
replacement** — it connects to the same `/ws` endpoint and emits the exact same
`schemas.py` messages, so **the frontend needs zero changes**.

## What changed in `main.py`

The `/ws` receive loop now handles messages that *originate from the drone* and relays them
to all frontend clients (additive, backward-compatible):

```python
elif msg_type in ("telemetry", "detection", "event", "alert", "command_ack"):
    await ws_manager.broadcast(msg)          # relay to all GCS frontend clients
    if msg_type == "detection":
        mission.add_alert(msg)               # persist to history
    elif msg_type == "event":
        mission.add_event(msg)
```

Commands now route to the drone when the simulator is off:

```python
elif msg_type == "command":
    if simulator is not None:
        ... # dev: handle locally, broadcast ACK
    else:
        await ws_manager.broadcast(msg)      # real: forward command to the Pi
```

## How to run with the real drone

1. **Turn the simulator off** in `config.py`:
   ```python
   SIMULATOR_ENABLED = False
   ```
   (or wire it to an env var). With the simulator off, the backend stops generating
   synthetic telemetry and instead relays whatever the Pi sends.

2. **Start the backend** as usual:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

3. **Point the Pi at this backend** — in the Pi's `.env`:
   ```
   GCS_WS_URL=wss://your-public-host/ws
   ```
   The Pi opens the outbound WSS, streams `telemetry` at 1 Hz, sends `detection` on
   confirmed targets, and accepts `command` messages.

## Why this is safe / minimal

* **No frontend changes.** The messages on the wire are identical to the simulator's.
* **Backward compatible.** With `SIMULATOR_ENABLED = True`, behaviour is unchanged; the new
  branches only fire for drone-origin message types, which the simulator never sends.
* **Broker stays a broker.** Content is relayed verbatim; the backend does not transform it.
