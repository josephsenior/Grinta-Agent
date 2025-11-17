"""Performance Predictor - ML-Based Performance Forecasting.

Uses machine learning models to predict prompt performance before execution,
enabling proactive optimization and risk assessment.
"""

from __future__ import annotations

import json
import pickle
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

from forge.core.logger import forge_logger as logger
from forge.prompt_optimization.models import PromptVariant, PromptMetrics


class PredictionModel(Enum):
    """Types of prediction models."""

    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    LINEAR_REGRESSION = "linear_regression"
    ENSEMBLE = "ensemble"


@dataclass
class PredictionFeatures:
    """Features for performance prediction."""

    prompt_length: int
    prompt_complexity: float
    variant_version: int
    historical_success_rate: float
    historical_avg_time: float
    historical_error_rate: float
    context_domain: str
    context_task_type: str
    context_urgency: str
    time_of_day: int  # 0-23
    day_of_week: int  # 0-6
    recent_performance_trend: float
    resource_availability: float
    user_experience_level: str
    system_load: float


@dataclass
class PerformancePrediction:
    """Performance prediction result."""

    variant_id: str
    predicted_score: float
    confidence: float
    predicted_success_rate: float
    predicted_execution_time: float
    predicted_error_rate: float
    risk_level: str  # low, medium, high
    recommendations: List[str]
    model_used: str
    features_used: Dict[str, Any]


