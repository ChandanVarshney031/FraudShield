import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import os

# Define feature names used in training
FEATURES = [
    'amount',
    'time_of_day',
    'card_holder_age',
    'transaction_velocity',
    'location_mismatch',
    'device_risk',
    'category_risk',
    'historical_fraud_rate'
]

class FraudModelEngine:
    def __init__(self, data_dir=None):
        self.model = None
        self.scaler = None
        self.feature_means = {}
        self.feature_stds = {}
        self.feature_importances = {}
        self.data_dir = data_dir or os.path.dirname(os.path.abspath(__file__))
        
    def generate_synthetic_data(self, num_samples=10000):
        """Generates synthetic credit card transaction data with fraud patterns."""
        np.random.seed(42)
        
        # 1. Base features
        amount = np.random.exponential(scale=80, size=num_samples)  # most transactions are small
        # Add some huge transactions
        large_tx_idx = np.random.choice(num_samples, size=int(num_samples * 0.05), replace=False)
        amount[large_tx_idx] = np.random.uniform(200, 5000, size=len(large_tx_idx))
        
        time_of_day = np.random.uniform(0, 24, size=num_samples)
        card_holder_age = np.random.randint(18, 90, size=num_samples)
        
        # Velocity (number of transactions in last 15 min)
        transaction_velocity = np.random.poisson(lam=0.6, size=num_samples)
        # Add high velocity spikes
        high_vel_idx = np.random.choice(num_samples, size=int(num_samples * 0.03), replace=False)
        transaction_velocity[high_vel_idx] = np.random.randint(4, 10, size=len(high_vel_idx))
        
        location_mismatch = np.random.choice([0, 1], p=[0.95, 0.05], size=num_samples)
        
        # Device risk: Desktop (0.1), Mobile (0.3), Tablet (0.2), Tor/Proxy/Unknown (0.9)
        device_types = np.random.choice([0.1, 0.3, 0.2, 0.9], p=[0.5, 0.4, 0.08, 0.02], size=num_samples)
        
        # Category risk: Grocery (0.15), Dining (0.2), Electronics (0.75), Travel (0.8), Cash Transfer (0.95)
        category_risks = np.random.choice([0.15, 0.2, 0.75, 0.8, 0.95], p=[0.4, 0.3, 0.15, 0.1, 0.05], size=num_samples)
        
        historical_fraud_rate = np.random.beta(a=1, b=99, size=num_samples)  # mostly near 0%
        # High historical risk for some users
        high_risk_users = np.random.choice(num_samples, size=int(num_samples * 0.02), replace=False)
        historical_fraud_rate[high_risk_users] = np.random.uniform(0.1, 0.8, size=len(high_risk_users))
        
        df = pd.DataFrame({
            'amount': amount,
            'time_of_day': time_of_day,
            'card_holder_age': card_holder_age,
            'transaction_velocity': transaction_velocity,
            'location_mismatch': location_mismatch,
            'device_risk': device_types,
            'category_risk': category_risks,
            'historical_fraud_rate': historical_fraud_rate
        })
        
        # 2. Assign fraud targets based on heuristics (to train ML model)
        # Baseline probability of fraud: 1.5%
        fraud_prob = np.full(num_samples, 0.015)
        
        # Rule 1: High transaction amount + high-risk device or category
        fraud_prob += np.where((df['amount'] > 1200) & (df['category_risk'] >= 0.75), 0.35, 0.0)
        
        # Rule 2: Location mismatch + high amount
        fraud_prob += np.where((df['location_mismatch'] == 1) & (df['amount'] > 400), 0.45, 0.0)
        
        # Rule 3: High transaction velocity
        fraud_prob += np.where(df['transaction_velocity'] >= 4, 0.55, 0.0)
        
        # Rule 4: High historical fraud rate + medium-to-high amount
        fraud_prob += np.where((df['historical_fraud_rate'] > 0.15) & (df['amount'] > 100), 0.30, 0.0)
        
        # Rule 5: Odd hour (1 AM to 5 AM) + high amount + location mismatch
        odd_hours = (df['time_of_day'] >= 1.0) & (df['time_of_day'] <= 5.0)
        fraud_prob += np.where(odd_hours & (df['amount'] > 500) & (df['location_mismatch'] == 1), 0.50, 0.0)
        
        # Cap probabilities at 0.98
        fraud_prob = np.clip(fraud_prob, 0.0, 0.98)
        
        # Generate final target
        # If fraud probability is extremely high, make it fraud deterministically to keep clean boundaries
        is_fraud = np.where(fraud_prob > 0.75, 1, np.random.binomial(1, fraud_prob))
        df['is_fraud'] = is_fraud
        
        return df
        
    def train(self):
        """Generates data and trains the RandomForestClassifier."""
        print("Generating synthetic dataset...")
        df = self.generate_synthetic_data(12000)
        
        X = df[FEATURES]
        y = df['is_fraud']
        
        # Record feature statistics for local explanation normalization
        for col in FEATURES:
            self.feature_means[col] = float(X[col].mean())
            self.feature_stds[col] = float(X[col].std()) if X[col].std() > 0 else 1.0
            
        print("Training Random Forest model...")
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=12,
            random_state=42,
            class_weight='balanced'
        )
        self.model.fit(X_scaled, y)
        
        # Save feature importances
        for name, importance in zip(FEATURES, self.model.feature_importances_):
            self.feature_importances[name] = float(importance)
            
        print("Model training complete.")
        
        # Save assets to disk
        os.makedirs(self.data_dir, exist_ok=True)
        joblib.dump(self.model, os.path.join(self.data_dir, 'fraud_model.pkl'))
        joblib.dump(self.scaler, os.path.join(self.data_dir, 'scaler.pkl'))
        joblib.dump({
            'means': self.feature_means,
            'stds': self.feature_stds,
            'importances': self.feature_importances
        }, os.path.join(self.data_dir, 'metadata.pkl'))
        
    def load_model(self):
        """Loads a pre-trained model and metadata if available, otherwise trains a new one."""
        model_path = os.path.join(self.data_dir, 'fraud_model.pkl')
        scaler_path = os.path.join(self.data_dir, 'scaler.pkl')
        meta_path = os.path.join(self.data_dir, 'metadata.pkl')
        
        if os.path.exists(model_path) and os.path.exists(scaler_path) and os.path.exists(meta_path):
            try:
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                meta = joblib.load(meta_path)
                self.feature_means = meta['means']
                self.feature_stds = meta['stds']
                self.feature_importances = meta['importances']
                print("Model loaded successfully from cache.")
                return True
            except Exception as e:
                print(f"Error loading model: {e}. Retraining...")
                
        self.train()
        return True

    def predict(self, tx_dict):
        """
        Predicts fraud probability for a single transaction dictionary.
        Input format: {
            'amount': float,
            'time_of_day': float (0-23),
            'card_holder_age': int,
            'transaction_velocity': int,
            'location_mismatch': int (0 or 1),
            'device_risk': float (risk rating),
            'category_risk': float (risk rating),
            'historical_fraud_rate': float
        }
        Returns:
            dict containing probability (0-100), risk_level, and explanations (local risk drivers)
        """
        if self.model is None or self.scaler is None:
            self.load_model()
            
        # Parse transaction features
        tx_features = [tx_dict.get(feat, 0.0) for feat in FEATURES]
        df_tx = pd.DataFrame([tx_features], columns=FEATURES)
        
        # Scale and predict
        scaled_tx = self.scaler.transform(df_tx)
        prob = self.model.predict_proba(scaled_tx)[0][1]
        
        # Generate explanations (Local Risk Drivers)
        # Compute how far this feature is from the norm (standardized deviation)
        # and multiply by feature importance to simulate local SHAP values.
        explanations = []
        local_contributions = {}
        
        for col in FEATURES:
            val = tx_dict.get(col, 0.0)
            mean = self.feature_means.get(col, 0.0)
            std = self.feature_stds.get(col, 1.0)
            importance = self.feature_importances.get(col, 0.1)
            
            # Distance from mean in terms of standard deviations
            z_score = (val - mean) / std
            
            # Compute raw local contribution (only positive deviations represent risk drivers)
            # For time of day, absolute deviation is what matters (abnormal hour compared to average)
            if col == 'time_of_day':
                # Night/late-night hours (e.g. 1am-5am) are higher risk. Let's see if time is odd:
                is_odd_hour = 1.0 <= val <= 5.0
                dev = 2.0 if is_odd_hour else -0.5
            elif col == 'location_mismatch':
                dev = 3.5 if val == 1 else -0.2
            else:
                dev = z_score
                
            contribution = dev * importance
            local_contributions[col] = float(contribution)
            
        # Format human readable explanations
        if tx_dict.get('amount', 0.0) > 1000:
            explanations.append(f"High transaction amount (${tx_dict['amount']:,.2f}) deviates significantly from average.")
        if 1.0 <= tx_dict.get('time_of_day', 12.0) <= 5.0:
            explanations.append(f"Transaction occurred during high-risk hours (1:00 AM - 5:00 AM).")
        if tx_dict.get('transaction_velocity', 0) >= 3:
            explanations.append(f"High frequency of transactions ({tx_dict['transaction_velocity']} txs in last 15 min).")
        if tx_dict.get('location_mismatch', 0) == 1:
            explanations.append(f"Geographic mismatch between billing card country and transaction IP address.")
        if tx_dict.get('device_risk', 0.0) >= 0.75:
            explanations.append(f"Transaction originated from high-risk device or network configuration (e.g. VPN/Tor).")
        if tx_dict.get('category_risk', 0.0) >= 0.75:
            explanations.append(f"Merchant category is classified as high-risk (e.g. instant cash transfer or high-end electronics).")
        if tx_dict.get('historical_fraud_rate', 0.0) > 0.1:
            explanations.append(f"Card has elevated historical fraud risk ({tx_dict['historical_fraud_rate']*100:.1f}% flag rate).")
            
        if not explanations:
            explanations.append("Transaction profile lies within standard cardholder behaviors.")
            
        # Normalize local contributions for visualization (relative scaling)
        # Sum of positive contributions to make visual display of risk breakdown
        total_risk_contrib = sum(max(0, c) for c in local_contributions.values())
        normalized_drivers = {}
        if total_risk_contrib > 0:
            for k, v in local_contributions.items():
                normalized_drivers[k] = float(max(0, v) / total_risk_contrib)
        else:
            # If all are normal, assign equal minor weight to amount / time
            for k in FEATURES:
                normalized_drivers[k] = 1.0 / len(FEATURES)
                
        # Classify risk level
        prob_pct = float(prob * 100)
        if prob_pct < 30:
            risk_level = "LOW"
        elif prob_pct < 70:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"
            
        return {
            "fraud_probability": round(prob_pct, 2),
            "risk_level": risk_level,
            "explanations": explanations,
            "risk_drivers": normalized_drivers
        }

if __name__ == "__main__":
    # Test execution
    engine = FraudModelEngine()
    engine.train()
    
    test_tx = {
        'amount': 2500.0,
        'time_of_day': 3.5,
        'card_holder_age': 45,
        'transaction_velocity': 5,
        'location_mismatch': 1,
        'device_risk': 0.9,
        'category_risk': 0.95,
        'historical_fraud_rate': 0.15
    }
    
    result = engine.predict(test_tx)
    print("\nTest Prediction Result:")
    print(f"Probability: {result['fraud_probability']}%")
    print(f"Risk Level: {result['risk_level']}")
    print(f"Drivers: {result['risk_drivers']}")
    print("Explanations:")
    for exp in result['explanations']:
        print(f" - {exp}")
