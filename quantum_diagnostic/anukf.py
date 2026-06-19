"""
Adaptive Neural Unscented Kalman Filter (ANUKF)
Filters noisy multimodal biosignals using per-signal adaptive noise covariance.
"""
import numpy as np
from dataclasses import dataclass


@dataclass
class UKFConfig:
    alpha: float = 1e-3
    beta: float  = 2.0
    kappa: float = 0.0


class ScalarUKF:
    """1-D Unscented Kalman Filter for signal denoising."""

    def __init__(self, Q: float = 0.01, R: float = 0.1):
        self.Q = Q
        self.R = R
        self.cfg = UKFConfig()

    def _sigma_weights(self):
        n = 1
        lam = self.cfg.alpha ** 2 * (n + self.cfg.kappa) - n
        Wm = np.full(2 * n + 1, 0.5 / (n + lam))
        Wm[0] = lam / (n + lam)
        Wc = Wm.copy()
        Wc[0] += (1 - self.cfg.alpha ** 2 + self.cfg.beta)
        scale = np.sqrt(n + lam)
        return Wm, Wc, scale

    def filter(self, signal: np.ndarray) -> np.ndarray:
        Wm, Wc, scale = self._sigma_weights()
        x = signal[0]
        P = 1.0
        out = np.empty_like(signal)

        for k, z in enumerate(signal):
            # Sigma points
            pts = np.array([x, x + scale * np.sqrt(P), x - scale * np.sqrt(P)])

            # Predict
            x_pred = float(Wm @ pts)
            P_pred = float(Wc @ ((pts - x_pred) ** 2)) + self.Q

            # Update
            z_pred = x_pred
            Pzz = P_pred + self.R
            K = P_pred / Pzz
            x = x_pred + K * (z - z_pred)
            P = (1 - K) * P_pred
            out[k] = x

        return out


# ── Neural adaptive component ─────────────────────────────────────────────────
def _adaptive_covariance(signal: np.ndarray):
    """Infer Q and R from signal statistics (lightweight 'neural' adaptation)."""
    var = np.var(signal)
    peak_to_peak = np.ptp(signal)
    # Q scales with signal dynamics; R scales with noise estimate
    Q = np.clip(0.002 * var, 1e-7, 0.5)
    R = np.clip(0.08 * peak_to_peak, 1e-4, 10.0)
    return float(Q), float(R)


class ANUKF:
    """Adaptive Neural Unscented Kalman Filter — processes all biosignal modalities."""

    _SIGNAL_NAMES = ['ecg', 'sbp', 'dbp', 'temp', 'eeg', 'spo2']

    def process(self, patient) -> dict:
        """Return dict with raw / filtered / residual for each signal."""
        results = {}
        for name in self._SIGNAL_NAMES:
            raw = getattr(patient, name)
            Q, R = _adaptive_covariance(raw)
            filtered = ScalarUKF(Q=Q, R=R).filter(raw)
            results[name] = {
                'raw':      raw,
                'filtered': filtered,
                'residual': raw - filtered,
                'Q': Q, 'R': R,
                'snr_db': float(10 * np.log10(
                    (np.var(filtered) + 1e-12) / (np.var(raw - filtered) + 1e-12)
                )),
            }
        return results

    def get_filtered_patient(self, original, filtered_dict):
        from data_generator import PatientSignal
        return PatientSignal(
            patient_id=original.patient_id,
            label=original.label,
            ecg=filtered_dict['ecg']['filtered'],
            sbp=filtered_dict['sbp']['filtered'],
            dbp=filtered_dict['dbp']['filtered'],
            temp=filtered_dict['temp']['filtered'],
            eeg=filtered_dict['eeg']['filtered'],
            spo2=filtered_dict['spo2']['filtered'],
        )
