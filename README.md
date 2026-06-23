# Electrochemical Impedance Spectroscopy — MRE Electrode Health Monitoring

Simulation pipeline for detecting iridium-anode degradation in Molten Regolith Electrolysis (MRE) and Molten Oxide Electrolysis (MOE) reactors via Electrochemical Impedance Spectroscopy. This is the first published technical artifact from the autonomous MOE/MRE control project.

## The problem

MOE runs at ~1600°C with iridium anodes that degrade through two competing mechanisms: IrO2 passivation (oxidation) and IrO3 sublimation (evaporation). Both raise charge-transfer resistance and ultimately cause failure. Today, operators have no early warning — they find out when the cell dies. The question this repo addresses: can impedance spectra, measured periodically, give a reliable alert hours before failure?

This repo answers that on synthetic data. It does not yet answer it on real reactor data.

## Repository contents

```
eis-simulation/
├── randles_model.py               Randles equivalent-circuit model for an Ir anode in molten
│                                  iron-oxide at ~1600°C. Parameters: Rs, Rct, Cdl, sigma
│                                  (Warburg). Baseline from Sadoway 2012, Allanore 2013, Sirk 2010.
├── degradation_sim.py             Two parametric degradation modes: oxidation (IrO2 passivation,
│                                  ~500 h to failure) and evaporation (IrO3 sublimation, ~300 h).
│                                  Also combined mode and healthy baseline.
├── detector.py                    Pipeline: fit Randles circuit → extract Rct → CUSUM change-point
│                                  detection → alert before failure. Reports TPR, FPR, lead hours.
└── notebooks/
    ├── 01-randles-baseline.ipynb          Nyquist + Bode plots, parameter sensitivity sweeps.
    ├── 02-degradation-trajectories.ipynb  Spectrum evolution under degradation, normalised Rct
    │                                      as health indicator.
    └── 03-detector-evaluation.ipynb       End-to-end evaluation: 120 degraded + 30 healthy
                                           scenarios, ROC-like curve, lead time vs threshold,
                                           CUSUM example trace.
```

## Falsifiable claims

### Synthetic data — notebook 03

| Metric | Value |
|--------|-------|
| Dataset | 120 degraded (60 oxidation + 60 evaporation) + 30 healthy |
| Noise model | Additive complex Gaussian, SNR = 40 dB |
| TPR | 100% |
| FPR | 0% |
| Median lead time | 211 h before Rct failure threshold |

**Verdict:** these numbers confirm the pipeline runs end-to-end. They are not scientifically meaningful — the detector is matched to the data generator. A detector tested on data it generated itself will always perform perfectly.

---

### Real measured data — notebook 04

| Metric | Value |
|--------|-------|
| Dataset | NASA Battery B0005 — 278 EIS measurements over battery life |
| Source | Saha & Goebel, NASA Prognostics Center, 2007 |
| Rct rise over lifetime | 38% (subtle signal vs. 5× assumed for MOE) |
| CUSUM threshold | H = 3.0 |
| Detection lead time | 28 charge cycles before end-of-life |
| At threshold H ≥ 5.0 | Detector fires after EOL — no useful warning |

**Verdict:** this is the meaningful result. On real measured EIS data the detector fires before failure, but the signal is subtle and threshold tuning is non-trivial. The sensitivity/lead-time tradeoff is real.

## What this proves / what this does not prove

This proves that a CUSUM detector operating on Randles-fit Rct can, in principle, give reliable early warning of degradation under a parametric noise model. The degradation trajectories are physically motivated (literature parameters, realistic time constants), but they are not real reactor data.

This does not prove: that the parametric model captures all real degradation paths; that SNR = 40 dB is achievable in practice at 1600°C; that the detector generalises to degradation modes not in the training set; or that the lead-time margin survives thermal and chemical variability in a real cell.

The next validation step requires measured impedance time-series from an operating MOE cell, which is a data partnership problem.

## Installation and running

```bash
git clone https://github.com/tocki28/electrochemical-impedance-spectroscopy-mre.git
cd electrochemical-impedance-spectroscopy-mre
pip install -e ".[notebooks]"
jupyter lab
```

Run notebooks in order: 01 → 02 → 03. Each notebook is self-contained but 03 imports `detector.py` and uses degradation trajectories from `degradation_sim.py`.

Python 3.10+ recommended. Core dependencies: `impedance`, `numpy`, `scipy`, `matplotlib`.

## What comes next

CUSUM is the baseline detector — simple, interpretable, runs on any hardware. It is not the final answer.

The next iteration will compare CUSUM against three lightweight alternatives, all suitable for embedded hardware in a harsh environment:

- **EWMA** (Exponentially Weighted Moving Average) — smoother response to transient noise
- **Kalman filter on Rct** — optimal estimator that gives a predicted time-to-failure with uncertainty bounds, not just a binary alarm
- **Multi-feature Mahalanobis distance** — monitors all four Randles parameters jointly ([Rs, Rct, Cdl, sigma]), exploiting the fact that oxidation and evaporation leave different fingerprints across the full parameter set

Neural networks are explicitly excluded: the target deployment is an autonomous controller on constrained embedded hardware, possibly lunar. Interpretability and compute efficiency are constraints, not preferences.

Real MOE/MRE electrode failure data is also on the roadmap. The current real-data validation uses NASA battery EIS data as a proxy. The next step is measured impedance time-series from an operating MOE cell via a data partnership.

## Do you have real MOE or MRE impedance data?

If you are running MOE or MRE experiments and have EIS measurements taken over electrode lifetime — even partial data, even from a single cell — I would like to hear from you.

What would be useful:
- Impedance spectra (Re(Z), Im(Z) vs frequency) taken at intervals over electrode lifetime
- Any record of when the electrode was replaced or when performance dropped
- Operating conditions if available (current density, temperature, bath composition)

The goal is to validate this detection approach on real reactor data and improve the algorithm together. If the method works on your data, you get a better tool for predicting electrode end-of-life. If it doesn't, we learn something useful about where the model breaks down.

Get in touch: open an issue on this repo or reach out on X — [@Tocki28](https://x.com/Tocki28)

## Connection to the broader project

This repo is subproblem P1 of a larger project: building an autonomous brain for MOE process control. The full system needs to make, in real time, the judgment calls that a human operator currently makes — electrode swap timing, current-density adjustments, fault isolation. P1 (electrode health via EIS) is the narrowest, most tractable subproblem with a clear falsifiable structure. The approach here — fit a physical model, track a derived parameter, apply a classical change-point test — is the template for how the broader system handles any sensor modality: parametric model first, black-box only if the parametric model fails.
