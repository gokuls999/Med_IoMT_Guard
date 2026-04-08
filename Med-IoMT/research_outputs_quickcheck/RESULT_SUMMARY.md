# Research Results Summary

## Run Configuration
- sample_size: 10000
- test_size: 0.2
- base_threshold: 0.5
- alpha: 0.08
- beta: 0.03
- random_state: 42

## Variant Comparison
- Baseline static threshold:
  - accuracy: 0.9460
  - precision: 0.9516
  - recall: 0.9698
  - f1: 0.9606
  - false_positive_rate: 0.1044
  - latency_mean_ms (batch predict_proba): 65.85
- Adaptive threshold only:
  - accuracy: 0.9455
  - precision: 0.9509
  - recall: 0.9698
  - f1: 0.9603
  - false_positive_rate: 0.1059
  - latency_mean_ms (stream): 56.28
- Adaptive threshold + trust-weighted score:
  - accuracy: 0.5815
  - precision: 0.9762
  - recall: 0.3932
  - f1: 0.5606
  - false_positive_rate: 0.0202
  - latency_mean_ms (stream): 56.45

## Interpretation
- The trust-weighted variant substantially reduces false positives, but sharply reduces recall.
- For safety-critical IDS deployments, this precision/recall trade-off should be tuned with threshold and trust update parameters before production use.
- Cross-dataset transfer performance remains weak, indicating domain shift and feature mismatch between UNSW and ToN-IoT.

## Generated Files
- `experiment_results.json`
- `metrics_comparison.png`
- `trust_evolution.png`
- `adaptive_outputs_sample.json`
