import numpy as np
from dataclasses import dataclass, field


@dataclass
class PatientSignal:
    patient_id: int
    label: int          # 0 = normal, 1 = abnormal
    ecg: np.ndarray = field(repr=False)
    sbp: np.ndarray = field(repr=False)  # systolic BP
    dbp: np.ndarray = field(repr=False)  # diastolic BP
    temp: np.ndarray = field(repr=False)
    eeg: np.ndarray = field(repr=False)
    spo2: np.ndarray = field(repr=False)


def _ecg_synthetic(t, heart_rate_factor=1.0, noise=0.1, rng=None):
    if rng is None:
        rng = np.random.RandomState()
    cycle = (t * heart_rate_factor) % (2 * np.pi)
    # P-wave + QRS complex + T-wave
    p_wave  = 0.10 * np.exp(-((cycle - 0.4) ** 2) / 0.012)
    r_peak  = 1.00 * np.exp(-((cycle - 1.05) ** 2) / 0.002)
    s_wave  = -0.30 * np.exp(-((cycle - 1.18) ** 2) / 0.004)
    t_wave  = 0.35 * np.exp(-((cycle - 1.60) ** 2) / 0.025)
    return p_wave + r_peak + s_wave + t_wave + rng.normal(0, noise, len(t))


def generate_biosignals(n_patients: int = 80, n_timesteps: int = 200, seed: int = 42) -> list:
    rng = np.random.RandomState(seed)
    t = np.linspace(0, 4 * np.pi, n_timesteps)
    patients = []

    for i in range(n_patients):
        label = int(rng.random() > 0.62)       # ~38 % abnormal
        nf = 1.0 + label * 1.8                 # noise amplification for abnormal

        # ECG — tachycardia pattern in abnormal
        hr_factor = 1.0 + label * 0.45 + rng.normal(0, 0.05)
        ecg = _ecg_synthetic(t, hr_factor, noise=0.08 * nf, rng=rng)

        # Blood pressure
        sbp_mu = 118 + label * 38 + rng.normal(0, 8)
        dbp_mu = 78 + label * 22 + rng.normal(0, 5)
        sbp = sbp_mu + rng.normal(0, 4 * nf, n_timesteps)
        dbp = dbp_mu + rng.normal(0, 3 * nf, n_timesteps)

        # Temperature — fever in abnormal
        temp_mu = 36.8 + label * 1.9 + rng.normal(0, 0.15)
        temp = temp_mu + rng.normal(0, 0.12 * nf, n_timesteps)

        # EEG — reduced alpha, elevated beta in abnormal
        alpha = np.sin(10 * t) * (1.0 - 0.45 * label)
        beta  = np.sin(25 * t) * (1.0 + 0.65 * label)
        theta = np.sin(5 * t)  * (1.0 + 0.20 * label)
        eeg = alpha + beta + theta + rng.normal(0, 0.25 * nf, n_timesteps)

        # SpO2 — hypoxia in abnormal
        spo2_mu = 98.4 - label * 7.5 + rng.normal(0, 0.5)
        spo2 = np.clip(spo2_mu + rng.normal(0, 0.7 * nf, n_timesteps), 55, 100)

        patients.append(PatientSignal(
            patient_id=i, label=label,
            ecg=ecg, sbp=sbp, dbp=dbp,
            temp=temp, eeg=eeg, spo2=spo2,
        ))

    return patients


# ── Feature extraction ────────────────────────────────────────────────────────
SENSORS = ['ECG', 'SBP', 'DBP', 'Temp', 'EEG', 'SpO2']
STATS   = ['mean', 'std', 'min', 'max', 'median', 'iqr']

FEATURE_NAMES = [f'{s}_{st}' for s in SENSORS for st in STATS]  # 36 features


def _signal_stats(sig: np.ndarray) -> list:
    return [
        float(np.mean(sig)),
        float(np.std(sig)),
        float(np.min(sig)),
        float(np.max(sig)),
        float(np.median(sig)),
        float(np.percentile(sig, 75) - np.percentile(sig, 25)),
    ]


def extract_features(patient: PatientSignal) -> np.ndarray:
    feats = []
    for sig in [patient.ecg, patient.sbp, patient.dbp, patient.temp, patient.eeg, patient.spo2]:
        feats.extend(_signal_stats(sig))
    return np.array(feats, dtype=np.float64)


def build_dataset(patients: list):
    X = np.array([extract_features(p) for p in patients])
    y = np.array([p.label for p in patients])
    return X, y
