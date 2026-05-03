"""
Scoring package - Lead quality scoring and classification.

Modules:
- intent_score: Analyzes interest, objections, timeline
- engagement_score: Analyzes conversation engagement metrics
- sentiment_score: Analyzes emotional tone and sentiment
- scoring_engine: Main orchestrator combining all scores
"""

from backend.services.scoring.intent_score import IntentScoreCalculator
from backend.services.scoring.engagement_score import EngagementScoreCalculator
from backend.services.scoring.sentiment_score import SentimentScoreCalculator
from backend.services.scoring.scoring_engine import ScoringEngine, LeadClassification

__all__ = [
    "IntentScoreCalculator",
    "EngagementScoreCalculator",
    "SentimentScoreCalculator",
    "ScoringEngine",
    "LeadClassification",
]
