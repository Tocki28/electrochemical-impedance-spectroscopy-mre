"""
Parametric degradation models for an iridium anode in molten oxide electrolysis.

Two independent degradation modes, both producing time-series of Randles parameters:

  1. Oxidation   — IrO2 / IrO3 passivation layer grows on the anode surface.
                   Physical effect: a resistive film blocks charge transfer.
                   Circuit signature: Rct rises; Cdl falls (film adds series R,
                   parallel C is diluted by the film's own capacitance).

  2. Evaporation — IrO3 is volatile above ~1100 °C; it sublimates, removing
                   electrode mass and shrinking the active surface area.
                   Circuit signature: effective area A decreases exponentially,
                   which scales Rct ∝ 1/A (↑) and Cdl ∝ A (↓).
                   Diffusion path lengthens as pits form: sigma rises.

Both modes are parametric (no CFD / multi-physics); parameters are tuned so that
the "failure" threshold is reached at a chosen horizon.  The simulation is meant
to test the detector, not to replace a real experiment.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field

from randles_model import RandlesParams, moe_anode_baseline, moe_frequencies, randles_impedance, add_noise


# ── Failure thresholds ────────────────────────────────────────────────────────
# Rct more than 5× its baseline → anode is effectively dead (current efficiency
# has collapsed, cell voltage has spiked into thermal-runaway territory).
RCT_FAILURE_MULTIPLIER = 5.0

# Fraction of original area at which the anode is considered failed by evaporation.
AREA_FAILURE_FRACTION = 0.15


@dataclass
class DegradationScenario:
    name: str
    hours: np.ndarray                # shape (n_steps,)
    params: list[RandlesParams]      # len == n_steps
    failure_hour: float | None       # first hour where failure threshold is crossed

    def spectra(
        self,
        frequencies: np.ndarray | None = None,
        snr_db: float | None = None,
        rng: np.random.Generator | None = None,
    ) -> np.ndarray:
        """
        Return complex impedance array of shape (n_steps, n_freq).

        If snr_db is given, add Gaussian noise at that SNR.
        """
        if frequencies is None:
            frequencies = moe_frequencies()
        Z = np.array([randles_impedance(p, frequencies) for p in self.params])
        if snr_db is not None:
            Z = add_noise(Z, snr_db=snr_db, rng=rng)
        return Z

    def rct_series(self) -> np.ndarray:
        return np.array([p.Rct for p in self.params])

    def rs_series(self) -> np.ndarray:
        return np.array([p.Rs for p in self.params])

    def cdl_series(self) -> np.ndarray:
        return np.array([p.Cdl for p in self.params])


# ── Mode 1: Oxidation ─────────────────────────────────────────────────────────

def oxidation_trajectory(
    baseline: RandlesParams | None = None,
    n_steps: int = 200,
    total_hours: float = 500.0,
    rct_multiplier_at_failure: float = RCT_FAILURE_MULTIPLIER,
    cdl_drop_fraction: float = 0.6,
) -> DegradationScenario:
    """
    Grow an IrO2 passivation layer over time.

    Rct grows linearly (oxide film resistance adds in series with charge-transfer
    step; at the cell level this looks like a rising Rct in the equivalent circuit).

    Cdl decays to (1 - cdl_drop_fraction) of baseline as the oxide thickens and
    the effective permittivity of the interface falls.

    Rs and sigma are assumed unaffected by surface oxidation.

    The growth rate is chosen so that Rct reaches rct_multiplier_at_failure × Rct0
    at total_hours.
    """
    if baseline is None:
        baseline = moe_anode_baseline()

    hours = np.linspace(0.0, total_hours, n_steps)
    t_norm = hours / total_hours  # 0 → 1

    rct_end = baseline.Rct * rct_multiplier_at_failure
    rct_vals = baseline.Rct + (rct_end - baseline.Rct) * t_norm

    cdl_end = baseline.Cdl * (1.0 - cdl_drop_fraction)
    cdl_vals = baseline.Cdl - (baseline.Cdl - cdl_end) * t_norm

    params = [
        baseline.copy(Rct=rct, Cdl=cdl)
        for rct, cdl in zip(rct_vals, cdl_vals)
    ]

    failure_hour = float(total_hours)
    return DegradationScenario(
        name="oxidation",
        hours=hours,
        params=params,
        failure_hour=failure_hour,
    )


# ── Mode 2: Evaporation ───────────────────────────────────────────────────────

def evaporation_trajectory(
    baseline: RandlesParams | None = None,
    n_steps: int = 200,
    total_hours: float = 300.0,
    area_decay_constant: float | None = None,
    sigma_growth_factor: float = 2.5,
) -> DegradationScenario:
    """
    Simulate IrO3 sublimation removing electrode mass.

    Active area decays exponentially: A(t) = A0 * exp(-k * t).
    The decay constant k is chosen so that A(total_hours) = AREA_FAILURE_FRACTION * A0.

    Rct ∝ 1/A  (Butler-Volmer: exchange current density scales with area)
    Cdl ∝ A    (double-layer capacitance is proportional to true surface area)
    sigma ∝ 1/√A  (Warburg prefactor rises as the diffusion-accessible area shrinks)
    Rs is unaffected by electrode area.
    """
    if baseline is None:
        baseline = moe_anode_baseline()

    if area_decay_constant is None:
        # k such that exp(-k * total_hours) = AREA_FAILURE_FRACTION
        area_decay_constant = -np.log(AREA_FAILURE_FRACTION) / total_hours

    hours = np.linspace(0.0, total_hours, n_steps)
    area_ratio = np.exp(-area_decay_constant * hours)  # A(t)/A0

    rct_vals = baseline.Rct / area_ratio
    cdl_vals = baseline.Cdl * area_ratio
    sigma_vals = baseline.sigma / np.sqrt(area_ratio) * (1.0 + (sigma_growth_factor - 1.0) * (1 - area_ratio))

    params = [
        baseline.copy(Rct=rct, Cdl=cdl, sigma=sig)
        for rct, cdl, sig in zip(rct_vals, cdl_vals, sigma_vals)
    ]

    failure_idx = np.searchsorted(1.0 / area_ratio, RCT_FAILURE_MULTIPLIER)
    failure_hour = float(hours[failure_idx]) if failure_idx < n_steps else float(total_hours)

    return DegradationScenario(
        name="evaporation",
        hours=hours,
        params=params,
        failure_hour=failure_hour,
    )


# ── Combined mode ─────────────────────────────────────────────────────────────

def combined_trajectory(
    baseline: RandlesParams | None = None,
    n_steps: int = 200,
    total_hours: float = 400.0,
    ox_weight: float = 0.5,
    evap_weight: float = 0.5,
) -> DegradationScenario:
    """
    Superpose oxidation and evaporation effects with configurable weights.

    The two mechanisms compete: oxidation dominates at lower operating temperatures
    (film growth kinetics); evaporation dominates at higher temperatures.
    ox_weight + evap_weight need not sum to 1 — they are multiplicative amplifiers
    applied to the respective parameter deltas.
    """
    if baseline is None:
        baseline = moe_anode_baseline()

    ox = oxidation_trajectory(baseline, n_steps, total_hours)
    ev = evaporation_trajectory(baseline, n_steps, total_hours)

    params = []
    for p_ox, p_ev in zip(ox.params, ev.params):
        delta_rct = ox_weight * (p_ox.Rct - baseline.Rct) + evap_weight * (p_ev.Rct - baseline.Rct)
        delta_cdl = ox_weight * (p_ox.Cdl - baseline.Cdl) + evap_weight * (p_ev.Cdl - baseline.Cdl)
        delta_sigma = evap_weight * (p_ev.sigma - baseline.sigma)
        params.append(baseline.copy(
            Rct=baseline.Rct + delta_rct,
            Cdl=max(1e-6, baseline.Cdl + delta_cdl),
            sigma=max(0.1, baseline.sigma + delta_sigma),
        ))

    failure_hour = min(
        h for h, p in zip(ox.hours, params)
        if p.Rct >= baseline.Rct * RCT_FAILURE_MULTIPLIER
    ) if any(p.Rct >= baseline.Rct * RCT_FAILURE_MULTIPLIER for p in params) else float(total_hours)

    return DegradationScenario(
        name="combined",
        hours=ox.hours,
        params=params,
        failure_hour=failure_hour,
    )


# ── Healthy baseline (for labelling) ─────────────────────────────────────────

def healthy_trajectory(
    baseline: RandlesParams | None = None,
    n_steps: int = 50,
    total_hours: float = 100.0,
    jitter_std: float = 0.02,
    rng: np.random.Generator | None = None,
) -> DegradationScenario:
    """
    A stationary healthy electrode with small random parameter jitter.
    Used to generate negative (non-degraded) examples for the detector.
    """
    if baseline is None:
        baseline = moe_anode_baseline()
    if rng is None:
        rng = np.random.default_rng(0)

    hours = np.linspace(0.0, total_hours, n_steps)
    params = [
        baseline.copy(
            Rct=baseline.Rct * (1.0 + rng.normal(0, jitter_std)),
            Cdl=baseline.Cdl * (1.0 + rng.normal(0, jitter_std)),
        )
        for _ in hours
    ]
    return DegradationScenario(
        name="healthy",
        hours=hours,
        params=params,
        failure_hour=None,
    )
