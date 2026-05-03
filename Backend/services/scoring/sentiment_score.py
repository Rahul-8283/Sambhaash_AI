"""
Sentiment Score Module - Analyzes emotional tone of user responses.

Calculates 0-1 score based on:
- Positive sentiment keywords (increases score)
- Negative sentiment keywords (decreases score)
- Sentiment modifiers (very, really, extremely)
- Sentiment trajectory (trend over time)

Uses rule-based approach (no external ML required).
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class SentimentScoreCalculator:
    """Calculates sentiment-based score from user messages."""

    POSITIVE_KEYWORDS = {
        "very_strong": [
            "love", "amazing", "awesome", "wonderful", "fantastic", "perfect",
            "excellent", "outstanding", "incredible", "superb", "brilliant"
        ],
        "strong": [
            "good", "nice", "happy", "pleased", "satisfied", "impressed",
            "appreciate", "glad", "thrilled", "excited", "comfortable",
            "confident", "ready", "interested", "keen", "eager"
        ],
        "moderate": [
            "okay", "fine", "alright", "reasonable", "acceptable", "suitable",
            "fair", "decent", "adequate", "helpful", "useful"
        ]
    }

    NEGATIVE_KEYWORDS = {
        "very_strong": [
            "hate", "terrible", "horrible", "awful", "disgusting", "worst",
            "disgusted", "furious", "miserable", "depressed", "devastated"
        ],
        "strong": [
            "bad", "sad", "angry", "upset", "frustrated", "annoyed", "concerned",
            "worried", "scared", "afraid", "disappointed", "dislike", "problem",
            "issue", "mistake", "wrong", "fail", "failed", "difficult"
        ],
        "moderate": [
            "maybe", "uncertain", "unsure", "doubt", "skeptical", "hesitant",
            "question", "confused", "confusing"
        ]
    }

    INTENSIFIERS = {
        "very": 1.2,
        "really": 1.2,
        "extremely": 1.3,
        "absolutely": 1.3,
        "definitely": 1.2,
        "surely": 1.2,
        "quite": 1.1,
        "somewhat": 0.8,
        "kind of": 0.8,
        "sort of": 0.8,
        "not very": 0.5,
        "not really": 0.4,
        "not at all": 0.2
    }

    NEGATION_KEYWORDS = ["no", "not", "don't", "doesn't", "can't", "won't", "never"]

    @staticmethod
    def analyze_message_sentiment(message: str) -> float:
        """Analyze sentiment of a single message (0-1)."""
        if not message or not message.strip():
            return 0.5

        msg_lower = message.lower().strip()
        sentiment_score = 0.5
        
        positive_weight = 0
        negative_weight = 0
        
        for strength, keywords in SentimentScoreCalculator.POSITIVE_KEYWORDS.items():
            strength_multiplier = {"very_strong": 1.5, "strong": 1.0, "moderate": 0.7}[strength]
            
            for keyword in keywords:
                if keyword in msg_lower:
                    is_negated = False
                    words = msg_lower.split()
                    try:
                        for i, word in enumerate(words):
                            if keyword in word:
                                if i > 0 and words[i - 1] in SentimentScoreCalculator.NEGATION_KEYWORDS:
                                    is_negated = True
                                break
                    except (ValueError, IndexError):
                        pass
                    
                    if not is_negated:
                        positive_weight += strength_multiplier
        
        for strength, keywords in SentimentScoreCalculator.NEGATIVE_KEYWORDS.items():
            strength_multiplier = {"very_strong": 1.5, "strong": 1.0, "moderate": 0.7}[strength]
            
            for keyword in keywords:
                if keyword in msg_lower:
                    is_negated = False
                    words = msg_lower.split()
                    try:
                        for i, word in enumerate(words):
                            if keyword in word:
                                if i > 0 and words[i - 1] in SentimentScoreCalculator.NEGATION_KEYWORDS:
                                    is_negated = True
                                break
                    except (ValueError, IndexError):
                        pass
                    
                    if not is_negated:
                        negative_weight += strength_multiplier
        
        intensifier_multiplier = 1.0
        for intensifier, multiplier in SentimentScoreCalculator.INTENSIFIERS.items():
            if intensifier in msg_lower:
                intensifier_multiplier = multiplier
                break
        
        if positive_weight > 0 or negative_weight > 0:
            net_sentiment = positive_weight - negative_weight
            
            if net_sentiment > 0:
                sentiment_score = 0.5 + (min(net_sentiment, 1.0) * 0.5)
            elif net_sentiment < 0:
                sentiment_score = 0.5 - (min(abs(net_sentiment), 1.0) * 0.5)
            else:
                sentiment_score = 0.5
            
            if sentiment_score > 0.5:
                sentiment_score = 0.5 + ((sentiment_score - 0.5) * intensifier_multiplier)
            elif sentiment_score < 0.5:
                sentiment_score = 0.5 - ((0.5 - sentiment_score) * intensifier_multiplier)
        
        sentiment_score = max(0.0, min(sentiment_score, 1.0))
        return sentiment_score

    @staticmethod
    def calculate_sentiment_trajectory(user_messages: List[str]) -> float:
        """Analyze sentiment trend (do they get more positive?)."""
        if not user_messages or len(user_messages) < 2:
            return 0.5
        
        sentiments = [
            SentimentScoreCalculator.analyze_message_sentiment(msg)
            for msg in user_messages if msg
        ]
        
        if not sentiments or len(sentiments) < 2:
            return 0.5
        
        first_half_avg = sum(sentiments[:len(sentiments)//2]) / (len(sentiments)//2 + 1)
        second_half_avg = sum(sentiments[len(sentiments)//2:]) / (len(sentiments) - len(sentiments)//2 + 1)
        
        trajectory = second_half_avg - first_half_avg
        trajectory_score = 0.5 + (trajectory * 0.5)
        trajectory_score = max(0.0, min(trajectory_score, 1.0))
        
        logger.debug(
            f"Sentiment trajectory: {trajectory_score:.2f} "
            f"(first: {first_half_avg:.2f}, second: {second_half_avg:.2f})"
        )
        return trajectory_score

    @staticmethod
    def calculate(
        user_messages: List[str],
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Calculate sentiment score from user messages."""
        if not user_messages:
            return {
                "sentiment_score": 0.5,
                "message_sentiments": [],
                "trajectory_score": 0.5,
                "details": {
                    "num_messages": 0,
                    "positive_messages": 0,
                    "negative_messages": 0,
                    "neutral_messages": 0
                }
            }
        
        message_sentiments = [
            SentimentScoreCalculator.analyze_message_sentiment(msg)
            for msg in user_messages if msg
        ]
        
        if not message_sentiments:
            return {
                "sentiment_score": 0.5,
                "message_sentiments": [],
                "trajectory_score": 0.5,
                "details": {
                    "num_messages": 0,
                    "positive_messages": 0,
                    "negative_messages": 0,
                    "neutral_messages": 0
                }
            }
        
        overall_sentiment = sum(message_sentiments) / len(message_sentiments)
        trajectory_score = SentimentScoreCalculator.calculate_sentiment_trajectory(user_messages)
        
        sentiment_score = (overall_sentiment * 0.7) + (trajectory_score * 0.3)
        sentiment_score = max(0.0, min(sentiment_score, 1.0))
        
        positive_msgs = sum(1 for s in message_sentiments if s > 0.6)
        negative_msgs = sum(1 for s in message_sentiments if s < 0.4)
        neutral_msgs = len(message_sentiments) - positive_msgs - negative_msgs
        
        logger.info(
            f"Sentiment Score: {sentiment_score:.3f} | "
            f"Overall: {overall_sentiment:.2f}, Trajectory: {trajectory_score:.2f} | "
            f"Positive: {positive_msgs}, Negative: {negative_msgs}, Neutral: {neutral_msgs}"
        )
        
        return {
            "sentiment_score": sentiment_score,
            "message_sentiments": message_sentiments,
            "trajectory_score": trajectory_score,
            "details": {
                "num_messages": len(message_sentiments),
                "positive_messages": positive_msgs,
                "negative_messages": negative_msgs,
                "neutral_messages": neutral_msgs,
                "avg_sentiment": overall_sentiment
            }
        }
