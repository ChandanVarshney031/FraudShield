from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import os
import uvicorn
from typing import List, Dict, Any, Optional

# Import local modules
from model_engine import FraudModelEngine
from simulator import TransactionSimulator

app = FastAPI(title="Real-Time Fraud Detection Engine", version="1.0.0")

# Enable CORS for frontend hosting
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=False,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# Initialize models and simulator
model_engine = FraudModelEngine()
simulator = TransactionSimulator()

# Active configurations in memory
rules_config = {
    "block_high_amount": True,
    "block_high_amount_threshold": 5000.0,
    "block_location_mismatch": False,
    "block_high_velocity": True,
    "block_high_velocity_threshold": 4,
    "block_high_risk_device": False,
    "min_ml_threshold": 75.0, # Automatically block if ML score >= 75%
}

simulator_config = {
    "fraud_probability": 0.08,
    "active": False,
    "interval_ms": 1500
}

# Session database of transactions (in-memory)
# Format of records: {transaction_data, analysis_result, decision, final_status}
transaction_history: List[Dict[str, Any]] = []
MAX_HISTORY_SIZE = 200

# Performance metrics variables
metrics_counters = {
    "true_positives": 0,   # Simulated fraud successfully BLOCKED
    "false_positives": 0,  # Simulated normal transaction BLOCKED
    "true_negatives": 0,   # Simulated normal transaction APPROVED
    "false_negatives": 0,  # Simulated fraud transaction APPROVED
    "suspicious_reviews": 0, # Transactions flagged for manual review
    "total_blocked_amount": 0.0,
    "total_processed_amount": 0.0
}

# Pydantic schemas
class TransactionInput(BaseModel):
    amount: float = Field(..., example=250.0)
    time_of_day: float = Field(..., example=14.5)
    card_holder_age: int = Field(..., example=34)
    transaction_velocity: int = Field(..., example=1)
    location_mismatch: int = Field(..., example=0)
    device_risk: float = Field(..., example=0.2)
    category_risk: float = Field(..., example=0.15)
    historical_fraud_rate: float = Field(..., example=0.01)
    
    # Metadata for display
    cardholder_name: str = "Manual Input"
    card_number_masked: str = "4111 **** **** 1111"
    card_network: str = "Visa"
    card_country: str = "US"
    ip_country: str = "US"
    category: str = "General Retail"
    device: str = "Desktop (Chrome/Windows)"
    simulated_fraud: int = 0

class RulesConfigUpdate(BaseModel):
    block_high_amount: Optional[bool] = None
    block_high_amount_threshold: Optional[float] = None
    block_location_mismatch: Optional[bool] = None
    block_high_velocity: Optional[bool] = None
    block_high_velocity_threshold: Optional[int] = None
    block_high_risk_device: Optional[bool] = None
    min_ml_threshold: Optional[float] = None

class SimulatorConfigUpdate(BaseModel):
    fraud_probability: Optional[float] = None
    active: Optional[bool] = None
    interval_ms: Optional[int] = None

@app.on_event("startup")
def startup_event():
    """Train or load the Machine Learning model on start."""
    print("Initializing Fraud Detection engine...")
    model_engine.load_model()
    print("Initialization complete.")

