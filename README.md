# Electrochemical Impedance Spectroscopy - MRE Electrode Health Monitoring

Simulation pipeline for detecting iridium-anode degradation in Molten Regolith Electrolysis (MRE) and Molten Oxide Electrolysis (MOE) reactors via Electrochemical Impedance Spectroscopy. This is the first published technical artifact from the autonomous MOE/MRE control project.

## The problem

MOE runs at ~1600°C with iridium anodes that degrade through two competing mechanisms: IrO2 passivation (oxidation) and IrO3 sublimation (evaporation). Both raise charge-transfer resistance and ultimately cause failure. Today, operators have no early warning - they find out when the cell dies. The question this repo addresses: can impedance spectra, measured periodically, give a reliable alert hours before failure?

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
    ├── 03-detector-evaluation.ipynb       End-to-end evaluation: 120 degraded + 30 healthy
    │                                      scenarios, ROC-like curve, lead time vs threshold,
    │                                      CUSUM example trace.
    ├── 04-real-data-nasa-battery.ipynb    Validation on real measured EIS data (NASA Battery
    │                                      B0005, 278 impedance measurements). CUSUM fires
    │                                      28 cycles before end-of-life at threshold H=3.0.
    └── 05-your-own-data.ipynb             Run the detector on your own EIS data. Two input
                                           formats: full spectra CSVs (fits Randles model) or
                                           pre-fitted Rct time series. Includes threshold
                                           sensitivity table for parameter tuning.
