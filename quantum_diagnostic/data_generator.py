"""
IoMT Network Traffic Generator — Quantum IDS
Synthetic IoMT network packet streams for quantum-enhanced attack detection.
Labels: 0 = normal, 1 = attack
Attack types: dos, spoof, tamper, replay, ransomware
"""
import numpy as np
from dataclasses import dataclass, field

FEATURE_NAMES = [
    "packet_rate",      # packets/sec        — very high in DoS
    "byte_ratio",       # src/dst bytes      — skewed in attacks
    "duration",         # connection sec     — short in DoS, long in ransomware
    "proto_enc",        # protocol           — TCP=0, UDP=0.5, ICMP=1
    "ttl_norm",         # TTL consistency    — forged in spoofing
    "payload_entropy",  # data randomness    — high in ransomware/tamper
    "conn_count",       # src connections    — massive in DoS/scan
    "failed_auth",      # auth failures      — high in spoofing
    "port_enc",         # dst port category  — unusual in C2/ransomware
    "flag_enc",         # TCP flag pattern   — SYN flood in DoS
]

ATTACK_TYPES = ["normal", "dos", "spoof", "tamper", "replay", "ransomware"]
N_FEATURES   = len(FEATURE_NAMES)
N_TIMESTEPS  = 200


@dataclass
class NetworkPacket:
    packet_id:    int
    label:        int    # 0 = normal, 1 = attack
    attack_type:  str
    features:     np.ndarray = field(repr=False)    # shape (N_FEATURES,)
    rate_series:  np.ndarray = field(repr=False)    # 200-step packet-rate time series
    byte_series:  np.ndarray = field(repr=False)    # 200-step byte-count time series


# ── Per-attack feature generators ─────────────────────────────────────────────
def _normal(rng):
    return np.array([
        rng.uniform(10, 80),     # packet_rate   — moderate
        rng.uniform(0.8, 1.2),   # byte_ratio    — balanced src/dst
        rng.uniform(1.0, 30.0),  # duration      — typical session
        rng.choice([0.0, 0.5]),  # proto_enc     — TCP or UDP
        rng.uniform(0.88, 1.0),  # ttl_norm      — consistent
        rng.uniform(0.05, 0.25), # payload_entropy — low (plaintext)
        rng.uniform(1, 10),      # conn_count    — few connections
        rng.uniform(0.0, 0.04),  # failed_auth   — minimal
        rng.uniform(0.2, 0.5),   # port_enc      — standard ports
        rng.uniform(0.1, 0.3),   # flag_enc      — SYN/ACK normal
    ])


def _dos(rng):
    return np.array([
        rng.uniform(800, 2000),  # packet_rate   — VERY high (flood)
        rng.uniform(5, 25),      # byte_ratio    — src-heavy
        rng.uniform(0.01, 0.5),  # duration      — very short
        1.0,                     # proto_enc     — ICMP flood
        rng.uniform(0.7, 0.92),  # ttl_norm      — slightly anomalous
        rng.uniform(0.05, 0.2),  # payload_entropy — low (same payload)
        rng.uniform(100, 500),   # conn_count    — massive
        rng.uniform(0.0, 0.08),  # failed_auth   — low (just flooding)
        rng.uniform(0.0, 0.2),   # port_enc      — port 80/443
        rng.uniform(0.8, 1.0),   # flag_enc      — SYN flood pattern
    ])


def _spoof(rng):
    return np.array([
        rng.uniform(20, 100),    # packet_rate   — moderate
        rng.uniform(2, 8),       # byte_ratio    — asymmetric
        rng.uniform(0.5, 5.0),   # duration      — brief sessions
        rng.choice([0.0, 0.5]),  # proto_enc
        rng.uniform(0.25, 0.55), # ttl_norm      — ANOMALOUS forged TTL
        rng.uniform(0.2, 0.5),   # payload_entropy — moderate
        rng.uniform(1, 20),      # conn_count    — moderate
        rng.uniform(0.45, 0.95), # failed_auth   — HIGH (spoofed creds)
        rng.uniform(0.5, 0.9),   # port_enc      — unusual ports
        rng.uniform(0.4, 0.7),   # flag_enc      — RST/FIN patterns
    ])


def _tamper(rng):
    return np.array([
        rng.uniform(30, 150),    # packet_rate   — normal-ish
        rng.uniform(0.5, 3.0),   # byte_ratio    — slightly off
        rng.uniform(5.0, 60.0),  # duration      — longer sessions
        rng.choice([0.0, 0.5]),  # proto_enc
        rng.uniform(0.85, 1.0),  # ttl_norm      — normal
        rng.uniform(0.62, 0.92), # payload_entropy — HIGH (modified data)
        rng.uniform(2, 15),      # conn_count    — few
        rng.uniform(0.0, 0.15),  # failed_auth   — low
        rng.uniform(0.3, 0.6),   # port_enc      — clinical data ports
        rng.uniform(0.2, 0.5),   # flag_enc      — PSH/ACK (data transfer)
    ])


