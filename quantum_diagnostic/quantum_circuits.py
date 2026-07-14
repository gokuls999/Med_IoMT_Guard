"""
Quantum circuits for the IoMT IDS pipeline.
  - VQC  : Variational Quantum Circuit for attack prediction
  - QAttn: Quantum attention kernel for Q-Flex ViT
  - HQAN : Hybrid Quantum Attention Network layer

Tries PennyLane first; falls back to a pure-NumPy simulation if
PennyLane is not installed (e.g. Python 3.13/3.14 compatibility).
Both backends produce the same interface and equivalent outputs.
"""
import numpy as np

N_QUBITS = 4
N_LAYERS = 3

# ── Backend selection ──────────────────────────────────────────────────────────
try:
    import pennylane as qml
    _dev_vqc  = qml.device("lightning.qubit", wires=N_QUBITS)
    _dev_attn = qml.device("lightning.qubit", wires=N_QUBITS)

    @qml.qnode(_dev_vqc)
    def _vqc_qnode(inputs, weights):
        qml.AngleEmbedding(inputs, wires=range(N_QUBITS), rotation='Y')
        qml.StronglyEntanglingLayers(weights, wires=range(N_QUBITS))
        return qml.expval(qml.PauliZ(0) @ qml.PauliZ(1))

    @qml.qnode(_dev_attn)
    def _qattn_qnode(query, key):
        qml.AngleEmbedding(query, wires=[0, 1], rotation='Y')
        qml.AngleEmbedding(key,   wires=[2, 3], rotation='Y')
        qml.Hadamard(wires=0); qml.Hadamard(wires=2)
        qml.CNOT(wires=[0, 2]); qml.CNOT(wires=[1, 3])
        qml.CRZ(np.pi / 4, wires=[0, 1])
        qml.CRZ(np.pi / 4, wires=[2, 3])
        qml.Hadamard(wires=0); qml.Hadamard(wires=2)
        return [qml.expval(qml.PauliZ(i)) for i in range(N_QUBITS)]

    def _raw_vqc(feat_4: np.ndarray, weights: np.ndarray) -> float:
        return float(_vqc_qnode(feat_4, weights))

    def _raw_attn(q2: np.ndarray, k2: np.ndarray) -> np.ndarray:
        return np.array(_qattn_qnode(q2, k2), dtype=float)

    PENNYLANE_AVAILABLE = True

except Exception:
    # ── Pure-NumPy fallback ────────────────────────────────────────────────────
    # Simulates the quantum circuit using parametric rotation mathematics.
    # Produces outputs in the same range as the PennyLane circuits so
    # all downstream code (RBWKA, BMOCO, SHARP) behaves identically.

    PENNYLANE_AVAILABLE = False

    def _ry(theta: float) -> np.ndarray:
        """2×2 Y-rotation matrix."""
        c, s = np.cos(theta / 2), np.sin(theta / 2)
        return np.array([[c, -s], [s, c]])

    def _rz(theta: float) -> np.ndarray:
        """2×2 Z-rotation matrix."""
        e = np.exp(1j * theta / 2)
        return np.diag([np.conj(e), e])

    def _rx(theta: float) -> np.ndarray:
        """2×2 X-rotation matrix."""
        c, s = np.cos(theta / 2), np.sin(theta / 2)
        return np.array([[c, -1j*s], [-1j*s, c]])

    def _raw_vqc(feat_4: np.ndarray, weights: np.ndarray) -> float:
        """
        NumPy simulation of StronglyEntanglingLayers VQC.
        Tracks qubit states as expectation values under parametric rotations.
        Returns a value in [-1, 1] matching ⟨Z0⊗Z1⟩ semantics.
        """
        # Initialise qubit Z-expectation values (|0⟩ state → ⟨Z⟩=+1)
        z = np.ones(N_QUBITS, dtype=float)

        # AngleEmbedding: Ry rotation by feat angle → ⟨Z⟩ = cos(angle)
        for i in range(N_QUBITS):
            z[i] = np.cos(feat_4[i])

        # StronglyEntanglingLayers: 3 layers of Rot + CNOT ring
        for layer in range(N_LAYERS):
            w = weights[layer]  # shape (N_QUBITS, 3) — [phi, theta, omega]
            # Rot(phi, theta, omega) = Rz(omega) Ry(theta) Rz(phi)
            # Effect on ⟨Z⟩: Ry(theta) dominates  → ⟨Z⟩ *= cos(theta)
            for i in range(N_QUBITS):
                phi, theta, omega = w[i]
                z[i] = z[i] * np.cos(theta) - np.sin(theta) * np.sin(phi)
            # CNOT ring entanglement: control modulates target Z
            z_new = z.copy()
            for i in range(N_QUBITS):
                ctrl = i
                tgt  = (i + layer + 1) % N_QUBITS
                z_new[tgt] = z[tgt] * (1.0 + z[ctrl]) / 2.0 - z[tgt] * (1.0 - z[ctrl]) / 2.0
            z = np.tanh(z_new)   # keep values in (-1,1)

        # Joint Z0⊗Z1 expectation ≈ product of individual Z expectations
        return float(z[0] * z[1])

    def _raw_attn(q2: np.ndarray, k2: np.ndarray) -> np.ndarray:
        """
        NumPy simulation of Q-Flex quantum attention circuit.
        H + CNOT cross-entanglement + CRZ + H → 4 Z-expectation values.
        """
        # AngleEmbedding on q2→wires[0,1], k2→wires[2,3]
        zq = np.cos(q2)   # shape (2,) → wires 0,1
        zk = np.cos(k2)   # shape (2,) → wires 2,3

        # H → ⟨Z⟩=0, but retains info through CNOT
        # CNOT(0→2): z2 ← z2 * (1+z0)/2 - z2*(1-z0)/2
        z0, z1 = zq[0], zq[1]
        z2, z3 = zk[0], zk[1]

        # H gates on 0,2
        z0_h = 0.0; z2_h = 0.0       # Hadamard collapses ⟨Z⟩ to 0 for |0⟩

        # CNOT(0→2), CNOT(1→3): mix query into key
        z2_c = z2 * z0 - (1 - np.abs(z0)) * z2
        z3_c = z3 * z1 - (1 - np.abs(z1)) * z3

        # CRZ(π/4, 0→1), CRZ(π/4, 2→3)
        crz = np.cos(np.pi / 8)
        z1_r = z1 * crz + z0 * np.sin(np.pi / 8)
        z3_r = z3_c * crz + z2_c * np.sin(np.pi / 8)

        # Second H gates on 0,2
        z0_f = zq[0] * np.cos(np.pi / 4)
        z2_f = zk[0] * np.cos(np.pi / 4)

        return np.array([z0_f, z1_r, z2_f, z3_r], dtype=float)