```

## Falsifiable claims

### Synthetic data - notebook 03

| Metric | Value |
|--------|-------|
| Dataset | 120 degraded (60 oxidation + 60 evaporation) + 30 healthy |
| Noise model | Additive complex Gaussian, SNR = 40 dB |
| TPR | 100% |
| FPR | 0% |
| Median lead time | 211 h before Rct failure threshold |

**Verdict:** these numbers confirm the pipeline runs end-to-end. They are not scientifically meaningful - the detector is matched to the data generator. A detector tested on data it generated itself will always perform perfectly.

---

### Real measured data - notebook 04

| Metric | Value |
|--------|-------|
| Dataset | NASA Battery B0005 - 278 EIS measurements over battery life |
| Source | Saha & Goebel, NASA Prognostics Center, 2007 |
| Rct rise over lifetime | 38% (subtle signal vs. 5× assumed for MOE) |
| CUSUM threshold | H = 3.0 |
| Detection lead time | 28 charge cycles before end-of-life |
| At threshold H ≥ 5.0 | Detector fires after EOL - no useful warning |

**Verdict:** this is the meaningful result. On real measured EIS data the detector fires before failure, but the signal is subtle and threshold tuning is non-trivial. The sensitivity/lead-time tradeoff is real.

## What this proves / what this does not prove

This proves that a CUSUM detector operating on Randles-fit Rct can, in principle, give reliable early warning of degradation under a parametric noise model. The degradation trajectories are physically motivated (literature parameters, realistic time constants), but they are not real reactor data.

This does not prove: that the parametric model captures all real degradation paths; that SNR = 40 dB is achievable in practice at 1600°C; that the detector generalises to degradation modes not in the training set; or that the lead-time margin survives thermal and chemical variability in a real cell.

The next validation step requires measured impedance time-series from an operating MOE cell, which is a data partnership problem.

## Installation and running

No programming experience required. Follow the steps for your operating system below. Each step tells you what to type and what to expect.

---

### macOS

**Step 1 - Open Terminal.**
Press `Cmd + Space`, type `Terminal`, and press Enter. A black or white window with a blinking cursor will open. This is where you type commands.

**Step 2 - Check your Python version.**
Type the following and press Enter:
```
python3 --version
```
You need version **3.10 or higher**. macOS ships with Python 3.9 by default, which is too old. If your version is below 3.10, go to [python.org/downloads](https://www.python.org/downloads/), download the latest installer (e.g. Python 3.12), and run it. Then open a new Terminal window and check the version again before continuing.

**Step 3 - Update pip.**
This ensures the installer itself is up to date:
```
python3 -m pip install --upgrade pip
```

**Step 4 - Download this repository.**
Type the following and press Enter (this copies all the code to your computer):
```
git clone https://github.com/tocki28/electrochemical-impedance-spectroscopy-mre.git
```
If you get "git: command not found", install Git from [git-scm.com](https://git-scm.com/download/mac) and repeat.

**Step 5 - Navigate into the folder.**
```
cd electrochemical-impedance-spectroscopy-mre
```

**Step 6 - Install the required libraries.**
```
python3 -m pip install -r requirements.txt
```
This will download and install everything needed. It may take 1–2 minutes. You will see a lot of text scrolling - that is normal.

**Step 7 - Open the notebooks.**
```
jupyter lab
```
Your browser will open automatically with the Jupyter interface. Click on the `notebooks/` folder and open notebook `01-randles-baseline.ipynb` to start.

---

### Windows

**Step 1 - Install Anaconda.**
Anaconda is a free Python distribution that includes everything you need. Download it from [anaconda.com/download](https://www.anaconda.com/download) and run the installer. Accept all default options.

**Step 2 - Open Anaconda Prompt.**
Click the Start menu, search for `Anaconda Prompt`, and open it. A black window will appear. This is where you type commands.

**Step 3 - Install Git (if not already installed).**
Type the following and press Enter:
```
conda install git -y
```

**Step 4 - Download this repository.**
```
git clone https://github.com/tocki28/electrochemical-impedance-spectroscopy-mre.git
```

**Step 5 - Navigate into the folder.**
```
cd electrochemical-impedance-spectroscopy-mre
```

**Step 6 - Install the required libraries.**
```
python3 -m pip install -r requirements.txt
```
This may take 1-2 minutes. Text will scroll - that is normal.

**Step 7 - Open the notebooks.**
```
jupyter lab
```
Your browser will open automatically with the Jupyter interface. Click on the `notebooks/` folder and open notebook `01-randles-baseline.ipynb` to start.

---

### Linux

**Step 1 - Open a terminal.**
On Ubuntu: press `Ctrl + Alt + T`. On other distributions, look for "Terminal" in your application menu.

**Step 2 - Check that Python and pip are installed.**
```
python3 --version
pip3 --version
```
If pip is missing, install it:
- Ubuntu/Debian: `sudo apt install python3-pip`
- Fedora: `sudo dnf install python3-pip`

**Step 3 - Download this repository.**
```
git clone https://github.com/tocki28/electrochemical-impedance-spectroscopy-mre.git
```

**Step 4 - Navigate into the folder.**
```
cd electrochemical-impedance-spectroscopy-mre
```

**Step 5 - Install the required libraries.**
```
python3 -m pip install -r requirements.txt
```
This may take 1-2 minutes. Text will scroll - that is normal.

**Step 6 - Open the notebooks.**
```
jupyter lab
```
Your browser will open automatically. Click on the `notebooks/` folder and open notebook `01-randles-baseline.ipynb` to start.

---

### How to use the notebooks

A Jupyter notebook is a document that contains code and text side by side. You run it one block at a time. Each block is called a cell. To run a cell, click on it and press `Shift + Enter`. The result appears immediately below. You do not need to understand the code to use the notebooks - just run each cell in order from top to bottom.

When you open Jupyter Lab in your browser, you will see a file browser on the left. Click on the `notebooks/` folder, then open the notebooks in this order:

**Notebook 01 - Randles baseline**
This is the starting point. It shows you what the equivalent circuit of an iridium anode looks like in impedance space - the Nyquist plot (a semicircle) and the Bode plot (magnitude and phase vs frequency). Run it to confirm everything is installed correctly and to see what a healthy electrode looks like.

**Notebook 02 - Degradation trajectories**
This shows how the impedance spectrum changes as the electrode degrades over time - both through oxidation (IrO2 passivation) and evaporation (IrO3 sublimation). You will see the semicircle growing as charge-transfer resistance rises. This is the signal the detector is trained to catch.

**Notebook 03 - Detector evaluation**
This runs the full detection pipeline on 150 simulated scenarios (120 degraded electrodes, 30 healthy ones) and reports how well it performs: true positive rate, false positive rate, and how many hours before failure the alert fires. Note: these results are on synthetic data generated by the same model, so they are optimistic by design.

**Notebook 04 - Real data validation (NASA battery dataset)**
This is the most meaningful result. It runs the same detector on real measured EIS data from NASA's battery aging dataset - 278 impedance measurements taken on a lithium-ion cell as it was cycled to end-of-life. The detector fires 28 cycles before the battery crosses the end-of-life threshold. To run this notebook you need to download the NASA dataset first - the notebook contains the exact download link and instructions at the top.

**Notebook 05 - Your own data**
If you have real EIS measurements from an electrode, this notebook lets you run the detector on your own data. There is a `my_data/` folder inside the `notebooks/` directory - place your files there. To upload files, use the Jupyter Lab file browser on the left: navigate into `notebooks/my_data/`, then click the upload button (upward arrow icon) and select your files. The notebook supports two formats: a folder of CSV files (one per measurement, with columns `frequency_hz`, `re_z_ohm`, `neg_im_z_ohm`) or a single CSV of pre-fitted Rct values over time. Edit the configuration cell at the top if needed, then run the notebook top to bottom. If you get results - whether the detector works or not - please open an issue or reach out on X [@02iTAG](https://x.com/02iTAG).

## What comes next

CUSUM is the baseline detector - simple, interpretable, runs on any hardware. It is not the final answer.

The next iteration will compare CUSUM against three lightweight alternatives, all suitable for embedded hardware in a harsh environment:

- **EWMA** (Exponentially Weighted Moving Average) - smoother response to transient noise
- **Kalman filter on Rct** - optimal estimator that gives a predicted time-to-failure with uncertainty bounds, not just a binary alarm
- **Multi-feature Mahalanobis distance** - monitors all four Randles parameters jointly ([Rs, Rct, Cdl, sigma]), exploiting the fact that oxidation and evaporation leave different fingerprints across the full parameter set

Neural networks are excluded for now. The target deployment is an autonomous controller on constrained embedded hardware, possibly lunar - interpretability and compute efficiency are hard constraints. That said, neuromorphic chips could change this entirely. If you are working on neuromorphic hardware - hey Cyberswarm - running neural-network-like computation at a fraction of the power of conventional processors, this is exactly the kind of application we would love to explore together.

Real MOE/MRE electrode failure data is also on the roadmap. The current real-data validation uses NASA battery EIS data as a proxy. The next step is measured impedance time-series from an operating MOE cell via a data partnership.

## Do you have real MOE or MRE impedance data?

If you are running MOE or MRE experiments and have EIS measurements taken over electrode lifetime - even partial data, even from a single cell - I would like to hear from you.

What would be useful:
- Impedance spectra (Re(Z), Im(Z) vs frequency) taken at intervals over electrode lifetime
- Any record of when the electrode was replaced or when performance dropped
- Operating conditions if available (current density, temperature, bath composition)

The goal is to validate this detection approach on real reactor data and improve the algorithm together. If the method works on your data, you get a better tool for predicting electrode end-of-life. If it doesn't, we learn something useful about where the model breaks down.

Get in touch: open an issue on this repo or reach out on X - [@02iTAG](https://x.com/02iTAG)

## Connection to the broader project

This repo is subproblem P1 of a larger project: building an autonomous brain for MOE process control. The full system needs to make, in real time, the judgment calls that a human operator currently makes - electrode swap timing, current-density adjustments, fault isolation. P1 (electrode health via EIS) is the narrowest, most tractable subproblem with a clear falsifiable structure. The approach here - fit a physical model, track a derived parameter, apply a classical change-point test - is the template for how the broader system handles any sensor modality: parametric model first, black-box only if the parametric model fails.