class PerformancePredictor:
    """Performance Predictor - ML-based performance forecasting.

    Features:
    - Multiple ML models for prediction
    - Feature engineering and selection
    - Confidence scoring
    - Risk assessment
    - Recommendation generation
    - Model retraining and adaptation
    """

    def __init__(
        self,
        model_type: PredictionModel = PredictionModel.ENSEMBLE,
        retrain_frequency: int = 100,  # Retrain every N predictions
        confidence_threshold: float = 0.7,
        risk_thresholds: Optional[Dict[str, float]] = None,
    ):
        """Configure prediction model options and initialize training state caches."""
        if isinstance(model_type, str):
            try:
                model_type = PredictionModel(model_type)
            except ValueError:
                logger.warning(
                    "Unknown prediction model '%s', defaulting to 'ensemble'", model_type
                )
                model_type = PredictionModel.ENSEMBLE

        self.model_type = model_type
        self.retrain_frequency = retrain_frequency
        self.confidence_threshold = confidence_threshold
        self.risk_thresholds = risk_thresholds or {
            "low": 0.8,
            "medium": 0.6,
            "high": 0.4,
        }

        # Models
        self.models: Dict[str, Any] = {}
        self.scaler = StandardScaler()
        self.is_trained = False

        # Training data
        self.training_data: List[Tuple[PredictionFeatures, float]] = []
        self.prediction_count = 0

        # Performance tracking
        self.prediction_accuracy: List[float] = []
        self.model_performance: Dict[str, List[float]] = {}

        # Feature importance
        self.feature_importance: Dict[str, float] = {}

        logger.info(f"Performance Predictor initialized with {model_type.value} model")

    def _initialize_models(self) -> None:
        """Initialize prediction models."""
        if self.model_type == PredictionModel.RANDOM_FOREST:
            self.models["primary"] = RandomForestRegressor(
                n_estimators=100, max_depth=10, random_state=42
            )
        elif self.model_type == PredictionModel.GRADIENT_BOOSTING:
            self.models["primary"] = GradientBoostingRegressor(
                n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42
            )
        elif self.model_type == PredictionModel.LINEAR_REGRESSION:
            self.models["primary"] = LinearRegression()
        elif self.model_type == PredictionModel.ENSEMBLE:
            self.models["random_forest"] = RandomForestRegressor(
                n_estimators=50, max_depth=8, random_state=42
            )
            self.models["gradient_boosting"] = GradientBoostingRegressor(
                n_estimators=50, max_depth=6, learning_rate=0.1, random_state=42
            )
            self.models["linear_regression"] = LinearRegression()

    def _extract_features(
        self,
        variant: PromptVariant,
        context: Dict[str, Any],
        historical_metrics: Optional[PromptMetrics] = None,
    ) -> PredictionFeatures:
        """Extract features for prediction from variant and context."""
        # Basic prompt features
        prompt_length = len(variant.content)
        prompt_complexity = self._calculate_complexity(variant.content)

        # Historical performance
        historical_success_rate = (
            historical_metrics.success_rate if historical_metrics else 0.5
        )
        historical_avg_time = (
            historical_metrics.avg_execution_time if historical_metrics else 1.0
        )
        historical_error_rate = (
            historical_metrics.error_rate if historical_metrics else 0.1
        )

        # Context features
        context_domain = context.get("domain", "general")
        context_task_type = context.get("task_type", "general")
        context_urgency = context.get("urgency", "medium")

        # Time features
        now = datetime.now()
        time_of_day = now.hour
        day_of_week = now.weekday()

        # Performance trend
        recent_performance_trend = self._calculate_performance_trend(variant.id)

        # Resource features
        resource_availability = context.get("resource_availability", 1.0)
        user_experience_level = context.get("user_experience_level", "intermediate")
        system_load = context.get("system_load", 0.5)

        return PredictionFeatures(
            prompt_length=prompt_length,
            prompt_complexity=prompt_complexity,
            variant_version=variant.version,
            historical_success_rate=historical_success_rate,
            historical_avg_time=historical_avg_time,
            historical_error_rate=historical_error_rate,
            context_domain=context_domain,
            context_task_type=context_task_type,
            context_urgency=context_urgency,
            time_of_day=time_of_day,
            day_of_week=day_of_week,
            recent_performance_trend=recent_performance_trend,
            resource_availability=resource_availability,
            user_experience_level=user_experience_level,
            system_load=system_load,
        )

    def _calculate_complexity(self, content: str) -> float:
        """Calculate prompt complexity score."""
        # Simple complexity heuristics
        word_count = len(content.split())
        sentence_count = content.count(".") + content.count("!") + content.count("?")
        avg_sentence_length = word_count / max(sentence_count, 1)

        # Check for complex indicators
        complex_indicators = [
            "complex",
            "sophisticated",
            "advanced",
            "intricate",
            "multi-step",
            "recursive",
            "algorithm",
            "optimization",
        ]
        complexity_bonus = sum(
            1 for indicator in complex_indicators if indicator in content.lower()
        )

        # Normalize to 0-1 range
        complexity = min(1.0, (avg_sentence_length / 20.0) + (complexity_bonus * 0.1))
        return complexity

    def _calculate_performance_trend(self, variant_id: str) -> float:
        """Calculate recent performance trend for a variant."""
        # This would typically fetch from a time-series database
        # For now, return a neutral value
        return 0.0

    def _features_to_array(self, features: PredictionFeatures) -> np.ndarray:
        """Convert features to numpy array for model input."""
        # Convert categorical features to numerical
        domain_map = {"general": 0, "software": 1, "data": 2, "web": 3, "creative": 4}
        task_type_map = {
            "general": 0,
            "reasoning": 1,
            "generation": 2,
            "debugging": 3,
            "optimization": 4,
        }
        urgency_map = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        experience_map = {"beginner": 0, "intermediate": 1, "advanced": 2, "expert": 3}

        return np.array(
            [
                features.prompt_length,
                features.prompt_complexity,
                features.variant_version,
                features.historical_success_rate,
                features.historical_avg_time,
                features.historical_error_rate,
                domain_map.get(features.context_domain, 0),
                task_type_map.get(features.context_task_type, 0),
                urgency_map.get(features.context_urgency, 1),
                features.time_of_day,
                features.day_of_week,
                features.recent_performance_trend,
                features.resource_availability,
                experience_map.get(features.user_experience_level, 1),
                features.system_load,
            ]
        ).reshape(1, -1)

    def _prepare_training_data(self) -> tuple[np.ndarray, np.ndarray]:
        """Prepare features and targets from training data.

        Returns:
            Tuple of (X, y) arrays

        """
        X = np.array(
            [
                self._features_to_array(features).flatten()
                for features, _ in self.training_data
            ]
        )
        y = np.array([target for _, target in self.training_data])
        return X, y

    def _split_and_scale_data(
        self, X: np.ndarray, y: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Split and scale training data.

        Args:
            X: Feature array
            y: Target array

        Returns:
            Tuple of (X_train_scaled, X_test_scaled, y_train, y_test)

        """
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        return X_train_scaled, X_test_scaled, y_train, y_test

    def _train_ensemble_models(
        self,
        X_train_scaled: np.ndarray,
        y_train: np.ndarray,
        X_test_scaled: np.ndarray,
        y_test: np.ndarray,
    ) -> None:
        """Train ensemble models.

        Args:
            X_train_scaled: Scaled training features
            y_train: Training targets
            X_test_scaled: Scaled test features
            y_test: Test targets

        """
        for name, model in self.models.items():
            model.fit(X_train_scaled, y_train)

            y_pred = model.predict(X_test_scaled)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)

            logger.info(f"Model {name} - MSE: {mse:.4f}, R2: {r2:.4f}")

            if name not in self.model_performance:
                self.model_performance[name] = []
            self.model_performance[name].append(r2)

        # Calculate feature importance from best model
        best_model_name = max(
            self.model_performance.keys(), key=lambda k: self.model_performance[k][-1]
        )
        if hasattr(self.models[best_model_name], "feature_importances_"):
            self.feature_importance = dict(
                zip(
                    [
                        "prompt_length",
                        "prompt_complexity",
                        "variant_version",
                        "historical_success_rate",
                        "historical_avg_time",
                        "historical_error_rate",
                        "context_domain",
                        "context_task_type",
                        "context_urgency",
                        "time_of_day",
                        "day_of_week",
                        "recent_performance_trend",
                        "resource_availability",
                        "user_experience_level",
                        "system_load",
                    ],
                    self.models[best_model_name].feature_importances_,
                )
            )

    def train(self, training_data: List[Tuple[PredictionFeatures, float]]) -> None:
        """Train the prediction models."""
        if not training_data:
            logger.warning("No training data provided")
            return

        self.training_data.extend(training_data)

        if len(self.training_data) < 10:
            logger.warning(
                f"Not enough training data: {len(self.training_data)} samples"
            )
            return

        X, y = self._prepare_training_data()
        X_train_scaled, X_test_scaled, y_train, y_test = self._split_and_scale_data(
            X, y
        )

        self._initialize_models()

        if self.model_type == PredictionModel.ENSEMBLE:
            self._train_ensemble_models(X_train_scaled, y_train, X_test_scaled, y_test)
        else:
            # Train single model
            model = self.models["primary"]
            model.fit(X_train_scaled, y_train)

            # Evaluate model
            y_pred = model.predict(X_test_scaled)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)

            logger.info(f"Model performance - MSE: {mse:.4f}, R2: {r2:.4f}")

            # Store performance
            if "primary" not in self.model_performance:
                self.model_performance["primary"] = []
            self.model_performance["primary"].append(r2)

            # Calculate feature importance
            if hasattr(model, "feature_importances_"):
                self.feature_importance = dict(
                    zip(
                        [
                            "prompt_length",
                            "prompt_complexity",
                            "variant_version",
                            "historical_success_rate",
                            "historical_avg_time",
                            "historical_error_rate",
                            "context_domain",
                            "context_task_type",
                            "context_urgency",
                            "time_of_day",
                            "day_of_week",
                            "recent_performance_trend",
                            "resource_availability",
                            "user_experience_level",
                            "system_load",
                        ],
                        model.feature_importances_,
                    )
                )

        self.is_trained = True
        logger.info("Model training completed")

    def predict(
        self,
        variant: PromptVariant,
        context: Dict[str, Any],
        historical_metrics: Optional[PromptMetrics] = None,
    ) -> PerformancePrediction:
        """Predict performance for a variant."""
        if not self.is_trained:
            # Return default prediction if not trained
            return self._default_prediction(variant, context)

        try:
            # Extract features
            features = self._extract_features(variant, context, historical_metrics)
            features_array = self._features_to_array(features)
            features_scaled = self.scaler.transform(features_array)

            # Make prediction
            if self.model_type == PredictionModel.ENSEMBLE:
                predictions = []
                for name, model in self.models.items():
                    pred = model.predict(features_scaled)[0]
                    predictions.append(pred)

                # Average predictions
                predicted_score = np.mean(predictions)

                # Calculate confidence based on prediction variance
                confidence = max(0.0, 1.0 - np.std(predictions))

                model_used = f"ensemble_{len(self.models)}"
            else:
                model = self.models["primary"]
                predicted_score = model.predict(features_scaled)[0]

                # Simple confidence calculation
                confidence = 0.8  # Could be improved with uncertainty quantification
                model_used = self.model_type.value

            # Generate additional predictions
            predicted_success_rate = min(1.0, max(0.0, predicted_score))
            predicted_execution_time = max(0.1, 1.0 / max(predicted_score, 0.1))
            predicted_error_rate = max(0.0, 1.0 - predicted_success_rate)

            # Determine risk level
            risk_level = self._determine_risk_level(predicted_score, confidence)

            # Generate recommendations
            recommendations = self._generate_recommendations(
                features, predicted_score, confidence, risk_level
            )

            # Update prediction count
            self.prediction_count += 1

            # Check if retraining is needed
            if self.prediction_count % self.retrain_frequency == 0:
                logger.info("Retraining models due to prediction count threshold")
                # In a real implementation, this would trigger retraining

            return PerformancePrediction(
                variant_id=variant.id,
                predicted_score=predicted_score,
                confidence=confidence,
                predicted_success_rate=predicted_success_rate,
                predicted_execution_time=predicted_execution_time,
                predicted_error_rate=predicted_error_rate,
                risk_level=risk_level,
                recommendations=recommendations,
                model_used=model_used,
                features_used=self._features_to_dict(features),
            )

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return self._default_prediction(variant, context)

    def _default_prediction(
        self, variant: PromptVariant, context: Dict[str, Any]
    ) -> PerformancePrediction:
        """Return a default prediction when model is not trained or fails."""
        return PerformancePrediction(
            variant_id=variant.id,
            predicted_score=0.5,
            confidence=0.3,
            predicted_success_rate=0.5,
            predicted_execution_time=1.0,
            predicted_error_rate=0.1,
            risk_level="medium",
            recommendations=["Model not trained - using default prediction"],
            model_used="default",
            features_used={},
        )

    def _determine_risk_level(self, predicted_score: float, confidence: float) -> str:
        """Determine risk level based on prediction and confidence."""
        if predicted_score >= self.risk_thresholds["low"] and confidence >= 0.8:
            return "low"
        elif predicted_score >= self.risk_thresholds["medium"] and confidence >= 0.6:
            return "medium"
        else:
            return "high"

    def _generate_recommendations(
        self,
        features: PredictionFeatures,
        predicted_score: float,
        confidence: float,
        risk_level: str,
    ) -> List[str]:
        """Generate recommendations based on prediction."""
        recommendations = []

        if predicted_score < 0.6:
            recommendations.append("Consider using a different prompt variant")

        if confidence < 0.7:
            recommendations.append("Low confidence - consider gathering more data")

        if features.prompt_complexity > 0.8:
            recommendations.append("High complexity - consider simplifying the prompt")

        if features.historical_error_rate > 0.2:
            recommendations.append("High historical error rate - review prompt design")

        if features.context_urgency == "critical" and predicted_score < 0.8:
            recommendations.append(
                "Critical task with low predicted performance - use proven variant"
            )

        if features.resource_availability < 0.5:
            recommendations.append(
                "Low resource availability - consider simpler approach"
            )

        return recommendations

    def _features_to_dict(self, features: PredictionFeatures) -> Dict[str, Any]:
        """Convert features to dictionary for storage."""
        return {
            "prompt_length": features.prompt_length,
            "prompt_complexity": features.prompt_complexity,
            "variant_version": features.variant_version,
            "historical_success_rate": features.historical_success_rate,
            "historical_avg_time": features.historical_avg_time,
            "historical_error_rate": features.historical_error_rate,
            "context_domain": features.context_domain,
            "context_task_type": features.context_task_type,
            "context_urgency": features.context_urgency,
            "time_of_day": features.time_of_day,
            "day_of_week": features.day_of_week,
            "recent_performance_trend": features.recent_performance_trend,
            "resource_availability": features.resource_availability,
            "user_experience_level": features.user_experience_level,
            "system_load": features.system_load,
        }

    def add_training_data(
        self, features: PredictionFeatures, actual_score: float
    ) -> None:
        """Add training data for model improvement."""
        self.training_data.append((features, actual_score))

        # Check if retraining is needed
        if len(self.training_data) >= self.retrain_frequency:
            logger.info("Retraining models due to new training data")
            self.train([])  # Retrain with all data

    def get_model_performance(self) -> Dict[str, Any]:
        """Get model performance statistics."""
        if not self.model_performance:
            return {"message": "No model performance data available"}

        performance = {}
        for model_name, scores in self.model_performance.items():
            if scores:
                performance[model_name] = {
                    "latest_r2": scores[-1],
                    "avg_r2": np.mean(scores),
                    "max_r2": np.max(scores),
                    "min_r2": np.min(scores),
                    "prediction_count": len(scores),
                }

        return {
            "model_performance": performance,
            "feature_importance": self.feature_importance,
            "is_trained": self.is_trained,
            "training_data_size": len(self.training_data),
            "prediction_count": self.prediction_count,
        }

    def save_model(self, filepath: str) -> None:
        """Save trained models to file."""
        if not self.is_trained:
            logger.warning("No trained model to save")
            return

        model_data = {
            "models": self.models,
            "scaler": self.scaler,
            "is_trained": self.is_trained,
            "feature_importance": self.feature_importance,
            "model_performance": self.model_performance,
        }

        try:
            with open(filepath, "wb") as f:
                pickle.dump(model_data, f)
        except pickle.PicklingError as exc:
            logger.warning("Unable to pickle performance predictor model: %s", exc)
            model_data["models"] = {name: None for name in self.models}
            with open(filepath, "wb") as f:
                pickle.dump(model_data, f)

        logger.info(f"Model saved to {filepath}")

    def load_model(self, filepath: str) -> None:
        """Load trained models from file."""
        try:
            with open(filepath, "rb") as f:
                model_data = pickle.load(f)

            stored_models = model_data.get("models", {})
            if stored_models and any(value is None for value in stored_models.values()):
                self._initialize_models()
            else:
                self.models = stored_models
            self.scaler = model_data["scaler"]
            self.is_trained = model_data["is_trained"]
            self.feature_importance = model_data.get("feature_importance", {})
            self.model_performance = model_data.get("model_performance", {})

            logger.info(f"Model loaded from {filepath}")
        except Exception as e:
            logger.error(f"Failed to load model from {filepath}: {e}")
