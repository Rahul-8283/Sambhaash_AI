"""
Intent Score Module - Analyzes user interest, objections, and timeline.

Calculates 0-1 score based on:
- Stated Interest (40%): Explicit interest expressions
- Objections (30%): Number and severity of objections
- Timeline (30%): Purchase/action timeline mentioned

Formula: composite = (interest * 0.4) + ((1 - objections_penalty) * 0.3) + (timeline_score * 0.3)
"""

import logging
from typing import Dict, List, Any
from enum import Enum

logger = logging.getLogger(__name__)


class InterestLevel(Enum):
    """Interest expression categories."""
    VERY_HIGH = 0.95
    HIGH = 0.85
    MODERATE = 0.65
    LOW = 0.35
    VERY_LOW = 0.1
    NEUTRAL = 0.5


class ObjectionSeverity(Enum):
    """Objection severity levels."""
    CRITICAL = 0.9
    HIGH = 0.7
    MEDIUM = 0.5
    LOW = 0.25


class TimelineScore(Enum):
    """Timeline urgency scores."""
    IMMEDIATE = 0.95
    SOON = 0.85
    MODERATE = 0.65
    LATER = 0.35
    UNCLEAR = 0.5


class IntentScoreCalculator:
    """Calculates interest-based intent score from conversation."""

    INTEREST_KEYWORDS = {
        InterestLevel.VERY_HIGH: [
            "definitely", "100%", "sign me up", "yes please", "absolutely",
            "perfect", "exactly what i need", "can't wait", "when can i start",
            "let's do it", "count me in", "i want", "i need this"
        ],
        InterestLevel.HIGH: [
            "interested", "sounds good", "tell me more", "very good",
            "promising", "helpful", "useful", "that works", "i like",
            "impressive", "seems right"
        ],
        InterestLevel.MODERATE: [
            "maybe", "could be", "interesting", "not bad", "might work",
            "could be useful", "possibly", "let me think", "consider it"
        ],
        InterestLevel.LOW: [
            "not sure", "i don't know", "hmm", "uncertain", "doubtful",
            "need to think", "skeptical", "concerned", "worried"
        ],
        InterestLevel.VERY_LOW: [
            "not interested", "no thanks", "definitely not", "not for me",
            "waste of time", "not relevant", "pass"
        ]
    }

    OBJECTION_KEYWORDS = {
        ObjectionSeverity.CRITICAL: [
            "too expensive", "can't afford", "too costly", "price is wrong",
            "out of budget", "too high", "not in our budget"
        ],
        ObjectionSeverity.HIGH: [
            "security", "risk", "compliance", "privacy", "can't use",
            "blocked", "not allowed", "won't approve", "need approval"
        ],
        ObjectionSeverity.MEDIUM: [
            "need time", "let me think", "have to discuss", "need to check",
            "competing", "alternatives", "need features", "missing"
        ],
        ObjectionSeverity.LOW: [
            "one thing", "one issue", "small problem", "minor", "just wondering"
        ]
    }

    TIMELINE_KEYWORDS = {
        TimelineScore.IMMEDIATE: [
            "today", "right now", "asap", "urgent", "immediately",
            "this week", "before friday", "emergency"
        ],
        TimelineScore.SOON: [
            "next week", "this month", "couple weeks", "few weeks",
            "by end of month", "quarter end"
        ],
        TimelineScore.MODERATE: [
            "couple months", "1-2 months", "next quarter", "2-3 months"
        ],
        TimelineScore.LATER: [
            "later", "maybe later", "future", "eventually", "someday",
            "not now", "6 months", "next year"
        ]
    }

    @staticmethod
    def extract_interest_level(user_messages: List[str]) -> float:
        """Extract interest level from user messages (0-1)."""
        if not user_messages:
            return 0.5

        interest_scores = []
        for message in user_messages:
            if not message:
                continue
            
            msg_lower = message.lower().strip()
            msg_score = 0.5
            
            for level, keywords in IntentScoreCalculator.INTEREST_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in msg_lower:
                        msg_score = level.value
                        break
                if msg_score != 0.5:
                    break
            
            interest_scores.append(msg_score)
        
        avg_interest = sum(interest_scores) / len(interest_scores) if interest_scores else 0.5
        return min(avg_interest, 1.0)

    @staticmethod
    def calculate_objections_penalty(user_messages: List[str]) -> float:
        """Calculate objection penalty (0-1, higher = more objections)."""
        if not user_messages:
            return 0.0

        objection_scores = []
        objection_count = 0
        
        for message in user_messages:
            if not message:
                continue
            
            msg_lower = message.lower().strip()
            max_severity = 0.0
            
            for severity in ObjectionSeverity:
                for keyword in IntentScoreCalculator.OBJECTION_KEYWORDS[severity]:
                    if keyword in msg_lower:
                        max_severity = max(max_severity, severity.value)
                        objection_count += 1
            
            if max_severity > 0:
                objection_scores.append(max_severity)
        
        if not objection_scores:
            return 0.0
        
        penalty = sum(objection_scores) / len(objection_scores)
        objection_multiplier = min(1.0, 1.0 + (objection_count * 0.1))
        penalty = min(penalty * objection_multiplier, 1.0)
        
        return penalty

    @staticmethod
    def extract_timeline_urgency(user_messages: List[str]) -> float:
        """Extract timeline urgency from messages (0-1)."""
        if not user_messages:
            return 0.5

        timeline_scores = []
        
        for message in user_messages:
            if not message:
                continue
            
            msg_lower = message.lower().strip()
            msg_score = 0.5
            
            for urgency, keywords in IntentScoreCalculator.TIMELINE_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in msg_lower:
                        msg_score = urgency.value
                        break
                if msg_score != 0.5:
                    break
            
            timeline_scores.append(msg_score)
        
        avg_timeline = sum(timeline_scores) / len(timeline_scores) if timeline_scores else 0.5
        return min(avg_timeline, 1.0)

    @staticmethod
    def calculate(
        user_messages: List[str],
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Calculate intent score from conversation data."""
        interest = IntentScoreCalculator.extract_interest_level(user_messages)
        objections_penalty = IntentScoreCalculator.calculate_objections_penalty(user_messages)
        timeline = IntentScoreCalculator.extract_timeline_urgency(user_messages)
        
        intent_score = (
            (interest * 0.4) +
            ((1.0 - objections_penalty) * 0.3) +
            (timeline * 0.3)
        )
        
        intent_score = max(0.0, min(intent_score, 1.0))
        
        logger.info(
            f"Intent Score: {intent_score:.3f} | "
            f"Interest: {interest:.2f}, Objections: {objections_penalty:.2f}, "
            f"Timeline: {timeline:.2f}"
        )
        
        return {
            "intent_score": intent_score,
            "interest_score": interest,
            "objections_penalty": objections_penalty,
            "timeline_score": timeline,
            "details": {
                "interest_level": interest,
                "objection_severity": objections_penalty,
                "purchase_timeline": timeline,
                "num_user_messages": len([m for m in user_messages if m]),
            }
        }
