"""
Quantum Live Stream Engine — generates rolling patient data with VQC predictions.
Used by the Live Monitor page (auto-refresh).
"""
import sys, json, time, math
import numpy as np
from pathlib import Path
from collections import deque

_QD = Path(__file__).parent.parent / "quantum_diagnostic"
if str(_QD) not in sys.path:
    sys.path.insert(0, str(_QD))

from data_generator import generate_biosignals, build_dataset, extract_features
from quantum_circuits import vqc_predict, vqc_init_weights, N_QUBITS

# ── Paths ──────────────────────────────────────────────────────────────────────
_ACTIVE_ATTACKS = (
    Path(__file__).parent.parent / "iomt_attack_lab" / "generated" / "active_attacks.json"
)
_ATTACK_PLAN = (
    Path(__file__).parent.parent / "iomt_attack_lab" / "generated" / "attack_plan.json"
)

BUFFER_SIZE  = 60
BATCH_SIZE   = 4    # new patients per refresh tick

RISK_LABELS = ["LOW", "MODERATE", "HIGH", "CRITICAL"]
RISK_COLORS = ["#16a34a", "#d97706", "#ea580c", "#dc2626"]
RISK_THRESH = [0.35, 0.55, 0.75, 1.01]


# ── Attack helpers ─────────────────────────────────────────────────────────────
def load_active_attacks() -> dict:
    try:
        if _ACTIVE_ATTACKS.exists():
            data = json.loads(_ACTIVE_ATTACKS.read_text())
            active = data.get("active", [])
            if isinstance(active, list):
                return {k: 0.7 for k in active}
            if isinstance(active, dict):
                return active
    except Exception:
        pass
    return {}


def load_attack_plan() -> dict:
    try:
        if _ATTACK_PLAN.exists():
            return json.loads(_ATTACK_PLAN.read_text())
    except Exception:
        pass
    return {}


def _attack_noise(active: dict) -> tuple[float, float]:
    """Returns (noise_scale, flip_prob) based on active attacks."""
    if not active:
        return 0.0, 0.0
    total = sum(float(v) for v in active.values())
    noise = min(total * 0.18, 0.55)
    flip  = min(total * 0.08, 0.30)
    return noise, flip


# ── Risk mapping ───────────────────────────────────────────────────────────────
def confidence_to_risk(conf: float) -> tuple[int, str, str]:
    for i, t in enumerate(RISK_THRESH):
        if conf <= t:
            return i, RISK_LABELS[i], RISK_COLORS[i]
    return 3, RISK_LABELS[3], RISK_COLORS[3]


# ── Stream buffer ──────────────────────────────────────────────────────────────
class PatientStreamBuffer:
    """Rolling deque of live VQC diagnostic results."""

    def __init__(self, seed: int = 42):
        self.weights = vqc_init_weights(seed=seed)
        self._pid    = 0
        self._seed   = seed
        self.buffer  = deque(maxlen=BUFFER_SIZE)
        self.totals  = dict(patients=0, abnormal=0, critical=0, attacked=0, correct=0)
        self._history_conf: deque = deque(maxlen=200)  # rolling confidence trace

    # ── Generate ───────────────────────────────────────────────────────────────
    def tick(self, n: int = BATCH_SIZE) -> list[dict]:
        patients = generate_biosignals(n_patients=n, seed=self._seed)
        self._seed += 1

        active   = load_active_attacks()
        noise_sc, flip_p = _attack_noise(active)
        under_attack = bool(active)
        attack_types = list(active.keys())

        X, y = build_dataset(patients)
        mu  = X.mean(axis=0); sigma = X.std(axis=0) + 1e-9
        X_n = (X - mu) / sigma

        batch = []
        for i, (p, xn, label) in enumerate(zip(patients, X_n, y)):
            feat = xn.copy()
            if noise_sc > 0:
                feat += np.random.normal(0, noise_sc, feat.shape)

            conf = float(vqc_predict(feat, self.weights))
            if flip_p > 0 and np.random.random() < flip_p:
                conf = 1.0 - conf
            conf = float(np.clip(conf, 0.0, 1.0))

            risk_i, risk_lbl, risk_col = confidence_to_risk(conf)
            pred = int(conf > 0.5)

            hr   = round(float(np.mean(np.abs(p.ecg))) * 120 + 60 + label * 18, 1)
            hr   = float(np.clip(hr, 40, 180))

            rec = dict(
                patient_id   = self._pid + i,
                label        = int(label),
                prediction   = pred,
                confidence   = round(conf, 4),
                correct      = int(pred == int(label)),
                risk_level   = risk_lbl,
                risk_color   = risk_col,
                risk_idx     = risk_i,
                timestamp    = time.time(),
                hr           = hr,
                sbp          = round(float(np.mean(p.sbp)), 1),
                dbp          = round(float(np.mean(p.dbp)), 1),
                temp         = round(float(np.mean(p.temp)), 2),
                spo2         = round(float(np.clip(np.mean(p.spo2), 55, 100)), 1),
                under_attack = under_attack,
                attack_types = attack_types,
            )
            batch.append(rec)
            self._history_conf.append(conf)

            self.totals["patients"] += 1
            self.totals["abnormal"] += int(label)
            self.totals["critical"] += int(risk_i >= 2)
            self.totals["attacked"] += int(under_attack)
            self.totals["correct"]  += rec["correct"]

        self._pid  += n
        self.buffer.extend(batch)
        return batch

    # ── Accessors ──────────────────────────────────────────────────────────────
    def all(self) -> list[dict]:
        return list(self.buffer)

    def recent(self, n: int = 15) -> list[dict]:
        return list(self.buffer)[-n:]

    def accuracy(self) -> float:
        t = self.totals["patients"]
        return self.totals["correct"] / t if t else 0.0

    def risk_counts(self) -> dict:
        buf = self.all()
        return {lbl: sum(1 for r in buf if r["risk_level"] == lbl) for lbl in RISK_LABELS}

    def confidence_trace(self) -> list[float]:
        return list(self._history_conf)

    def vitals_series(self, field: str, n: int = 40) -> list[float]:
        return [r[field] for r in self.all()[-n:]]


