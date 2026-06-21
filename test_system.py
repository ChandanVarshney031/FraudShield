import os
import unittest
import numpy as np

# Import modules to test
from model_engine import FraudModelEngine, FEATURES

class TestFraudDetectionSystem(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Initialize engine pointing to temporary subdirectory for testing assets
        cls.test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_assets")
        cls.engine = FraudModelEngine(data_dir=cls.test_dir)
        
    @classmethod
    def tearDownClass(cls):
        # Clean up test assets generated during testing
        for filename in ['fraud_model.pkl', 'scaler.pkl', 'metadata.pkl']:
            path = os.path.join(cls.test_dir, filename)
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
        if os.path.exists(cls.test_dir):
            try:
                os.rmdir(cls.test_dir)
            except Exception:
                pass

    def test_01_synthetic_data_generation(self):
        """Test that synthetic transaction data is generated with correct shape and fields."""
        df = self.engine.generate_synthetic_data(num_samples=100)
        
        self.assertEqual(len(df), 100)
        # Check that features and target are in columns
        for feature in FEATURES:
            self.assertIn(feature, df.columns)
        self.assertIn('is_fraud', df.columns)
        
        # Verify columns type
        self.assertTrue(np.issubdtype(df['amount'].dtype, np.number))
        self.assertTrue(np.issubdtype(df['is_fraud'].dtype, np.integer))

    def test_02_model_training(self):
        """Test model training and serialization to disk."""
        self.engine.train()
        
        # Verify files are created
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, 'fraud_model.pkl')))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, 'scaler.pkl')))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, 'metadata.pkl')))
        
        # Check model loaded back properly
        self.assertIsNotNone(self.engine.model)
        self.assertIsNotNone(self.engine.scaler)
        self.assertTrue(len(self.engine.feature_importances) > 0)

    def test_03_prediction_logic(self):
        """Test model prediction on low and high risk samples."""
        self.engine.load_model()
        
        # Low risk transaction profile
        low_risk_tx = {
            'amount': 25.0,
            'time_of_day': 12.0,  # mid day
            'card_holder_age': 35,
            'transaction_velocity': 1,
            'location_mismatch': 0,
            'device_risk': 0.1,  # desktop browser
            'category_risk': 0.15,  # grocery
            'historical_fraud_rate': 0.005
        }
        
        # High risk transaction profile
        high_risk_tx = {
            'amount': 3800.0,      # very high amount
            'time_of_day': 3.5,     # odd hours
            'card_holder_age': 45,
            'transaction_velocity': 6, # high velocity
            'location_mismatch': 1, # card country != IP country
            'device_risk': 0.9,     # proxy device
            'category_risk': 0.95,  # high risk Category
            'historical_fraud_rate': 0.45
        }
        
        res_low = self.engine.predict(low_risk_tx)
        res_high = self.engine.predict(high_risk_tx)
        
        # Verify outputs structure
        for res in [res_low, res_high]:
            self.assertIn("fraud_probability", res)
            self.assertIn("risk_level", res)
            self.assertIn("explanations", res)
            self.assertIn("risk_drivers", res)
            self.assertTrue(isinstance(res["explanations"], list))
            self.assertTrue(isinstance(res["risk_drivers"], dict))
            
        # Verify relative ordering of fraud probability
        self.assertLess(res_low["fraud_probability"], 30.0)
        self.assertEqual(res_low["risk_level"], "LOW")
        
        self.assertGreater(res_high["fraud_probability"], 70.0)
        self.assertEqual(res_high["risk_level"], "HIGH")

if __name__ == "__main__":
    unittest.main()
