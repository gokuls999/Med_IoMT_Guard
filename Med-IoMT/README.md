# Adaptive Trust-Aware Stacking IDS for IoMT

## Modules
- `data_loader.py`: Loads UNSW-NB15 and ToN-IoT CSVs and unifies labels.
- `preprocess.py`: Numeric normalization and categorical encoding.
- `stacking_model.py`: Trains stacking model with RF + GRU + XGB.
- `trust_engine.py`: Maintains adaptive per-device trust.
- `blockchain.py`: Appends prediction events to a SHA256-linked ledger.
- `realtime_engine.py`: Record-by-record real-time detection loop.
- `evaluation.py`: Accuracy, precision, recall, and F1 metrics.
- `experiments.py`: Baseline vs adaptive experiments, false positives, latency, plots, cross-dataset checks.
- `main.py`: End-to-end pipeline entry point.

## Run
```bash
pip install -r requirements.txt
python main.py --unsw_csv <path_to_unsw.csv> --ton_csv <path_to_ton.csv>
```

## Research Experiments
```bash
python experiments.py --unsw_csv <path_to_unsw.csv> --ton_csv <path_to_ton.csv> --sample_size 60000
```
Outputs under `research_outputs/`:
- `experiment_results.json`
- `metrics_comparison.png`
- `trust_evolution.png`
- `adaptive_outputs_sample.json`

## Demo UI (Client Presentation)
```bash
streamlit run demo_app.py
```
Use the app sections:
- Overview
- Evaluation
- Blockchain
- Real-Time Demo
- Presenter Notes

## Outputs
- `trained_model.pkl`
- `trust_state.json`
- `blockchain.json`