# ── One-shot evaluation (for Evaluation page) ─────────────────────────────────
def run_evaluation(n_patients: int = 80, seed: int = 42) -> dict:
    """Run a mini-evaluation and return metrics dict."""
    patients = generate_biosignals(n_patients=n_patients, seed=seed)
    X, y = build_dataset(patients)
    mu = X.mean(axis=0); sigma = X.std(axis=0) + 1e-9
    X_n = (X - mu) / sigma

    weights = vqc_init_weights(seed=seed)

    confs, preds = [], []
    for xn in X_n:
        c = float(np.clip(vqc_predict(xn, weights), 0, 1))
        confs.append(c)
        preds.append(int(c > 0.5))

    preds = np.array(preds); y = y.astype(int)
    confs = np.array(confs)

    tp = int(np.sum((preds == 1) & (y == 1)))
    tn = int(np.sum((preds == 0) & (y == 0)))
    fp = int(np.sum((preds == 1) & (y == 0)))
    fn = int(np.sum((preds == 0) & (y == 1)))

    acc  = (tp + tn) / len(y) if len(y) else 0
    prec = tp / (tp + fp) if (tp + fp) else 0
    rec  = tp / (tp + fn) if (tp + fn) else 0
    f1   = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
    fpr  = fp / (fp + tn) if (fp + tn) else 0

    # Simple AUC via trapezoidal rule
    thresholds = np.linspace(0, 1, 50)
    roc_tpr, roc_fpr = [], []
    for t in thresholds:
        p = (confs >= t).astype(int)
        _tp = int(np.sum((p == 1) & (y == 1)))
        _fp = int(np.sum((p == 1) & (y == 0)))
        _fn = int(np.sum((p == 0) & (y == 1)))
        _tn = int(np.sum((p == 0) & (y == 0)))
        roc_tpr.append(_tp / (_tp + _fn) if (_tp + _fn) else 0)
        roc_fpr.append(_fp / (_fp + _tn) if (_fp + _tn) else 0)
    auc = float(np.trapz(roc_tpr[::-1], roc_fpr[::-1]))
    auc = max(0.0, min(1.0, abs(auc)))

    return dict(
        acc=round(acc, 4), prec=round(prec, 4), rec=round(rec, 4),
        f1=round(f1, 4), fpr=round(fpr, 4), auc=round(auc, 4),
        tp=tp, tn=tn, fp=fp, fn=fn,
        n_patients=n_patients, n_abnormal=int(y.sum()),
        confs=confs.tolist(), y=y.tolist(),
        roc_tpr=roc_tpr, roc_fpr=roc_fpr,
    )


# ── Attack degradation simulation ─────────────────────────────────────────────
ATTACK_PROFILES = {
    "dos":        dict(label="DoS Flood",        noise=0.45, flip=0.25, color="#ef4444"),
    "spoof":      dict(label="Device Spoofing",  noise=0.30, flip=0.18, color="#f59e0b"),
    "tamper":     dict(label="Data Tampering",   noise=0.55, flip=0.30, color="#a78bfa"),
    "replay":     dict(label="Replay Attack",    noise=0.20, flip=0.12, color="#06b6d4"),
    "ransomware": dict(label="Ransomware Burst", noise=0.70, flip=0.40, color="#dc2626"),
}


def simulate_attack_degradation(n_patients: int = 50, seed: int = 99) -> dict:
    """For each attack type, compute accuracy with vs without attack."""
    patients = generate_biosignals(n_patients=n_patients, seed=seed)
    X, y = build_dataset(patients)
    mu = X.mean(axis=0); sigma = X.std(axis=0) + 1e-9
    X_n = (X - mu) / sigma
    y = y.astype(int)
    weights = vqc_init_weights(seed=seed)

    # Baseline accuracy
    baseline_preds = [int(np.clip(vqc_predict(xn, weights), 0, 1) > 0.5) for xn in X_n]
    baseline_acc = np.mean(np.array(baseline_preds) == y)

    results = {}
    for atk_key, profile in ATTACK_PROFILES.items():
        acc_at_intensity = []
        for intensity in np.linspace(0.1, 1.0, 10):
            noise_sc = profile["noise"] * intensity
            flip_p   = profile["flip"]  * intensity
            attacked_preds = []
            for xn in X_n:
                feat = xn + np.random.RandomState(seed).normal(0, noise_sc, xn.shape)
                c = float(np.clip(vqc_predict(feat, weights), 0, 1))
                if np.random.RandomState(seed).random() < flip_p:
                    c = 1.0 - c
                attacked_preds.append(int(c > 0.5))
            acc = float(np.mean(np.array(attacked_preds) == y))
            acc_at_intensity.append(round(acc, 4))
        results[atk_key] = dict(
            label=profile["label"],
            color=profile["color"],
            baseline_acc=round(float(baseline_acc), 4),
            acc_curve=acc_at_intensity,
            final_acc=acc_at_intensity[-1],
            degradation=round(float(baseline_acc) - acc_at_intensity[-1], 4),
        )
    return results
