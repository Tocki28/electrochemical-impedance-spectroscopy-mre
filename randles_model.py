"""
Randles equivalent-circuit impedance model for an iridium anode
in a molten iron-oxide electrolysis bath (~1600 °C).

Circuit topology: Rs — [ Rct + W ] ║ Cdl

  Rs   : solution (electrolyte) resistance
  Rct  : charge-transfer resistance at the anode/melt interface
  Cdl  : double-layer capacitance
  W    : semi-infinite Warburg diffusion element

All impedances are in Ohms; frequencies in Hz; capacitance in Farads;
Warburg coefficient sigma in Ω·s^{-1/2}.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, asdict


@dataclass
class RandlesParams:
    Rs: float     # Ω  — solution resistance
    Rct: float    # Ω  — charge-transfer resistance
    Cdl: float    # F  — double-layer capacitance
    sigma: float  # Ω·s^{-1/2} — Warburg coefficient

    def to_dict(self) -> dict:
        return asdict(self)

    def copy(self, **overrides) -> "RandlesParams":
        d = asdict(self)
        d.update(overrides)
        return RandlesParams(**d)


def randles_impedance(params: RandlesParams, frequencies: np.ndarray) -> np.ndarray:
    """
    Return the complex impedance Z(f) for the Randles circuit.

    Warburg: Z_W = sigma*(1-j)/sqrt(omega)  — 45-degree line at low freq.
    """
    omega = 2.0 * np.pi * np.asarray(frequencies, dtype=float)

    Z_W = params.sigma * (1.0 - 1j) / np.sqrt(omega)
    Z_series = params.Rct + Z_W
    Z_dl = 1.0 / (1j * omega * params.Cdl)
    Z_parallel = (Z_series * Z_dl) / (Z_series + Z_dl)

    return params.Rs + Z_parallel


def moe_anode_baseline() -> RandlesParams:
    """
    Synthetic baseline parameters for a healthy iridium anode in a
    molten Fe2O3/SiO2 oxide melt at ~1600 °C.

    Values are order-of-magnitude estimates consistent with the published
    MOE electrode literature (Sadoway 2012, Allanore 2013, Sirk 2010).
    They are NOT measured data — they are a physically plausible starting
    point for the Month-2 simulation exercise.

    Rs:    ~1 Ω  — molten oxide has ionic conductivity ≈ 1–10 S/cm at 1600 °C,
                   far higher than room-temperature aqueous; cell gap ~1 cm.
    Rct:   ~8 Ω  — moderate anode kinetics on fresh iridium surface.
    Cdl:  250 μF — high-temperature double layer; larger than aqueous room-T.
    sigma: 3.5   — diffusion is faster at 1600 °C but oxide melt is viscous.
    """
    return RandlesParams(
        Rs=1.2,
        Rct=8.0,
        Cdl=2.5e-4,
        sigma=3.5,
    )


def moe_frequencies(n_per_decade: int = 10) -> np.ndarray:
    """
    Standard EIS sweep for a molten-oxide cell: 10 kHz → 10 mHz.

    At high temperature the double-layer time constant is fast, so useful
    information starts appearing around 10 kHz.  The Warburg tail resolves
    below ~1 Hz.  0.01 Hz is the practical low-frequency floor before
    measurement drift dominates in a real furnace experiment.
    """
    return np.logspace(4, -2, n_per_decade * 6)  # 6 decades


def add_noise(Z: np.ndarray, snr_db: float = 40.0, rng: np.random.Generator | None = None) -> np.ndarray:
    """Add complex Gaussian noise at the specified SNR (in dB)."""
    if rng is None:
        rng = np.random.default_rng()
    sigma_noise = np.abs(Z) * 10 ** (-snr_db / 20.0)
    noise = rng.normal(0, sigma_noise / np.sqrt(2), Z.shape) + \
            1j * rng.normal(0, sigma_noise / np.sqrt(2), Z.shape)
    return Z + noise


def nyquist_arrays(Z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (Re Z, −Im Z) for Nyquist plotting (convention: inductive up)."""
    return np.real(Z), -np.imag(Z)


def bode_arrays(Z: np.ndarray, frequencies: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (frequencies, |Z| in Ω, phase in degrees)."""
    return frequencies, np.abs(Z), np.degrees(np.angle(Z))
