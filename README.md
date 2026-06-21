# GuardianAI: Hybrid ML Real-Time Fraud Detection Sandbox

GuardianAI is a full-stack, real-time credit card fraud detection system designed for online transactions. It combines a **Machine Learning engine (Random Forest Classifier)** and a **Rule-Based Override Engine** to classify, review, or block suspicious payments on the fly. 

To provide transparency in automated decision-making, the system features **Explainable AI (XAI)** metrics (simulating local SHAP values) that outline feature-level risk drivers for every transaction.

---

## Key Features

1. **Hybrid Risk Engine**:
   - **Machine Learning**: Random Forest Classifier trained on simulated transaction metadata (amount, velocity, category, age, device, and historical risk profiles).
   - **Enterprise Rules overrides**: Quick toggles to immediately block transactions based on hard limits (e.g., amount limit, billing/IP location mismatch, high-frequency velocity, or Tor proxies).
2. **Interactive Payment Terminal Sandbox**:
   - Manually enter transaction data (card details, amounts, locations, velocity) to see how the system classifies risk in real time.
3. **Automated Ticker Simulator**:
   - Toggle real-time transaction streaming with adjustable frequency and fraud ratio sliders.
4. **Interactive Dashboard & XAI Analytics**:
   - Glassmorphic dark-theme UI with glowing metric status indicators.
   - Dynamic doughnut distribution charts.
   - Slidable Deep-Dive auditor drawer detailing rule hits, ML probabilities, and horizontal bar charts of local risk importances (drivers).
5. **Model Retraining Portal**:
   - Re-train the Random Forest model dynamically from the interface using updated transaction vectors.

---

## Tech Stack

- **Backend**: Python 3.14, FastAPI (Web server), Scikit-Learn (Random Forest), Pandas, NumPy.
- **Frontend**: HTML5, Vanilla CSS3 (Custom Glassmorphism layout), Vanilla Javascript (ES6), Chart.js (CDN) for animated graphs, Lucide Icons.

---

## Directory Structure

```
Fraud_Detection/
├── main.py                # FastAPI web server and API layer
├── model_engine.py        # Machine Learning training & predict logic
├── simulator.py           # Real-time transaction streamer
├── test_system.py         # Automated unit test suite
├── requirements.txt       # Python dependencies
├── static/                # Frontend web resources
│   ├── index.html         # Dashboard UI HTML
│   ├── styles.css         # Glassmorphism dark-theme CSS
│   └── app.js             # Real-time websocket/rest controller
└── README.md              # Project documentation
```

---

## API Documentation

FastAPI automatically generates an interactive Swagger UI. Once the server is running, navigate to `http://127.0.0.1:8000/docs` to test endpoints:

- `GET /api/rules` / `POST /api/rules`: View/Update rules override configuration.
- `GET /api/simulator/config` / `POST /api/simulator/config`: View/Update live transaction generator configurations.
- `POST /api/predict`: Evaluate a custom transaction.
- `GET /api/simulate/next`: Simulates a transaction, evaluates it, adds it to the audit log history, and returns the result.
- `GET /api/transactions`: Get recent transactions feed.
- `GET /api/metrics`: Retrieve session performance metrics (Accuracy, Precision, Recall, Financial Shield savings).
- `POST /api/retrain`: Trigger model retraining.
- `POST /api/metrics/reset`: Clear current session audit logs and metrics.

---

## Running the Project

### 1. Prerequisites
Ensure you have **Python 3.10+** (Python 3.14 tested) and **Node.js** (for dev commands if needed, though running Python is enough).

### 2. Setup and Install Dependencies
Navigate to the project root directory and set up a virtual environment:

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# macOS/Linux:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Run the Automated Tests
Before starting the server, you can run the test suite to verify the ML classifier and data pipelines are correctly configured:

```powershell
python test_system.py
```

### 4. Start the Application Server
Run the FastAPI application locally:

```powershell
python main.py
```

Once launched, the terminal will indicate the server is running at:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

Open this URL in any modern web browser to access the interactive GuardianAI dashboard.
