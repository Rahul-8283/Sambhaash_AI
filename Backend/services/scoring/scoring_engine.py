"""
Main Scoring Engine - Orchestrates intent, engagement, and sentiment scores.

Calculates composite lead score by combining:
- Intent Score (33.3%): Interest, objections, timeline
- Engagement Score (33.3%): Duration, questions, objections handled, response rate
- Sentiment Score (33.3%): Emotional tone, trajectory

Classifies leads into HOT/WARM/COLD based on composite score:
- HOT (≥0.75): High-quality leads ready for RM handoff
- WARM (0.50-0.74): Nurture candidates for WhatsApp messaging
- COLD (<0.50): Low-priority leads for future follow-up

Also triggers RM assignment if HOT lead detected.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

from services.scoring.intent_score import IntentScoreCalculator
from services.scoring.engagement_score import EngagementScoreCalculator
from services.scoring.sentiment_score import SentimentScoreCalculator
from services.database.repository import Repository

logger = logging.getLogger(__name__)


class LeadClassification(Enum):
    """Lead quality classifications."""
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"


class ScoringEngine:
    """
    Main scoring orchestrator.
    
    Combines intent, engagement, and sentiment scores to produce
    a composite score and lead classification.
    """

    # Classification thresholds
    HOT_THRESHOLD = 0.75
    WARM_THRESHOLD = 0.50
    
    def __init__(self, repository: Repository):
        """
        Initialize scoring engine with database repository.
        
        Args:
            repository: Repository instance for database operations
        """
        self.repository = repository
        logger.info("Scoring Engine initialized")

    @staticmethod
    def extract_user_messages(conversation_history) -> List[str]:
        """
        Extract the caller's utterances, oldest first.

        Accepts the stored turn shape ``{"user": ..., "ai": ...}``, chat-style
        ``{"role": "user", "content": ...}`` dicts, or the JSON text of either.
        """
        if isinstance(conversation_history, str):
            try:
                conversation_history = json.loads(conversation_history)
            except ValueError:
                return []
        if not isinstance(conversation_history, list):
            return []

        user_messages = []
        for turn in conversation_history:
            if not isinstance(turn, dict):
                continue
            if turn.get("role") == "user":
                content = turn.get("content")
            else:
                content = turn.get("user")
            content = str(content or "").strip()
            if content:
                user_messages.append(content)

        return user_messages

    @staticmethod
    def calculate_composite_score(
        intent_score: float,
        engagement_score: float,
        sentiment_score: float
    ) -> float:
        """
        Calculate composite score from three components.
        
        Uses equal weighting (33.3% each) by default.
        
        Args:
            intent_score: Interest/timeline/objections score (0-1)
            engagement_score: Duration/questions/response score (0-1)
            sentiment_score: Emotional tone score (0-1)
            
        Returns:
            float: Composite score 0-1
        """
        composite = (intent_score + engagement_score + sentiment_score) / 3.0
        return max(0.0, min(composite, 1.0))

    @staticmethod
    def classify_lead(composite_score: float) -> LeadClassification:
        """
        Classify lead based on composite score.
        
        Args:
            composite_score: Score 0-1
            
        Returns:
            LeadClassification enum
        """
        if composite_score >= ScoringEngine.HOT_THRESHOLD:
            return LeadClassification.HOT
        elif composite_score >= ScoringEngine.WARM_THRESHOLD:
            return LeadClassification.WARM
        else:
            return LeadClassification.COLD

    def score_conversation(
        self,
        conversation_history=None,
        duration_seconds: int = 0,
    ) -> Dict[str, Any]:
        """
        Score a conversation without touching the database.

        Returns the component scores (0-1), the composite and the classification.
        """
        if isinstance(conversation_history, str):
            try:
                conversation_history = json.loads(conversation_history)
            except ValueError:
                conversation_history = []
        user_messages = self.extract_user_messages(conversation_history)
        turns = len(conversation_history) if isinstance(conversation_history, list) else None

        intent_result = IntentScoreCalculator.calculate(user_messages, conversation_history)
        engagement_result = EngagementScoreCalculator.calculate(user_messages, duration_seconds, turns)
        sentiment_result = SentimentScoreCalculator.calculate(user_messages, conversation_history)

        intent_score = intent_result["intent_score"]
        engagement_score = engagement_result["engagement_score"]
        sentiment_score = sentiment_result["sentiment_score"]

        composite_score = self.calculate_composite_score(intent_score, engagement_score, sentiment_score)
        classification = self.classify_lead(composite_score)

        return {
            "composite_score": composite_score,
            "classification": classification.value,
            "intent_score": intent_score,
            "engagement_score": engagement_score,
            "sentiment_score": sentiment_score,
            "should_assign_rm": classification == LeadClassification.HOT,
            "should_send_whatsapp": classification == LeadClassification.WARM,
            "breakdown": {
                "intent": intent_result,
                "engagement": engagement_result,
                "sentiment": sentiment_result,
            },
        }

    async def calculate_score(
        self,
        lead_id: str,
        call_session_id: str,
        conversation_history=None,
        duration_seconds: int = 0,
    ) -> Dict[str, Any]:
        """Score a conversation and store the result as a lead_scores row."""
        result = self.score_conversation(conversation_history, duration_seconds)

        logger.info(
            f"Lead {lead_id} Scores: Intent={result['intent_score']:.3f}, "
            f"Engagement={result['engagement_score']:.3f}, Sentiment={result['sentiment_score']:.3f}, "
            f"Composite={result['composite_score']:.3f} -> {result['classification']}"
        )

        await self.repository.create_lead_score(
            lead_id=lead_id,
            call_session_id=call_session_id,
            interest_score=result["intent_score"],
            engagement_score=result["engagement_score"],
            sentiment_score=result["sentiment_score"],
            classification=result["classification"],
        )

        result["lead_id"] = lead_id
        result["timestamp"] = datetime.utcnow().isoformat()
        return result

    async def recalculate_scores_for_session(
        self,
        session_id: str,
        lead_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Recalculate scores for a call session.
        
        Args:
            session_id: UUID of the call session
            lead_id: UUID of the lead
            
        Returns:
            Scoring result or None if session not found
        """
        try:
            # Get call session from database
            session = await self.repository.get_call_session(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found")
                return None
            
            # Extract conversation data from session
            conversation_history = session.get("conversation_history", [])
            duration_seconds = session.get("duration_seconds", 0)
            
            # Calculate scores
            result = await self.calculate_score(
                lead_id=lead_id,
                call_session_id=session_id,
                conversation_history=conversation_history,
                duration_seconds=duration_seconds,
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error recalculating scores for session {session_id}: {e}")
            raise

    @staticmethod
    def get_scoring_summary(scoring_result: Dict[str, Any]) -> str:
        """
        Generate human-readable scoring summary.
        
        Args:
            scoring_result: Output from calculate_score()
            
        Returns:
            str: Formatted summary
        """
        return (
            f"Lead Scoring Summary\n"
            f"==================\n"
            f"Classification: {scoring_result['classification']}\n"
            f"Composite Score: {scoring_result['composite_score']:.2%}\n"
            f"\nComponent Scores:\n"
            f"  • Intent: {scoring_result['intent_score']:.2%}\n"
            f"  • Engagement: {scoring_result['engagement_score']:.2%}\n"
            f"  • Sentiment: {scoring_result['sentiment_score']:.2%}\n"
            f"\nActions:\n"
            f"  • Assign to RM: {'YES' if scoring_result['should_assign_rm'] else 'NO'}\n"
            f"  • Send WhatsApp: {'YES' if scoring_result['should_send_whatsapp'] else 'NO'}"
        )