def _replay(rng):
    return np.array([
        rng.uniform(50, 200),    # packet_rate   — moderate-high (duplicates)
        rng.uniform(0.88, 1.12), # byte_ratio    — balanced (same packets)
        rng.uniform(0.1, 2.0),   # duration      — very brief (replayed)
        0.0,                     # proto_enc     — TCP (stateful)
        rng.uniform(0.85, 1.0),  # ttl_norm      — normal (valid packets)
        rng.uniform(0.05, 0.25), # payload_entropy — LOW (same data)
        rng.uniform(5, 50),      # conn_count    — repeated same src
        rng.uniform(0.12, 0.35), # failed_auth   — some (stale tokens)
        rng.uniform(0.2, 0.5),   # port_enc      — normal ports
        rng.uniform(0.5, 0.8),   # flag_enc      — unusual ACK timing
    ])


def _ransomware(rng):
    return np.array([
        rng.uniform(100, 400),   # packet_rate   — high (exfil + encrypt)
        rng.uniform(10, 50),     # byte_ratio    — heavy outbound
        rng.uniform(30, 300),    # duration      — long persistent session
        0.0,                     # proto_enc     — TCP (C2 comms)
        rng.uniform(0.8, 1.0),   # ttl_norm      — normal
        rng.uniform(0.88, 1.0),  # payload_entropy — VERY HIGH (encrypted)
        rng.uniform(1, 5),       # conn_count    — few (targeted C2)
        rng.uniform(0.0, 0.08),  # failed_auth   — low (already inside)
        rng.uniform(0.72, 1.0),  # port_enc      — unusual C2 ports
        rng.uniform(0.3, 0.6),   # flag_enc      — PSH/ACK (bulk transfer)
    ])


_FEAT_FNS = {
    "normal":     _normal,
    "dos":        _dos,
    "spoof":      _spoof,
    "tamper":     _tamper,
    "replay":     _replay,
    "ransomware": _ransomware,
}


def _make_rate_series(attack_type: str, base_rate: float, rng, n: int = N_TIMESTEPS):
    noise = rng.normal(0, base_rate * 0.08 + 1, n)
    t = np.linspace(0, 4 * np.pi, n)
    if attack_type == "dos":
        burst = int(n * 0.3)
        s = np.full(n, base_rate * 0.05)
        s[burst:] = base_rate + rng.normal(0, base_rate * 0.04 + 1, n - burst)
    elif attack_type == "ransomware":
        s = np.linspace(10, base_rate, n) + noise
    elif attack_type == "replay":
        s = base_rate * 0.3 + base_rate * 0.7 * (np.sin(t * 3) > 0.5) + noise
    elif attack_type == "spoof":
        s = base_rate + rng.normal(0, base_rate * 0.3 + 1, n)
    else:
        s = base_rate + noise
    return np.abs(s)


def _make_byte_series(attack_type: str, byte_ratio: float, rng, n: int = N_TIMESTEPS):
    base = byte_ratio * 1000
    noise = rng.normal(0, abs(base) * 0.1 + 1, n)
    if attack_type == "ransomware":
        s = np.linspace(base * 0.1, base * 5, n) + noise
    elif attack_type == "dos":
        s = np.full(n, base * 0.05)
        burst = int(n * 0.3)
        s[burst:] = base + noise[burst:]
    elif attack_type == "tamper":
        s = base + np.sin(np.linspace(0, 6 * np.pi, n)) * base * 0.4 + noise
    else:
        s = base + noise
    return np.abs(s)


def generate_traffic(n_packets: int = 80, n_timesteps: int = N_TIMESTEPS, seed: int = 42) -> list:
    """Generate synthetic IoMT network packets for quantum attack detection."""
    rng = np.random.RandomState(seed)
    packets = []
    for i in range(n_packets):
        if rng.random() < 0.58:
            atk, label = "normal", 0
        else:
            atk   = rng.choice(["dos", "spoof", "tamper", "replay", "ransomware"])
            label = 1

        feats = _FEAT_FNS[atk](rng) + rng.normal(0, 0.015, N_FEATURES)
        feats = np.clip(feats, 0, None)

        rate_s = _make_rate_series(atk, feats[0], rng, n_timesteps)
        byte_s = _make_byte_series(atk, feats[1], rng, n_timesteps)

        packets.append(NetworkPacket(
            packet_id=i, label=label, attack_type=atk,
            features=feats, rate_series=rate_s, byte_series=byte_s,
        ))
    return packets


def build_dataset(packets: list):
    """Return (X, y) from a list of NetworkPacket."""
    X = np.array([p.features for p in packets], dtype=float)
    y = np.array([p.label   for p in packets], dtype=int)
    return X, y


def extract_features(packet) -> np.ndarray:
    return packet.features.copy()
