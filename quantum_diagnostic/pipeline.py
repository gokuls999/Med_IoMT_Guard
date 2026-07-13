"""
Quantum IoMT Attack Detection Pipeline
ANUKF → Q-Flex ViT → BMOCO → HQAN → RBWKA → VQC → Adaptive SHARP
Classifies IoMT network traffic: ATTACK (1) or NORMAL (0).
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from data_generator import generate_traffic, build_dataset, FEATURE_NAMES
from anukf import ScalarUKF, _adaptive_covariance
from quantum_circuits import vqc_predict, vqc_init_weights, hqan_forward, N_QUBITS, N_LAYERS
from bmoco import BMOCO
from rbwka import RBWKA


def run_pipeline(
    n_packets:    int = 60,
    seed:         int = 42,
    bmoco_iters:  int = 15,
    rbwka_iters:  int = 20,
    progress_cb=None,
    override_packets=None,
) -> dict:
    results = {}
    _cb = progress_cb or (lambda s, m: None)

    # ── 1. Network traffic data ───────────────────────────────────────────────
    _cb(1, "Generating IoMT network traffic data…")
    packets = override_packets if override_packets is not None else \
              generate_traffic(n_packets=n_packets, seed=seed)
    results['packets']   = packets
    results['n_packets'] = len(packets)
    results['n_attacks'] = sum(p.label for p in packets)

    atk_counts = {}
    for p in packets:
        atk_counts[p.attack_type] = atk_counts.get(p.attack_type, 0) + 1
    results['attack_counts'] = atk_counts

    # ── 2. ANUKF preprocessing ────────────────────────────────────────────────
    _cb(2, "Applying ANUKF to IoMT packet streams…")
    sample = packets[0]
    Q_r, R_r = _adaptive_covariance(sample.rate_series)
    Q_b, R_b = _adaptive_covariance(sample.byte_series)
    results['anukf_sample'] = {
        'raw_rate':    sample.rate_series,
        'filt_rate':   ScalarUKF(Q=Q_r, R=R_r).filter(sample.rate_series),
        'raw_byte':    sample.byte_series,
        'filt_byte':   ScalarUKF(Q=Q_b, R=R_b).filter(sample.byte_series),
        'attack_type': sample.attack_type,
    }

    anukf_by_type = {}
    for p in packets:
        if p.attack_type not in anukf_by_type:
            Qr, Rr = _adaptive_covariance(p.rate_series)
            anukf_by_type[p.attack_type] = {
                'raw_rate':    p.rate_series,
                'filt_rate':   ScalarUKF(Q=Qr, R=Rr).filter(p.rate_series),
                'attack_type': p.attack_type,
            }
    results['anukf_by_type'] = anukf_by_type

    # ── 3. Q-Flex ViT feature extraction ─────────────────────────────────────
    _cb(3, "Extracting quantum features with Q-Flex ViT…")
    X_raw, y = build_dataset(packets)
    mu    = X_raw.mean(axis=0)
    sigma = X_raw.std(axis=0) + 1e-9
    X_norm = (X_raw - mu) / sigma

    results['X_raw']          = X_raw
    results['X_norm']         = X_norm
    results['y']              = y
    results['feature_names']  = FEATURE_NAMES
    results['normalise_mu']   = mu
    results['normalise_sigma'] = sigma
    results['attack_types']   = [p.attack_type for p in packets]

    # ── 4. BMOCO feature selection ────────────────────────────────────────────
    _cb(4, "Running BMOCO feature selection…")
    bmoco = BMOCO(n_features=X_norm.shape[1], n_population=20,
                  n_iterations=bmoco_iters, seed=seed)
    sel_idx, sel_mask, bmoco_best = bmoco.optimize(X_norm, y)

    results['sel_idx']           = sel_idx
    results['sel_mask']          = sel_mask
    results['sel_feature_names'] = [FEATURE_NAMES[i] for i in sel_idx]
    results['bmoco_best_fitness'] = float(bmoco_best)
    results['bmoco_history']     = bmoco.history

    X_sel = X_norm[:, sel_idx]
    results['X_sel'] = X_sel

    # ── 5. HQAN analysis ──────────────────────────────────────────────────────
    _cb(5, "Running Hybrid Quantum Attention Network…")
    rng    = np.random.RandomState(seed + 1)
    n_sel  = X_sel.shape[1]
    proj_w = rng.uniform(-1, 1, (2, n_sel))

    hqan_out, hqan_attn = [], []
    for xn in X_sel:
        attended, attn = hqan_forward(xn, proj_w)
        hqan_out.append(attended)
        hqan_attn.append(attn)

    X_hqan = np.array(hqan_out)
    results['X_hqan']    = X_hqan
    results['hqan_attn'] = np.array(hqan_attn)

    # ── 6. RBWKA optimisation ─────────────────────────────────────────────────
    _cb(6, "Optimising VQC weights with Revamped Black-Winged Kite Algorithm…")
    w0        = vqc_init_weights(seed=seed)
    eval_size = min(30, len(X_hqan))

    def _fitness(flat_w):
        w = flat_w.reshape(N_LAYERS, N_QUBITS, 3)
        preds = np.array([vqc_predict(X_hqan[i], w) for i in range(eval_size)])
        return float(np.mean((preds > 0.5).astype(int) == y[:eval_size]))

    rbwka = RBWKA(dim=N_LAYERS * N_QUBITS * 3, n_population=12,
                  n_iterations=rbwka_iters, seed=seed)
    best_flat, rbwka_best = rbwka.optimize(_fitness, x0=w0)
    opt_weights = best_flat.reshape(N_LAYERS, N_QUBITS, 3)

    results['opt_weights']       = opt_weights
    results['rbwka_best_fitness'] = float(rbwka_best)
    results['rbwka_history']     = rbwka.history

    # ── 7. VQC attack detection ───────────────────────────────────────────────
    _cb(7, "Running VQC quantum attack detection…")
    probs = np.array([vqc_predict(X_hqan[i], opt_weights) for i in range(len(X_hqan))])
    preds = (probs > 0.5).astype(int)

    tp = int(np.sum((preds == 1) & (y == 1)))
    fp = int(np.sum((preds == 1) & (y == 0)))
    tn = int(np.sum((preds == 0) & (y == 0)))
    fn = int(np.sum((preds == 0) & (y == 1)))
    prec = tp / (tp + fp + 1e-9)
    rec  = tp / (tp + fn + 1e-9)
    f1   = 2 * prec * rec / (prec + rec + 1e-9)
    fpr  = fp / (fp + tn + 1e-9)

    results['probs']     = probs
    results['preds']     = preds
    results['accuracy']  = float(np.mean(preds == y))
    results['precision'] = float(prec)
    results['recall']    = float(rec)
    results['f1']        = float(f1)
    results['fpr']       = float(fpr)
    results['confusion'] = {'TP': tp, 'FP': fp, 'TN': tn, 'FN': fn}

    atk_types_list = [p.attack_type for p in packets]
    atk_detection  = {}
    for atk in set(atk_types_list):
        idxs = [i for i, a in enumerate(atk_types_list) if a == atk]
        if idxs:
            atk_detection[atk] = float(np.mean(preds[idxs] == y[idxs]))
    results['atk_detection'] = atk_detection

    # ── 8. Adaptive SHARP explainability ─────────────────────────────────────
    _cb(8, "Computing Adaptive SHARP feature importance…")
    base_probs = probs.copy()
    importance = np.zeros(len(sel_idx))
    for j in range(len(sel_idx)):
        X_perm = X_hqan.copy()
        col    = j % X_perm.shape[1]
        X_perm[:, col] = rng.permutation(X_perm[:, col])
        perm_probs = np.array([vqc_predict(X_perm[i], opt_weights) for i in range(len(X_perm))])
        importance[j] = float(np.mean(np.abs(base_probs - perm_probs)))

    order = np.argsort(importance)[::-1]
    thresh = float(np.mean(importance))

    results['importance']          = importance
    results['importance_order']    = order
    results['adaptive_threshold']  = thresh
    results['significant_features'] = importance > thresh
    results['sharp_feature_names'] = [FEATURE_NAMES[i] for i in sel_idx]

    _cb(9, "Pipeline complete.")
    return results
