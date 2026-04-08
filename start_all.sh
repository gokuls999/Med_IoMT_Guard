#!/bin/bash
# MedGuard IoMT - Start All 3 Terminals (Linux/Mac)
echo "============================================"
echo "  MedGuard IoMT System - Starting All 3 Terminals"
echo "============================================"

DIR="$(cd "$(dirname "$0")" && pwd)"

# Install dependencies
echo "[1/4] Installing dependencies..."
pip install -r "$DIR/requirements.txt" --quiet

# Initialize hospital database
echo "[2/4] Initializing hospital database..."
cd "$DIR/hospital_workflow_system"
mkdir -p outputs
python -c "from hospital_db import init_database; init_database()" 2>/dev/null

# Start all 3 terminals
echo "[3/4] Starting all terminals..."
cd "$DIR/Med-IoMT" && streamlit run demo_app.py --server.port 8501 --server.headless true &
cd "$DIR/hospital_workflow_system" && streamlit run dashboard.py --server.port 8502 --server.headless true &
cd "$DIR/iomt_attack_lab" && streamlit run app.py --server.port 8503 --server.headless true &

echo ""
echo "[4/4] All terminals launched!"
echo "============================================"
echo "  IDS Dashboard:    http://localhost:8501"
echo "  Hospital System:  http://localhost:8502"
echo "  Attack Lab:       http://localhost:8503"
echo "============================================"
wait