def evaluate_transaction_hybrid(tx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates a transaction using both the rule-based engine and the ML model.
    """
    # 1. Run Machine Learning predictions
    ml_result = model_engine.predict(tx)
    ml_score = ml_result["fraud_probability"]
    
    # 2. Check rule overrides
    rule_hits = []
    
    if rules_config["block_high_amount"] and tx["amount"] >= rules_config["block_high_amount_threshold"]:
        rule_hits.append(f"Transaction amount (${tx['amount']:,.2f}) exceeds rule limit of (${rules_config['block_high_amount_threshold']:,.2f})")
        
    if rules_config["block_location_mismatch"] and tx["location_mismatch"] == 1:
        rule_hits.append(f"Geographic mismatch detected (Card: {tx['card_country']}, IP: {tx['ip_country']})")
        
    if rules_config["block_high_velocity"] and tx["transaction_velocity"] >= rules_config["block_high_velocity_threshold"]:
        rule_hits.append(f"Velocity threshold breached: {tx['transaction_velocity']} transactions in 15 min (limit: {rules_config['block_high_velocity_threshold']})")
        
    if rules_config["block_high_risk_device"] and tx["device_risk"] >= 0.8:
        rule_hits.append(f"High risk device configuration flagged: {tx['device']}")
        
    # 3. Determine final status
    decision_reason = ""
    rule_blocked = len(rule_hits) > 0
    ml_blocked = ml_score >= rules_config["min_ml_threshold"]
    
    if rule_blocked:
        status = "BLOCKED"
        decision_reason = "Rule-based Auto-Block: " + "; ".join(rule_hits)
    elif ml_blocked:
        status = "BLOCKED"
        decision_reason = f"ML Engine Auto-Block: Risk Score ({ml_score}%) exceeds block threshold ({rules_config['min_ml_threshold']}%)"
    elif ml_score >= 30.0:
        status = "REVIEW"
        decision_reason = f"Flagged for Review: Risk Score ({ml_score}%) is suspicious (30% - {rules_config['min_ml_threshold']}%)"
    else:
        status = "APPROVED"
        decision_reason = f"Auto-Approved: Transaction within safe thresholds (Risk Score: {ml_score}%)"
        
    # Combine results
    evaluation = {
        "status": status,
        "decision_reason": decision_reason,
        "rule_hits": rule_hits,
        "ml_score": ml_score,
        "risk_level": ml_result["risk_level"],
        "explanations": ml_result["explanations"],
        "risk_drivers": ml_result["risk_drivers"]
    }
    
    # 4. Update metrics counters based on simulation target (if simulated)
    simulated_fraud = tx.get("simulated_fraud", 0)
    amount = tx.get("amount", 0.0)
    
    metrics_counters["total_processed_amount"] += amount
    
    if status == "BLOCKED":
        metrics_counters["total_blocked_amount"] += amount
        if simulated_fraud == 1:
            metrics_counters["true_positives"] += 1
        else:
            metrics_counters["false_positives"] += 1
    elif status == "REVIEW":
        metrics_counters["suspicious_reviews"] += 1
        # Let's count reviews as approved in the base stats, or separate
        if simulated_fraud == 1:
            metrics_counters["false_negatives"] += 1
        else:
            metrics_counters["true_negatives"] += 1
    else:  # APPROVED
        if simulated_fraud == 1:
            metrics_counters["false_negatives"] += 1
        else:
            metrics_counters["true_negatives"] += 1
            
    return evaluation

@app.get("/api/rules")
def get_rules():
    return rules_config

@app.post("/api/rules")
def update_rules(update: RulesConfigUpdate):
    for key, value in update.dict(exclude_unset=True).items():
        rules_config[key] = value
    return {"message": "Rules updated successfully", "rules": rules_config}

@app.get("/api/simulator/config")
def get_simulator_config():
    return simulator_config

@app.post("/api/simulator/config")
def update_simulator_config(update: SimulatorConfigUpdate):
    for key, value in update.dict(exclude_unset=True).items():
        simulator_config[key] = value
    return {"message": "Simulator config updated", "config": simulator_config}

@app.post("/api/predict")
def predict_transaction(tx_input: TransactionInput):
    tx_data = tx_input.dict()
    eval_result = evaluate_transaction_hybrid(tx_data)
    
    record = {
        "tx": tx_data,
        "evaluation": eval_result
    }
    
    # Store in history
    transaction_history.insert(0, record)
    if len(transaction_history) > MAX_HISTORY_SIZE:
        transaction_history.pop()
        
    return record

@app.get("/api/simulate/next")
def simulate_next(force_fraud: bool = False):
    """Simulates a transaction, scores it, saves it to history and returns the evaluation."""
    tx_data = simulator.generate_transaction(
        config_fraud_prob=simulator_config["fraud_probability"],
        force_fraud=force_fraud
    )
    
    eval_result = evaluate_transaction_hybrid(tx_data)
    
    record = {
        "tx": tx_data,
        "evaluation": eval_result
    }
    
    transaction_history.insert(0, record)
    if len(transaction_history) > MAX_HISTORY_SIZE:
        transaction_history.pop()
        
    return record

@app.get("/api/transactions")
def get_transactions(limit: int = 50):
    return transaction_history[:limit]

@app.get("/api/metrics")
def get_metrics():
    tp = metrics_counters["true_positives"]
    fp = metrics_counters["false_positives"]
    tn = metrics_counters["true_negatives"]
    fn = metrics_counters["false_negatives"]
    
    # Calculate statistical metrics
    accuracy = (tp + tn) / (tp + fp + tn + fn) if (tp + fp + tn + fn) > 0 else 1.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    # Calculate detection rate
    alert_rate = (tp + fp) / (tp + fp + tn + fn) if (tp + fp + tn + fn) > 0 else 0.0
    
    return {
        "accuracy": round(accuracy * 100, 2),
        "precision": round(precision * 100, 2),
        "recall": round(recall * 100, 2),
        "f1_score": round(f1_score * 100, 2),
        "alert_rate": round(alert_rate * 100, 2),
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "suspicious_reviews": metrics_counters["suspicious_reviews"],
        "total_blocked_amount": round(metrics_counters["total_blocked_amount"], 2),
        "total_processed_amount": round(metrics_counters["total_processed_amount"], 2),
        "fraud_savings_usd": round(metrics_counters["total_blocked_amount"], 2) # Saved money is what we blocked
    }

@app.post("/api/metrics/reset")
def reset_metrics():
    for key in metrics_counters:
        if isinstance(metrics_counters[key], float):
            metrics_counters[key] = 0.0
        else:
            metrics_counters[key] = 0
    # Clear history too
    transaction_history.clear()
    return {"message": "Metrics and history reset successfully"}

@app.post("/api/retrain")
def retrain_model():
    """Forces retraining of the model with new synthetic data."""
    try:
        model_engine.train()
        return {"message": "Model retrained successfully", "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrain: {str(e)}")

# Mount the static directory
static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if not os.path.exists(static_path):
    os.makedirs(static_path)

# HTML fallback to host the app
@app.get("/", response_class=HTMLResponse)
def index_fallback():
    index_file = os.path.join(static_path, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Frontend is under construction! Check back soon.</h1>")

app.mount("/", StaticFiles(directory=static_path), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