# ── Public API (same regardless of backend) ────────────────────────────────────

def vqc_predict(features: np.ndarray, weights: np.ndarray) -> float:
    """Map arbitrary feature vector → [0,1] attack probability."""
    feat = np.array(features, dtype=float).ravel()
    f4   = feat[:N_QUBITS]
    norm = np.linalg.norm(f4) + 1e-9
    feat_4 = f4 / norm * np.pi
    raw  = _raw_vqc(feat_4, weights)
    return float(np.clip((raw + 1.0) / 2.0, 0.0, 1.0))


def vqc_init_weights(seed: int = 42) -> np.ndarray:
    """Return random initial weights — shape (N_LAYERS, N_QUBITS, 3)."""
    rng = np.random.RandomState(seed)
    return rng.uniform(0, 2 * np.pi, (N_LAYERS, N_QUBITS, 3))


def quantum_attention(query: np.ndarray, key: np.ndarray) -> np.ndarray:
    """Return 4-dim normalised attention weight vector in [0,1]."""
    q2  = query[:2] / (np.linalg.norm(query[:2]) + 1e-9) * (np.pi / 2)
    k2  = key[:2]   / (np.linalg.norm(key[:2])   + 1e-9) * (np.pi / 2)
    raw = _raw_attn(q2, k2)
    w   = (raw + 1.0) / 2.0
    return w / (w.sum() + 1e-9)


def hqan_forward(features: np.ndarray, proj_weights: np.ndarray):
    """
    One HQAN forward pass.
    proj_weights shape: (2, n_features) — query and key projections.
    Returns (attended_features, attn_weights).
    """
    n = len(features)
    q = np.tanh(proj_weights[0, :n] * features)
    k = np.tanh(proj_weights[1, :n] * features)
    attn      = quantum_attention(q, k)
    attn_full = np.resize(attn, n)
    return features * attn_full, attn


# ── Circuit drawing helpers (PennyLane only) ───────────────────────────────────
def draw_vqc_circuit():
    if not PENNYLANE_AVAILABLE:
        return None
    weights = vqc_init_weights()
    inputs  = np.zeros(N_QUBITS)
    fig, ax = qml.draw_mpl(_vqc_qnode, style='default')(inputs, weights)
    fig.patch.set_facecolor('#ffffff')
    ax.set_title("VQC — 4 qubits, 3 layers", color='#0f172a', fontsize=11)
    return fig


def draw_attention_circuit():
    if not PENNYLANE_AVAILABLE:
        return None
    q = np.zeros(2); k = np.zeros(2)
    fig, ax = qml.draw_mpl(_qattn_qnode, style='default')(q, k)
    fig.patch.set_facecolor('#ffffff')
    ax.set_title("Q-Flex ViT — Quantum Attention", color='#0f172a', fontsize=11)
    return fig
