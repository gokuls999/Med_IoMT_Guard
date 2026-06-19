"""
PennyLane quantum circuits:
  - VQC  : Variational Quantum Circuit for final prediction
  - QAttn: Quantum attention kernel for Q-Flex ViT
  - HQAN : Hybrid Quantum Attention Network layer
"""
import numpy as np
import pennylane as qml

N_QUBITS = 4
N_LAYERS = 3

# ── Devices ───────────────────────────────────────────────────────────────────
_vqc_dev  = qml.device("lightning.qubit", wires=N_QUBITS)
_attn_dev = qml.device("lightning.qubit", wires=N_QUBITS)


# ── VQC ───────────────────────────────────────────────────────────────────────
@qml.qnode(_vqc_dev)
def _vqc_qnode(inputs, weights):
    """4-qubit Variational Quantum Circuit (VQC) using StronglyEntanglingLayers."""
    qml.AngleEmbedding(inputs, wires=range(N_QUBITS), rotation='Y')
    qml.StronglyEntanglingLayers(weights, wires=range(N_QUBITS))
    return qml.expval(qml.PauliZ(0) @ qml.PauliZ(1))


def vqc_predict(features: np.ndarray, weights: np.ndarray) -> float:
    """Map arbitrary feature vector → [0,1] probability."""
    feat = np.array(features, dtype=float)
    feat_4 = feat[:N_QUBITS] / (np.linalg.norm(feat[:N_QUBITS]) + 1e-9) * np.pi
    raw = float(_vqc_qnode(feat_4, weights))
    return (raw + 1.0) / 2.0          # [-1,1] → [0,1]


def vqc_init_weights(seed: int = 42) -> np.ndarray:
    """Return random initial weights of shape (N_LAYERS, N_QUBITS, 3)."""
    rng = np.random.RandomState(seed)
    return rng.uniform(0, 2 * np.pi, (N_LAYERS, N_QUBITS, 3))


# ── Q-Flex ViT quantum attention ──────────────────────────────────────────────
@qml.qnode(_attn_dev)
def _qattn_qnode(query, key):
    """
    Q-Flex quantum attention kernel.
    Encodes query into wires 0-1 and key into wires 2-3,
    creates cross-entanglement, returns 4 Z-expectation values
    that serve as attention coefficients.
    """
    qml.AngleEmbedding(query, wires=[0, 1], rotation='Y')
    qml.AngleEmbedding(key,   wires=[2, 3], rotation='Y')

    # Cross-attention entanglement
    qml.Hadamard(wires=0)
    qml.Hadamard(wires=2)
    qml.CNOT(wires=[0, 2])
    qml.CNOT(wires=[1, 3])
    qml.CRZ(np.pi / 4, wires=[0, 1])
    qml.CRZ(np.pi / 4, wires=[2, 3])
    qml.Hadamard(wires=0)
    qml.Hadamard(wires=2)

    return [qml.expval(qml.PauliZ(i)) for i in range(N_QUBITS)]


def quantum_attention(query: np.ndarray, key: np.ndarray) -> np.ndarray:
    """Return 4-dim attention weight vector in [0,1]."""
    q2 = query[:2] / (np.linalg.norm(query[:2]) + 1e-9) * (np.pi / 2)
    k2 = key[:2]   / (np.linalg.norm(key[:2])   + 1e-9) * (np.pi / 2)
    raw = np.array(_qattn_qnode(q2, k2), dtype=float)
    weights = (raw + 1.0) / 2.0        # → [0,1]
    return weights / (weights.sum() + 1e-9)


# ── HQAN layer ────────────────────────────────────────────────────────────────
def hqan_forward(features: np.ndarray, proj_weights: np.ndarray):
    """
    One Hybrid Quantum Attention Network forward pass.
    proj_weights shape: (2, n_features)  — query and key projections.
    Returns (attended_features, attn_weights).
    """
    n = len(features)
    q = np.tanh(proj_weights[0, :n] * features)
    k = np.tanh(proj_weights[1, :n] * features)

    attn = quantum_attention(q, k)             # 4-dim
    attn_full = np.resize(attn, n)             # tile to feature length

    attended = features * attn_full
    return attended, attn


# ── Circuit drawing helpers ───────────────────────────────────────────────────
def draw_vqc_circuit():
    """Return a matplotlib Figure of the VQC circuit (light theme)."""
    import matplotlib.pyplot as plt
    weights = vqc_init_weights()
    inputs  = np.zeros(N_QUBITS)
    fig, ax = qml.draw_mpl(_vqc_qnode, style='default')(inputs, weights)
    fig.patch.set_facecolor('#ffffff')
    ax.patch.set_facecolor('#f8fafc')
    ax.set_title("VQC  —  Variational Quantum Circuit  (4 qubits, 3 layers)",
                 color='#0f172a', fontsize=11, pad=10)
    return fig


def draw_attention_circuit():
    """Return a matplotlib Figure of the quantum attention circuit (light theme)."""
    import matplotlib.pyplot as plt
    q = np.zeros(2)
    k = np.zeros(2)
    fig, ax = qml.draw_mpl(_qattn_qnode, style='default')(q, k)
    fig.patch.set_facecolor('#ffffff')
    ax.patch.set_facecolor('#f8fafc')
    ax.set_title("Q-Flex ViT  —  Quantum Attention Circuit",
                 color='#0f172a', fontsize=11, pad=10)
    return fig
