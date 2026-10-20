# nightlink-cyberdeck

## Nightlink Radar — passive BLE proximity scanner

`nightlink_radar.py` listens to public Bluetooth LE advertisement broadcasts (the same
packets Find My / Tile / AirTag scanners read) and draws a live ASCII radar of nearby
devices by estimated distance, using signal strength (RSSI).

**Read-only by design:** it never pairs, connects, writes to, or otherwise interacts with
any device — it only observes broadcasts anyone nearby is already sending. Distance is a
rough RSSI-based estimate (±2-3 m), since BLE doesn't carry a real bearing.

### Setup

```bash
pip install -r requirements.txt
python3 nightlink_radar.py
```

On macOS, grant Bluetooth permission to your terminal the first time it runs:
**System Settings → Privacy & Security → Bluetooth**.

### Output

Each detected device gets a letter marker placed on the radar at its estimated distance,
with a legend below listing name, RSSI, estimated distance and MAC address. Devices are
dropped from the display after 15 seconds of silence.