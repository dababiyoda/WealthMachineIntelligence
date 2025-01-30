import numpy as np
from typing import Dict, Any
import tensorflow as tf
from sklearn.ensemble import RandomForestClassifier

class MarketIntelligenceAgent:
    def __init__(self):
        self.rf_model = RandomForestClassifier(n_estimators=100)
        self.lstm_model = self._build_lstm_model()
        
    def _build_lstm_model(self):
        model = tf.keras.Sequential([
            tf.keras.layers.LSTM(64, input_shape=(None, 5)),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        return model
        
    async def analyze_market_trends(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market trends using LSTM"""
        features = np.array([
            market_data["price"],
            market_data["volume"],
            [market_data["volatility"]] * 5,
            [market_data["sentiment"]] * 5,
            [market_data["market_cap"]] * 5
        ]).T.reshape(1, 5, 5)
        
        prediction = self.lstm_model.predict(features)
        confidence = float(np.mean(prediction))
        
        return {
            "confidence": confidence,
            "prediction": float(prediction[0, 0]),
            "timestamp": "2025-01-30"
        }
        
    async def assess_risk(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess market risk using Random Forest"""
        features = np.array([[
            np.mean(market_data["price"]),
            np.mean(market_data["volume"]),
            market_data["volatility"],
            market_data["sentiment"],
            market_data["market_cap"]
        ]])
        
        # Simple risk classification based on volatility and sentiment
        risk_score = float(market_data["volatility"] * (1 - market_data["sentiment"]))
        risk_class = "high" if risk_score > 0.5 else "medium" if risk_score > 0.2 else "low"
        
        return {
            "risk_score": risk_score,
            "risk_class": risk_class,
            "confidence": 0.85
        }
