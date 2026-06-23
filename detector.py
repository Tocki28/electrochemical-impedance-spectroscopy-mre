"""
Degradation detector for EIS spectra of a molten-oxide electrolysis anode.

Pipeline
--------
1. fit_spectrum()   — fit a Randles model to one measured spectrum, returning
                      the equivalent-circuit parameters (Rs, Rct, Cdl, sigma).
2. extract_features() — given a time-series of fitted params, return a
                       1-D feature vector per time step (currently just Rct,
                       but easily extended).
3. cusum_detector() — run CUSUM change-point detection on the Rct series.
                      Returns the alert index (first sample where CUSUM
                      statistic exceeds the threshold) and the full statistic.
4. evaluate()       — given a labelled set of scenarios, compute detection
                      lead-time (hours before failure) and false-positive rate.

The detector is intentionally simple for Month 2: one feature (Rct), one
algorithm (CUSUM).  The goal is a falsifiable claim, not a production model.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import least_squares
from dataclasses import dataclass

from randles_model import RandlesParams, randles_impedance, moe_frequencies
from degradation_sim import DegradationScenario


# ── Spectrum fitting ──────────────────────────────────────────────────────────

_PARAM_BOUNDS = (
    [0.0, 0.0, 1e-9, 0.0],          # lower: Rs, Rct, Cdl, sigma
    [100.0, 5000.0, 1e-1, 500.0],   # upper
)


def fit_spectrum(
    Z_measured: np.ndarray,
    frequencies: np.ndarray,
    initial_guess: RandlesParams | None = None,
) -> RandlesParams:
    """
    Fit a Randles circuit to one complex impedance spectrum.

    Uses non-linear least squares on the combined real+imag residual,
    weighted by 1/|Z| so high-frequency and low-frequency points contribute
    equally (otherwise the Warburg tail dominates numerically).

    Returns best-fit RandlesParams.  Raises RuntimeError if optimisation fails.
    """
    if initial_guess is None:
        from randles_model import moe_anode_baseline
        initial_guess = moe_anode_baseline()

    x0 = [initial_guess.Rs, initial_guess.Rct, initial_guess.Cdl, initial_guess.sigma]

    def residuals(x):
        p = RandlesParams(*x)
        Z_model = randles_impedance(p, frequencies)
        weights = 1.0 / (np.abs(Z_measured) + 1e-12)
        r_real = (np.real(Z_model) - np.real(Z_measured)) * weights
        r_imag = (np.imag(Z_model) - np.imag(Z_measured)) * weights
        return np.concatenate([r_real, r_imag])

    result = least_squares(residuals, x0, bounds=_PARAM_BOUNDS, method="trf", max_nfev=2000)
    if not result.success and result.cost > 1.0:
        raise RuntimeError(f"Spectrum fit did not converge: cost={result.cost:.4f}")

    return RandlesParams(*result.x)


def fit_scenario(
    scenario: DegradationScenario,
    frequencies: np.ndarray | None = None,
    snr_db: float | None = None,
    rng: np.random.Generator | None = None,
) -> list[RandlesParams]:
    """
    Simulate and fit spectra for every time step of a scenario.

    If snr_db is given, noise is added before fitting (end-to-end pipeline test).
    Returns a list of fitted RandlesParams, one per time step.
    """
    if frequencies is None:
        frequencies = moe_frequencies()

    spectra = scenario.spectra(frequencies=frequencies, snr_db=snr_db, rng=rng)
    fitted = []
    prev = scenario.params[0]
    for Z in spectra:
        try:
            p = fit_spectrum(Z, frequencies, initial_guess=prev)
            fitted.append(p)
            prev = p
        except RuntimeError:
            fitted.append(prev)  # carry forward on fit failure

    return fitted


# ── Feature extraction ────────────────────────────────────────────────────────

def extract_rct(fitted_params: list[RandlesParams]) -> np.ndarray:
    """Extract Rct time series from a sequence of fitted params."""
    return np.array([p.Rct for p in fitted_params])


# ── CUSUM change-point detector ───────────────────────────────────────────────

@dataclass
class CusumResult:
    alert_index: int | None     # index where CUSUM first exceeds threshold; None if no alert
    alert_hour: float | None    # corresponding time in hours
    statistic: np.ndarray       # full CUSUM statistic series
    lead_hours: float | None    # hours of warning before failure_hour (None if healthy or no alert)


def cusum_detector(
    rct_series: np.ndarray,
    hours: np.ndarray,
    baseline_rct: float,
    threshold: float = 10.0,
    drift: float | None = None,
    failure_hour: float | None = None,
) -> CusumResult:
    """
    Upper-sided CUSUM on normalised Rct to detect rising drift.

    The test statistic:
        S[0] = 0
        S[n] = max(0, S[n-1] + (x[n] - mu0 - k))

    where x[n] = Rct[n] / baseline_rct  (normalised, so x ≈ 1 when healthy)
          mu0  = 1.0 (expected normalised Rct under H0)
          k    = drift  (allowable drift before alarm; default 0.05, i.e. 5%)
          threshold = H in standard CUSUM notation

    Alert fires when S[n] > threshold.

    Parameters
    ----------
    rct_series   : 1-D array of fitted Rct values
    hours        : corresponding time array (same length)
    baseline_rct : healthy Rct (= params at t=0 before degradation)
    threshold    : CUSUM decision threshold H (in units of normalised Rct)
    drift        : allowable slack k; defaults to 2 × measurement noise (0.05)
    failure_hour : if known, compute lead time as failure_hour - alert_hour
    """
    if drift is None:
        drift = 0.05  # 5% drift per sample before we care

    x = rct_series / baseline_rct
    mu0 = 1.0
    S = np.zeros(len(x))
    for n in range(1, len(x)):
        S[n] = max(0.0, S[n - 1] + (x[n] - mu0 - drift))

    alert_idx = next((i for i, s in enumerate(S) if s > threshold), None)
    alert_hour = float(hours[alert_idx]) if alert_idx is not None else None

    lead_hours = None
    if alert_hour is not None and failure_hour is not None:
        lead_hours = max(0.0, failure_hour - alert_hour)

    return CusumResult(
        alert_index=alert_idx,
        alert_hour=alert_hour,
        statistic=S,
        lead_hours=lead_hours,
    )


# ── Evaluation ────────────────────────────────────────────────────────────────

@dataclass
class DetectorMetrics:
    n_degraded: int
    n_healthy: int
    true_positive_rate: float       # fraction of degraded scenarios detected
    false_positive_rate: float      # fraction of healthy scenarios falsely alarmed
    median_lead_hours: float | None
    min_lead_hours: float | None


def evaluate(
    scenarios: list[DegradationScenario],
    frequencies: np.ndarray | None = None,
    snr_db: float | None = 40.0,
    cusum_threshold: float = 10.0,
    cusum_drift: float = 0.05,
    rng: np.random.Generator | None = None,
) -> DetectorMetrics:
    """
    Run the full fit → detect pipeline on a list of scenarios.

    Degraded scenarios are those with failure_hour not None.
    Healthy scenarios have failure_hour == None.

    Returns DetectorMetrics with TPR, FPR, and lead-time statistics.
    """
    if frequencies is None:
        frequencies = moe_frequencies()
    if rng is None:
        rng = np.random.default_rng(42)

    leads = []
    false_positives = 0
    true_positives = 0
    n_degraded = sum(1 for s in scenarios if s.failure_hour is not None)
    n_healthy = len(scenarios) - n_degraded

    for scenario in scenarios:
        baseline_rct = scenario.params[0].Rct
        fitted = fit_scenario(scenario, frequencies=frequencies, snr_db=snr_db, rng=rng)
        rct = extract_rct(fitted)
        result = cusum_detector(
            rct,
            scenario.hours,
            baseline_rct=baseline_rct,
            threshold=cusum_threshold,
            drift=cusum_drift,
            failure_hour=scenario.failure_hour,
        )

        if scenario.failure_hour is not None:
            if result.alert_index is not None:
                true_positives += 1
                leads.append(result.lead_hours or 0.0)
        else:
            if result.alert_index is not None:
                false_positives += 1

    return DetectorMetrics(
        n_degraded=n_degraded,
        n_healthy=n_healthy,
        true_positive_rate=true_positives / n_degraded if n_degraded > 0 else float("nan"),
        false_positive_rate=false_positives / n_healthy if n_healthy > 0 else float("nan"),
        median_lead_hours=float(np.median(leads)) if leads else None,
        min_lead_hours=float(np.min(leads)) if leads else None,
    )
