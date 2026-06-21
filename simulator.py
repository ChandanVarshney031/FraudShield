import random
import time
import uuid

# Configuration and categories for synthetic transactions
NAMES = [
    "John Doe", "Sarah Jenkins", "Michael Chen", "Emily Rodriguez", "David Kim",
    "Jessica Taylor", "James Wilson", "Sophia Martinez", "Robert Kovacs", "Anna Novak",
    "Li Wei", "Carlos Santana", "Amina Diop", "Yuki Sato", "Alex Mercer",
    "Elena Petrova", "Daniel Brown", "Chloe Lefevre", "Omar Al-Fayed", "Priya Patel"
]

CARD_NETWORKS = ["Visa", "Mastercard", "Amex", "Discover"]

COUNTRIES = ["US", "GB", "DE", "FR", "IN", "BR", "CA", "JP", "AU", "SG", "ZA", "RU", "CN"]

CATEGORIES = [
    # (Category Name, Base Fraud Risk [0-1])
    ("Grocery Store", 0.15),
    ("Restaurant / Dining", 0.20),
    ("Gas Station", 0.35),
    ("Apparel / Fashion", 0.40),
    ("Electronics Store", 0.75),
    ("Travel Agency / Flights", 0.80),
    ("Digital Wallet Transfer", 0.95)
]

DEVICES = [
    # (Device Type, Base Fraud Risk [0-1])
    ("Desktop (Chrome/Windows)", 0.10),
    ("Mobile App (iOS)", 0.20),
    ("Mobile Safari (Android)", 0.35),
    ("Tablet Browser", 0.20),
    ("Unknown / Tor Network Proxy", 0.90)
]

class TransactionSimulator:
    def __init__(self):
        # Keep track of card velocity in memory: {card_number: [timestamps]}
        self.velocity_history = {}
        # Keep track of historical fraud rate in memory: {card_number: (flags, total)}
        self.card_histories = {}
        
    def _clean_velocity_history(self, card_no, current_time):
        """Remove timestamps older than 15 minutes."""
        if card_no in self.velocity_history:
            # 15 minutes = 900 seconds
            self.velocity_history[card_no] = [
                t for t in self.velocity_history[card_no]
                if current_time - t < 900
            ]
            
    def generate_transaction(self, config_fraud_prob=0.05, force_fraud=False):
        """
        Generates a single synthetic transaction.
        - config_fraud_prob: general probability (0 to 1) that this transaction should be simulated as fraud.
        - force_fraud: force this transaction to trigger fraud characteristics.
        """
        current_time = time.time()
        
        # Decide if this transaction is simulated to be fraud
        is_fraudulent_intent = force_fraud or (random.random() < config_fraud_prob)
        
        # Select or create cardholder profile
        name = random.choice(NAMES)
        
        # Generate stable card details for the cardholder
        # We derive a card number hash-like from the name to keep it semi-consistent, 
        # or generate a random one and save it.
        random.seed(name)
        card_no = f"4{random.randint(1000, 9999)}{random.randint(1000, 9999)}{random.randint(1000, 9999)}{random.randint(1000, 9999)}"
        card_network = random.choice(CARD_NETWORKS)
        card_country = random.choice(COUNTRIES)
        random.seed() # reset seed
        
        # Track velocity
        self._clean_velocity_history(card_no, current_time)
        if card_no not in self.velocity_history:
            self.velocity_history[card_no] = []
        self.velocity_history[card_no].append(current_time)
        
        # Determine velocity variable
        if is_fraudulent_intent and random.random() < 0.6:
            # High velocity fraud spike: inject multiple mock timestamps
            velocity = random.randint(4, 8)
            self.velocity_history[card_no].extend([current_time - random.randint(1, 60) for _ in range(velocity - 1)])
        else:
            velocity = len(self.velocity_history[card_no])
            
        # Determine amount
        if is_fraudulent_intent:
            # Fraud transactions are generally higher amount
            amount = round(random.exponential(scale=800) + 150, 2)
            if amount > 10000:
                amount = round(random.uniform(500, 5000), 2)
        else:
            # Normal amount
            amount = round(random.exponential(scale=60) + 5.0, 2)
            if random.random() < 0.05: # occasional high normal transaction
                amount = round(random.uniform(150, 800), 2)
                
        # Card country vs IP Country
        ip_country = card_country
        location_mismatch = 0
        if is_fraudulent_intent and random.random() < 0.7:
            # Geographic spoofing
            ip_country = random.choice([c for c in COUNTRIES if c != card_country])
            location_mismatch = 1
        elif random.random() < 0.03: # 3% chance of normal travel mismatch
            ip_country = random.choice([c for c in COUNTRIES if c != card_country])
            location_mismatch = 1
            
        # Device
        if is_fraudulent_intent and random.random() < 0.4:
            device_name, device_risk = DEVICES[-1]  # Tor/Proxy
        else:
            device_name, device_risk = random.choices(DEVICES, weights=[50, 35, 10, 4, 1])[0]
            
        # Merchant category
        if is_fraudulent_intent and random.random() < 0.6:
            # Target liquid assets
            category_name, category_risk = random.choice(CATEGORIES[4:])
        else:
            category_name, category_risk = random.choices(CATEGORIES, weights=[35, 30, 15, 10, 6, 3, 1])[0]
            
        # Cardholder historical fraud rates
        if card_no not in self.card_histories:
            # Set baseline historical fraud
            if is_fraudulent_intent:
                self.card_histories[card_no] = [random.randint(0, 2), random.randint(10, 50)]
            else:
                self.card_histories[card_no] = [0, random.randint(5, 40)]
        
        # update card history
        if is_fraudulent_intent:
            self.card_histories[card_no][0] += 1
        self.card_histories[card_no][1] += 1
        
        hist_fraud_numerator, hist_fraud_denominator = self.card_histories[card_no]
        historical_fraud_rate = hist_fraud_numerator / hist_fraud_denominator
        
        # Time of day
        if is_fraudulent_intent and random.random() < 0.4:
            time_of_day = random.uniform(1.0, 4.9)  # midnight/early morning fraud
        else:
            # normal active hours distribution (peaks around mid-day)
            time_of_day = (random.normalvariate(14, 4)) % 24
            
        # Unique transaction identifier
        tx_id = str(uuid.uuid4())[:13].replace("-", "")
        
        return {
            # Display metadata
            "id": tx_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_time)),
            "cardholder_name": name,
            "card_number_masked": f"{card_no[:4]} **** **** {card_no[-4:]}",
            "card_network": card_network,
            "card_country": card_country,
            "ip_country": ip_country,
            "category": category_name,
            "device": device_name,
            
            # Numeric inputs for model
            "amount": amount,
            "time_of_day": round(time_of_day, 2),
            "card_holder_age": random.randint(18, 85) if not name == "Yuki Sato" else 28, # make age check stable-ish
            "transaction_velocity": velocity,
            "location_mismatch": location_mismatch,
            "device_risk": device_risk,
            "category_risk": category_risk,
            "historical_fraud_rate": round(historical_fraud_rate, 4),
            
            # Simulation intent (for analytics validation)
            "simulated_fraud": 1 if is_fraudulent_intent else 0
        }

if __name__ == "__main__":
    # Test generator
    sim = TransactionSimulator()
    print("Normal transaction:")
    print(sim.generate_transaction(config_fraud_prob=0.0))
    print("\nFraudulent transaction:")
    print(sim.generate_transaction(config_fraud_prob=1.0))
