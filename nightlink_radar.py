#!/usr/bin/env python3
"""Nightlink Radar — passive Bluetooth LE proximity scanner.

READ-ONLY by design: this listens to public BLE advertisement broadcasts
only (the same packets Find My / Tile / AirTag scanners read). It never
pairs, connects, or writes to any device. No consent is implied or needed
for receiving a public broadcast, but this tool still does not act on
anything beyond showing you what's nearby and how strong its signal is.

Install:  pip install -r requirements.txt
Run:      python3 nightlink_radar.py
"""
from __future__ import annotations

import asyncio
import math
import os
import time
from dataclasses import dataclass, field

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

# ---- tunables -----------------------------------------------------------
REFRESH_SECS = 1.0          # how often the radar redraws
STALE_AFTER_SECS = 15.0     # drop a device if we haven't heard it in this long
RADAR_RADIUS = 11           # character radius of the radar circle
RSSI_AT_1M = -59            # typical calibration constant for BLE beacons
PATH_LOSS_N = 2.0           # path-loss exponent (2 = free space, higher = more obstacles)


@dataclass
class SeenDevice:
    address: str
    name: str
    rssi: int
    last_seen: float = field(default_factory=time.time)

    def distance_m(self) -> float:
        """Rough RSSI -> distance estimate. BLE RSSI is noisy; treat as approximate."""
        if self.rssi == 0:
            return -1.0
        ratio = (RSSI_AT_1M - self.rssi) / (10 * PATH_LOSS_N)
        return round(10 ** ratio, 1)

    def angle(self) -> float:
        """BLE gives no real bearing; derive a stable pseudo-angle from the MAC
        so each device keeps the same radar position between redraws."""
        h = sum(self.address.encode()) if self.address else 0
        return (h % 360) * (math.pi / 180)


class RadarState:
    def __init__(self):
        self.devices: dict[str, SeenDevice] = {}

    def update(self, device: BLEDevice, adv: AdvertisementData) -> None:
        name = adv.local_name or device.name or "(unnamed)"
        self.devices[device.address] = SeenDevice(
            address=device.address, name=name, rssi=adv.rssi if adv.rssi is not None else -127
        )

    def prune(self) -> None:
        now = time.time()
        stale = [a for a, d in self.devices.items() if now - d.last_seen > STALE_AFTER_SECS]
        for a in stale:
            del self.devices[a]

    def render(self) -> str:
        size = RADAR_RADIUS * 2 + 1
        grid = [[" "] * size for _ in range(size)]
        cx = cy = RADAR_RADIUS

        # concentric range rings
        for r in range(1, RADAR_RADIUS + 1, 3):
            for deg in range(0, 360, 6):
                rad = math.radians(deg)
                x = cx + round(r * math.cos(rad))
                y = cy + round(r * math.sin(rad))
                if 0 <= x < size and 0 <= y < size and grid[y][x] == " ":
                    grid[y][x] = "."
        grid[cy][cx] = "@"  # you are here

        rows_meta = []
        for i, d in enumerate(sorted(self.devices.values(), key=lambda d: d.distance_m())):
            dist = d.distance_m()
            scaled = min(dist, 30.0) / 30.0 * RADAR_RADIUS if dist >= 0 else RADAR_RADIUS
            ang = d.angle()
            x = cx + round(scaled * math.cos(ang))
            y = cy + round(scaled * math.sin(ang))
            x = max(0, min(size - 1, x))
            y = max(0, min(size - 1, y))
            marker = chr(ord("A") + i) if i < 26 else "*"
            grid[y][x] = marker
            rows_meta.append(f"  {marker}  {d.name:<24} {d.rssi:>5} dBm  ~{dist if dist >= 0 else '?'} m  {d.address}")

        lines = ["".join(row) for row in grid]
        header = f"Nightlink Radar — passive BLE scan (no connections) — {len(self.devices)} nearby"
        return "\n".join([header, "=" * len(header), *lines, "-" * 40, *rows_meta]) if rows_meta else \
            "\n".join([header, "=" * len(header), *lines, "-" * 40, "  (listening...)"])


async def main() -> None:
    state = RadarState()

    def on_detect(device: BLEDevice, adv: AdvertisementData) -> None:
        state.update(device, adv)

    async with BleakScanner(detection_callback=on_detect):
        try:
            while True:
                state.prune()
                os.system("clear" if os.name != "nt" else "cls")
                print(state.render())
                await asyncio.sleep(REFRESH_SECS)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    asyncio.run(main())
