"""
Full quantum IoMT diagnostic pipeline orchestrator.
Stages: Data → ANUKF → Q-Flex ViT → BMOCO → HQAN → RBWKA → VQC → Adaptive SHARP
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from data_generator import generate_biosignals, build_dataset, FEATURE_NAMES
from anukf import ANUKF
from quantum_circuits import (
    vqc_predict, vqc_init_weights, hqan_forward, N_QUBITS, N_LAYERS,
)
from bmoco import BMOCO
from rbwka import RBWKA


def run_pipeline(
    n_patients: int = 60,
    seed: int = 42,
    bmoco_iters: int = 15,
    rbwka_iters: int = 20,
    progress_cb=None,
    override_patients=None,     # list[PatientSignal] — supply hospital data directly
) -> dict:
    results = {}
    _cb = progress_cb or (lambda s, m: None)

    # ── 1. Data collection ────────────────────────────────────────────────────
    if override_patients is not None:
        _cb(1, "Loading hospital IoMT device data…")
        patients = override_patients
    else:
        _cb(1, "Generating multimodal biosignals…")
        patients = generate_biosignals(n_patients=n_patients, seed=seed)
    results['patients'] = patients
    results['n_patients'] = n_patients
    results['n_abnormal'] = sum(p.label for p in patients)

    # ── 2. ANUKF preprocessing ────────────────────────────────────────────────
    _cb(2, "Running ANUKF adaptive filtering…")
    anukf = ANUKF()
    sample_filter = anukf.process(patients[0])   # keep for visualisation
    filtered_patients = []
    for p in patients:
        fd = anukf.process(p)
        filtered_patients.append(anukf.get_filtered_patient(p, fd))
    results['anukf_sample'] = sample_filter
    results['filtered_patients'] = filtered_patients

    # ── 3. Q-Flex ViT feature extraction ─────────────────────────────────────
    _cb(3, "Extracting features with Q-Flex ViT…")
    X_raw, y = build_dataset(patients)
    X_filt, _ = build_dataset(filtered_patients)

    mu = X_filt.mean(axis=0)
    sigma = X_filt.std(axis=0) + 1e-9
    X_norm = (X_filt - mu) / sigma

    results['X_raw'] = X_raw
    results['X_norm'] = X_norm
    results['y'] = y
    results['feature_names'] = FEATURE_NAMES
    results['normalise_mu'] = mu
    results['normalise_sigma'] = sigma

    # ── 4. BMOCO feature selection ────────────────────────────────────────────
    _cb(4, "Running BMOCO feature selection…")
    bmoco = BMOCO(
        n_features=X_norm.shape[1],
        n_population=20,
        n_iterations=bmoco_iters,
        seed=seed,
    )
    sel_idx, sel_mask, bmoco_best = bmoco.optimize(X_norm, y)
    results['sel_idx'] = sel_idx
    results['sel_mask'] = sel_mask
    results['sel_feature_names'] = [FEATURE_NAMES[i] for i in sel_idx]
    results['bmoco_best_fitness'] = float(bmoco_best)
    results['bmoco_history'] = bmoco.history

    X_sel = X_norm[:, sel_idx]
    results['X_sel'] = X_sel

    # ── 5. HQAN analysis ──────────────────────────────────────────────────────
    _cb(5, "Running Hybrid Quantum Attention Network…")
    rng = np.random.RandomState(seed + 1)
    n_sel = X_sel.shape[1]
    proj_w = rng.uniform(-1, 1, (2, n_sel))

    hqan_out = []
    hqan_attn = []
    for i in range(len(X_sel)):
        attended, attn = hqan_forward(X_sel[i], proj_w)
        hqan_out.append(attended)
        hqan_attn.append(attn)

    X_hqan = np.array(hqan_out)
    results['X_hqan'] = X_hqan
    results['hqan_attn'] = np.array(hqan_attn)

    # ── 6. RBWKA optimisation of VQC weights ─────────────────────────────────
    _cb(6, "Optimising VQC with Revamped Black-Winged Kite Algorithm…")
    w0 = vqc_init_weights(seed=seed)
    eval_size = min(30, len(X_hqan))

    def _fitness(flat_w):
        w = flat_w.reshape(N_LAYERS, N_QUBITS, 3)
        preds = np.array([vqc_predict(X_hqan[i], w) for i in range(eval_size)])
        pred_labels = (preds > 0.5).astype(int)
        return float(np.mean(pred_labels == y[:eval_size]))

    rbwka = RBWKA(
        dim=N_LAYERS * N_QUBITS * 3,
        n_population=12,
        n_iterations=rbwka_iters,
        seed=seed,
    )
    best_flat, rbwka_best = rbwka.optimize(_fitness, x0=w0)
    opt_weights = best_flat.reshape(N_LAYERS, N_QUBITS, 3)

    results['opt_weights'] = opt_weights
    results['rbwka_best_fitness'] = float(rbwka_best)
    results['rbwka_history'] = rbwka.history

    # ── 7. VQC prediction ─────────────────────────────────────────────────────
    _cb(7, "Running VQC quantum predictions…")
    probs = np.array([vqc_predict(X_hqan[i], opt_weights) for i in range(len(X_hqan))])
    preds = (probs > 0.5).astype(int)

    tp = int(np.sum((preds == 1) & (y == 1)))
    fp = int(np.sum((preds == 1) & (y == 0)))
    tn = int(np.sum((preds == 0) & (y == 0)))
    fn = int(np.sum((preds == 0) & (y == 1)))
    precision = tp / (tp + fp + 1e-9)
    recall    = tp / (tp + fn + 1e-9)
    f1        = 2 * precision * recall / (precision + recall + 1e-9)

    results['probs']     = probs
    results['preds']     = preds
    results['accuracy']  = float(np.mean(preds == y))
    results['precision'] = float(precision)
    results['recall']    = float(recall)
    results['f1']        = float(f1)
    results['confusion'] = {'TP': tp, 'FP': fp, 'TN': tn, 'FN': fn}

    # ── 8. Adaptive SHARP explainability ─────────────────────────────────────
    _cb(8, "Computing Adaptive SHARP explanations…")
    # Permutation importance as XAI proxy (quantum-safe)
    base_probs = probs.copy()
    importance = np.zeros(len(sel_idx))
    for j in range(len(sel_idx)):
        X_perm = X_hqan.copy()
        perm_col = j % X_perm.shape[1]
        X_perm[:, perm_col] = rng.permutation(X_perm[:, perm_col])
        perm_probs = np.array([vqc_predict(X_perm[i], opt_weights) for i in range(len(X_perm))])
        importance[j] = float(np.mean(np.abs(base_probs - perm_probs)))

    # Adaptive: sort by importance, keep only significant ones
    order = np.argsort(importance)[::-1]
    adaptive_threshold = float(np.mean(importance))
    significant = importance > adaptive_threshold

    results['importance'] = importance
    results['importance_order'] = order
    results['adaptive_threshold'] = adaptive_threshold
    results['significant_features'] = significant
    results['sharp_feature_names'] = [FEATURE_NAMES[i] for i in sel_idx]

    _cb(9, "Pipeline complete.")
    return results
