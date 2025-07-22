# Stub file for the AI service integration
import random


class AIService:
    """Simplified AI service for development"""

    def __init__(self):
        pass

    def generate_post_suggestions(self, user, platform):
        """Generate mock post suggestions"""
        suggestions = [
            {"content": "Check out our latest product launch!", "confidence": 0.85},
            {"content": "Happy Monday! Starting the week with some exciting news.", "confidence": 0.78},
            {"content": "Behind the scenes look at our team working hard.", "confidence": 0.72},
        ]
        return suggestions

    def generate_hashtags(self, content, platform):
        """Generate mock hashtags"""
        all_hashtags = [
            "#marketing",
            "#social",
            "#content",
            "#digital",
            "#branding",
            "#strategy",
            "#creativity",
            "#engagement",
            "#media",
            "#trending",
            "#viral",
            "#community",
        ]
        # Return 3-5 random hashtags
        count = random.randint(3, 5)
        return random.sample(all_hashtags, count)

    def analyze_sentiment(self, text):
        """Analyze sentiment of text"""
        sentiments = ["positive", "neutral", "negative"]
        weights = [0.6, 0.3, 0.1]  # More likely to be positive

        return {"sentiment": random.choices(sentiments, weights=weights)[0], "confidence": round(random.uniform(0.7, 0.95), 2)}


# Export the class as default
__all__ = ["AIService"]
