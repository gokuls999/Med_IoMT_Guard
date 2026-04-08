"""Dataset loading utilities for IoMT IDS training."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import pandas as pd


LABEL_CANDIDATES = ["label", "Label", "attack", "Attack", "class", "Class", "type", "Type", "attack_cat"]
DEVICE_ID_CANDIDATES = ["device_id", "device", "srcip", "src_ip", "source_ip", "id"]


@dataclass
class DatasetBundle:
    data: pd.DataFrame
    label_column: str
    device_id_column: Optional[str]


def _find_first_existing(columns: Iterable[str], candidates: Iterable[str]) -> Optional[str]:
    colset = set(columns)
    for candidate in candidates:
        if candidate in colset:
            return candidate
    return None


def _infer_binary_label(raw: pd.Series) -> pd.Series:

    if pd.api.types.is_numeric_dtype(raw):
        return (raw.astype(float) > 0).astype(int)

    coerced = pd.to_numeric(raw, errors="coerce")
    if coerced.notna().mean() >= 0.5:
        return (coerced.fillna(0).astype(float) > 0).astype(int)

    lowered = raw.astype(str).str.strip().str.lower()
    normal_tokens = {"0", "0.0", "0.00", "normal", "benign", "false", "no", "clean", "non-attack"}
    return (~lowered.isin(normal_tokens)).astype(int)


def load_single_dataset(csv_path: str) -> pd.DataFrame:
    frame = pd.read_csv(csv_path)
    frame.columns = [str(c).strip() for c in frame.columns]
    return frame


def load_and_merge_datasets(unsw_csv_path: str, ton_csv_path: str, label_col: Optional[str] = None) -> DatasetBundle:
    unsw = load_single_dataset(unsw_csv_path)
    ton = load_single_dataset(ton_csv_path)
    unsw["dataset_source"] = "unsw_nb15"
    ton["dataset_source"] = "ton_iot"

    merged = pd.concat([unsw, ton], axis=0, ignore_index=True, sort=False)

    if label_col and label_col not in merged.columns:
        raise ValueError(f"Provided label column '{label_col}' was not found in merged data.")

    available_label_cols = [c for c in LABEL_CANDIDATES if c in merged.columns]
    if label_col:
        raw_label = merged[label_col]
    elif available_label_cols:
        # Combine multiple possible label columns row-wise (e.g., UNSW uses `label`, ToN-IoT uses `Label`).
        raw_label = merged[available_label_cols].bfill(axis=1).iloc[:, 0]
    else:
        raise ValueError(
            "Could not infer label column. Pass label_col explicitly from your dataset schema."
        )

    merged = merged.copy()
    merged["label_bin"] = _infer_binary_label(raw_label)

    device_col = _find_first_existing(merged.columns, DEVICE_ID_CANDIDATES)
    if not device_col:
        device_col = "device_id"
        merged[device_col] = "unknown_device"

    return DatasetBundle(data=merged, label_column="label_bin", device_id_column=device_col)
