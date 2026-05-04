"""
Engagement Score Module - Analyzes user engagement in the conversation.

Calculates 0-1 score based on:
- Duration (25%): Length of conversation
- Questions Asked (25%): Number of questions user asks
- Objections Handled (25%): Objections overcome
- Response Rate (25%): Quality of responses

Formula: composite = (duration * 0.25) + (questions * 0.25) + (objections * 0.25) + (response * 0.25)
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class EngagementScoreCalculator:
    """Calculates engagement-based score from conversation metrics."""

    DURATION_THRESHOLDS = {
        0: 0.1,
        30: 0.3,
        60: 0.5,
        180: 0.7,
        600: 0.95
    }

    QUESTION_THRESHOLDS = {
        0: 0.1,
        1: 0.3,
        2: 0.5,
        4: 0.75,
        7: 0.95
    }

    QUESTION_INDICATORS = [
        "?", "how ", "what ", "when ", "where ", "why ", "which ",
        "can you ", "could you ", "would you ", "will you ",
        "is it ", "are there ", "do you ", "does ",
        "tell me ", "show me ", "explain "
    ]

    RESOLUTION_KEYWORDS = [
        "okay", "ok", "alright", "fine", "got it", "understand",
        "that makes sense", "thanks", "thank you", "helpful",
        "good point", "i see", "yes that", "that works"
    ]

    @staticmethod
    def calculate_duration_score(duration_seconds: int) -> float:
        """Calculate engagement score based on call duration."""
        if duration_seconds <= 0:
            return 0.1
        
        score = 0.1
        for threshold, score_value in sorted(EngagementScoreCalculator.DURATION_THRESHOLDS.items()):
            if duration_seconds >= threshold:
                score = score_value
        
        score = min(score, 1.0)
        logger.debug(f"Duration score: {score:.2f} for {duration_seconds}s")
        return score

    @staticmethod
    def detect_questions(message: str) -> int:
        """Detect number of questions in a message."""
        if not message:
            return 0
        
        msg_lower = message.lower().strip()
        question_count = msg_lower.count("?")
        
        if question_count == 0:
            for indicator in EngagementScoreCalculator.QUESTION_INDICATORS:
                if indicator in msg_lower:
                    question_count += 1
                    break
        
        return question_count

    @staticmethod
    def calculate_questions_score(user_messages: List[str]) -> float:
        """Calculate engagement score based on questions asked."""
        if not user_messages:
            return 0.1
        
        total_questions = 0
        for message in user_messages:
            if message:
                total_questions += EngagementScoreCalculator.detect_questions(message)
        
        score = 0.1
        for threshold, score_value in sorted(EngagementScoreCalculator.QUESTION_THRESHOLDS.items()):
            if total_questions >= threshold:
                score = score_value
        
        score = min(score, 1.0)
        logger.debug(f"Questions score: {score:.2f} for {total_questions} questions")
        return score

    @staticmethod
    def detect_objections(user_messages: List[str]) -> int:
        """Detect number of objections raised in messages."""
        if not user_messages:
            return 0
        
        objection_keywords = [
            "but ", "however", "concern", "worried", "problem",
            "issue", "question about", "confused", "unclear",
            "cost", "price", "afford", "budget", "expensive"
        ]
        
        objection_count = 0
        for message in user_messages:
            if not message:
                continue
            
            msg_lower = message.lower().strip()
            for keyword in objection_keywords:
                if keyword in msg_lower:
                    objection_count += 1
                    break
        
        return objection_count

    @staticmethod
    def calculate_objections_handled_score(user_messages: List[str]) -> float:
        """Calculate engagement score based on objections handled."""
        if not user_messages:
            return 0.1
        
        objections_count = EngagementScoreCalculator.detect_objections(user_messages)
        
        if objections_count == 0:
            return 0.1
        
        resolutions_found = 0
        for message in user_messages:
            if not message:
                continue
            
            msg_lower = message.lower().strip()
            for keyword in EngagementScoreCalculator.RESOLUTION_KEYWORDS:
                if keyword in msg_lower:
                    resolutions_found += 1
                    break
        
        resolution_rate = min(resolutions_found / objections_count, 1.0)
        
        if resolution_rate == 0:
            score = 0.1
        elif resolution_rate < 0.33:
            score = 0.3
        elif resolution_rate < 0.66:
            score = 0.5
        elif resolution_rate < 0.9:
            score = 0.75
        else:
            score = 0.95
        
        score = min(score, 1.0)
        logger.debug(f"Objections handled score: {score:.2f} for {objections_count} objections")
        return score

    @staticmethod
    def calculate_response_rate_score(
        user_messages: List[str],
        conversation_turns: int = None
    ) -> float:
        """Calculate engagement score based on response quality/speed."""
        if not user_messages:
            return 0.1
        
        valid_messages = [m for m in user_messages if m and m.strip()]
        
        if not valid_messages:
            return 0.1
        
        avg_length = sum(len(msg) for msg in valid_messages) / len(valid_messages)
        
        if avg_length < 10:
            response_score = 0.1
        elif avg_length < 30:
            response_score = 0.3
        elif avg_length < 100:
            response_score = 0.5
        elif avg_length < 200:
            response_score = 0.75
        else:
            response_score = 0.95
        
        if conversation_turns and conversation_turns > 0:
            participation_rate = len(valid_messages) / conversation_turns
            if participation_rate < 0.3:
                response_score *= 0.5
        
        response_score = min(response_score, 1.0)
        logger.debug(f"Response rate score: {response_score:.2f} (avg length: {avg_length:.0f} chars)")
        return response_score

    @staticmethod
    def calculate(
        user_messages: List[str],
        duration_seconds: int = 0,
        conversation_turns: int = None
    ) -> Dict[str, Any]:
        """Calculate engagement score from conversation metrics."""
        duration_score = EngagementScoreCalculator.calculate_duration_score(duration_seconds)
        questions_score = EngagementScoreCalculator.calculate_questions_score(user_messages)
        objections_score = EngagementScoreCalculator.calculate_objections_handled_score(user_messages)
        response_rate_score = EngagementScoreCalculator.calculate_response_rate_score(
            user_messages,
            conversation_turns
        )
        
        engagement_score = (
            (duration_score * 0.25) +
            (questions_score * 0.25) +
            (objections_score * 0.25) +
            (response_rate_score * 0.25)
        )
        
        engagement_score = max(0.0, min(engagement_score, 1.0))
        
        logger.info(
            f"Engagement Score: {engagement_score:.3f} | "
            f"Duration: {duration_score:.2f}, Questions: {questions_score:.2f}, "
            f"Objections: {objections_score:.2f}, Response: {response_rate_score:.2f}"
        )
        
        return {
            "engagement_score": engagement_score,
            "duration_score": duration_score,
            "questions_score": questions_score,
            "objections_handled_score": objections_score,
            "response_rate_score": response_rate_score,
            "details": {
                "duration_seconds": duration_seconds,
                "num_user_messages": len([m for m in user_messages if m]),
                "conversation_turns": conversation_turns,
                "total_questions": sum(
                    EngagementScoreCalculator.detect_questions(m)
                    for m in user_messages if m
                ),
                "total_objections": EngagementScoreCalculator.detect_objections(user_messages),
            }
        }
