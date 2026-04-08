"""Feature preprocessing: encoding + normalization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


DROP_COLUMNS = {
    "label_bin",
    "label",
    "Label",
    "attack_cat",
    "Attack",
    "attack",
    "class",
    "Class",
    "type",
    "Type",
    "dataset_source",
}


@dataclass
class PreprocessBundle:
    preprocessor: ColumnTransformer
    feature_columns: List[str]


def build_feature_frame(
    frame: pd.DataFrame,
    label_col: str = "label_bin",
    drop_extra: Optional[Sequence[str]] = None,
) -> tuple[pd.DataFrame, np.ndarray, list[str]]:
    drop_cols = set(DROP_COLUMNS)
    drop_cols.add(label_col)
    if drop_extra:
        drop_cols.update(drop_extra)

    feature_columns = [c for c in frame.columns if c not in drop_cols]
    if not feature_columns:
        raise ValueError("No feature columns remained after dropping label columns.")

    X = frame[feature_columns].copy()
    y = frame[label_col].astype(int).to_numpy()
    return X, y, feature_columns


def make_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    numeric_cols = X.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical_cols = [c for c in X.columns if c not in numeric_cols]

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, numeric_cols),
            ("cat", categorical_pipeline, categorical_cols),
        ],
        remainder="drop",
    )


def fit_preprocessor(X: pd.DataFrame) -> PreprocessBundle:
    preprocessor = make_preprocessor(X)
    preprocessor.fit(X)
    return PreprocessBundle(preprocessor=preprocessor, feature_columns=X.columns.tolist())


def transform_with_preprocessor(
    frame: pd.DataFrame,
    preprocess_bundle: PreprocessBundle,
) -> np.ndarray:
    # Keep training-time schema stable and fill missing columns for inference.
    X = frame.copy()
    for col in preprocess_bundle.feature_columns:
        if col not in X.columns:
            X[col] = np.nan
    X = X[preprocess_bundle.feature_columns]
    return preprocess_bundle.preprocessor.transform(X)
