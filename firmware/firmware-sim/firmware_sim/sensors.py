"""Dummy sensor model.

Generates believable, smoothly-drifting synthetic sensor readings so the
simulator looks like a real aeroponic node during testing. Each sensor keeps
its own state (value + phase) and does a bounded random walk with a slow sine
overlay, so trends look natural instead of pure noise.

For every configured input it returns both the engineering value (e.g. 26.4 C)
and the equivalent raw ADC reading (0..4095) used by the firmware-style
``telemetry.inputs`` field.

The mapping is heuristic: it infers the sensor type from the input *name*
(temp / humid / level / press / co2 / lux / ph / tds / flow / ec ...). Anything
unknown falls back to a generic 0..4095 analog value.
"""

from __future__ import annotations

import math
import random
import time

# name-substring -> (unit, base, amplitude, lo, hi, raw_max)
# Abbreviated names (hum, temp) are listed first so exact-match in _profile_for
# resolves them before the substring pass can collide with longer keys.
_PROFILES: dict[str, tuple[str, float, float, float, float, int]] = {
    "hum":            ("%",     70.0, 6.0, 40.0, 95.0, 4095),
    "temp":           ("C",     26.0, 2.0, 18.0, 35.0, 4095),
    "temp_nutrisi":   ("C",     25.0, 1.5, 20.0, 32.0, 4095),
    "humid":          ("%",     70.0, 6.0, 40.0, 95.0, 4095),
    "press":          ("hPa", 1013.0, 4.0, 990.0, 1030.0, 4095),
    "co2":            ("ppm",  600.0, 120.0, 400.0, 1200.0, 4095),
    "lux":            ("lx",  8000.0, 3000.0, 0.0, 20000.0, 4095),
    "ph":             ("",       6.5, 0.4, 4.0, 9.0, 4095),
    "ph_nutrisi":     ("",       6.0, 0.3, 4.5, 7.5, 4095),
    "tds":            ("ppm",  350.0, 80.0, 0.0, 1000.0, 4095),
    "ec":             ("mS/cm", 1.6, 0.4, 0.0, 4.0, 4095),
    "ec_nutrisi":     ("mS/cm", 1.8, 0.3, 0.5, 3.5, 4095),
    "flow":           ("L/min", 2.0, 0.8, 0.0, 6.0, 4095),
    "level":          ("",       1.0, 0.0, 0.0, 1.0, 1),
    "volt":           ("V",    220.0, 5.0, 200.0, 240.0, 4095),
    "current":        ("A",     1.2, 0.4, 0.0, 5.0, 4095),
    "amp":            ("A",     1.2, 0.4, 0.0, 5.0, 4095),
    "power":          ("W",    250.0, 60.0, 0.0, 800.0, 4095),
    "watt":           ("W",    250.0, 60.0, 0.0, 800.0, 4095),
}


def _profile_for(name: str, is_digital: bool):
    if is_digital:
        # digital sensors (buttons, level switches) are 0/1
        return ("", 0.0, 0.0, 0.0, 1.0, 1)
    n = name.lower()
    if n in _PROFILES:
        return _PROFILES[n]
    for key, prof in _PROFILES.items():
        if key in n:
            return prof
    # generic analog fallback
    return ("", 2000.0, 300.0, 0.0, 4095.0, 4095)


class DummySensorModel:
    def __init__(self) -> None:
        self._state: dict[str, dict] = {}

    def _ensure(self, name: str, input_def: dict) -> dict:
        if name in self._state:
            return self._state[name]
        is_digital = input_def.get("type") == "DIGITAL"
        unit, base, amp, lo, hi, raw_max = _profile_for(name, is_digital)
        self._state[name] = {
            "value": base,
            "phase": random.uniform(0, 2 * math.pi),
            "unit": unit,
            "amp": amp,
            "lo": lo,
            "hi": hi,
            "raw_max": raw_max,
            "digital": is_digital,
        }
        return self._state[name]

    def sample(self, name: str, input_def: dict, forced: float | None = None) -> tuple[float, int, str]:
        """Return (engineering_value, raw_adc, unit) for one input."""
        st = self._ensure(name, input_def)
        if forced is not None:
            st["value"] = float(forced)
        elif st["digital"]:
            # digital switches are stable at rest; they only change when an
            # external force is applied (e.g. emergency button pressed).
            pass
        else:
            drift = (random.uniform(-1, 1) * st["amp"] * 0.15
                     + math.sin(time.time() / 25.0 + st["phase"]) * st["amp"] * 0.4)
            st["value"] = max(st["lo"], min(st["hi"], st["value"] + drift))

        val = st["value"]
        if st["digital"]:
            raw = 1 if val > 0.5 else 0
            if input_def.get("invert"):
                raw = 0 if raw else 1
            eng = float(raw)
        else:
            span = max(1.0, st["hi"] - st["lo"])
            norm = (val - st["lo"]) / span
            raw = int(max(0, min(st["raw_max"], norm * st["raw_max"])))
            eng = val
        return eng, raw, st["unit"]

    def unit_of(self, name: str) -> str:
        st = self._state.get(name)
        return st["unit"] if st else ""
