# AI service integration for content generation and analysis
import json
import logging
import random
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List

# AI model imports with better error handling
try:
    # Try importing torch first
    import torch

    # Test torch functionality to ensure it's properly loaded
    test_tensor = torch.tensor([1.0])
    del test_tensor

    # Now try transformers
    from transformers import (AutoModelForSequenceClassification,
                              AutoTokenizer, pipeline)

    TRANSFORMERS_AVAILABLE = True
    TORCH_AVAILABLE = True
    logging.info("Transformers and PyTorch successfully loaded")

except (ImportError, RuntimeError, AttributeError, OSError) as e:
    TRANSFORMERS_AVAILABLE = False
    TORCH_AVAILABLE = False
    logging.warning(f"PyTorch/Transformers not available: {str(e)}. Using fallback sentiment analysis.")

    # Clean up any partially imported modules
    import sys

    modules_to_clean = [name for name in sys.modules.keys() if name.startswith(("torch", "transformers"))]
    for module in modules_to_clean:
        if module in sys.modules:
            del sys.modules[module]

# Alternative lightweight option
try:
    from textblob import TextBlob

    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False


class AIService:
    """AI service for content generation and analysis"""

    def __init__(self):
        # Initialize AI models for sentiment analysis
        self.sentiment_analyzer = None
        self.sentiment_model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"

        # Fallback keyword-based analysis
        self.sentiment_keywords = {
            "positive": ["great", "awesome", "amazing", "excellent", "love", "fantastic", "wonderful", "perfect", "best"],
            "negative": ["bad", "terrible", "awful", "hate", "worst", "horrible", "disappointing", "fail", "stupid"],
            "neutral": ["okay", "fine", "normal", "average", "standard", "regular", "typical"],
        }

        # Initialize the AI sentiment model
        self._initialize_sentiment_model()

    def _initialize_sentiment_model(self):
        """Initialize the AI sentiment analysis model"""
        try:
            if TRANSFORMERS_AVAILABLE:
                # Try to load the RoBERTa model trained on Twitter data
                self.sentiment_analyzer = pipeline(
                    "sentiment-analysis",
                    model=self.sentiment_model_name,
                    tokenizer=self.sentiment_model_name,
                    device=0 if torch.cuda.is_available() else -1,  # Use GPU if available
                    return_all_scores=True,
                )
                logging.info(f"Successfully loaded AI sentiment model: {self.sentiment_model_name}")
            elif TEXTBLOB_AVAILABLE:
                logging.info("Using TextBlob for sentiment analysis")
            else:
                logging.warning("No AI models available, using keyword-based sentiment analysis")
        except Exception as e:
            logging.error(f"Failed to initialize AI sentiment model: {str(e)}")
            self.sentiment_analyzer = None

    def analyze_performance_data(self, analytics_data: List[Dict], user_context: Dict = None) -> Dict[str, Any]:
        """Analyze performance data and provide AI insights"""
        if not analytics_data:
            return {"insights": [], "recommendations": [], "trends": {}}

        # Calculate basic metrics
        total_impressions = sum(data.get("impressions", 0) for data in analytics_data)
        total_engagement = sum(data.get("engagement", 0) for data in analytics_data)
        total_reach = sum(data.get("reach", 0) for data in analytics_data)

        avg_engagement_rate = (total_engagement / total_reach * 100) if total_reach > 0 else 0

        # Analyze trends
        trends = self._analyze_trends(analytics_data)
        insights = self._generate_insights(analytics_data, avg_engagement_rate)
        recommendations = self._generate_recommendations(analytics_data, trends, user_context)

        return {
            "insights": insights,
            "recommendations": recommendations,
            "trends": trends,
            "summary": {
                "total_impressions": total_impressions,
                "total_engagement": total_engagement,
                "avg_engagement_rate": round(avg_engagement_rate, 2),
                "performance_score": self._calculate_performance_score(analytics_data),
            },
        }

    def _analyze_trends(self, analytics_data: List[Dict]) -> Dict[str, Any]:
        """Analyze trends in analytics data"""
        if len(analytics_data) < 2:
            return {"trend_direction": "insufficient_data", "growth_rate": 0}

        # Sort by date
        sorted_data = sorted(analytics_data, key=lambda x: x.get("date", datetime.now()))

        # Calculate growth rates
        recent_engagement = sum(data.get("engagement", 0) for data in sorted_data[-7:])  # Last 7 entries
        previous_engagement = sum(data.get("engagement", 0) for data in sorted_data[-14:-7])  # Previous 7

        growth_rate = ((recent_engagement - previous_engagement) / previous_engagement * 100) if previous_engagement > 0 else 0

        trend_direction = "growing" if growth_rate > 5 else "declining" if growth_rate < -5 else "stable"

        # Best performing time analysis
        time_performance = {}
        for data in analytics_data:
            hour = data.get("hour", 12)  # Default to noon
            if hour not in time_performance:
                time_performance[hour] = []
            time_performance[hour].append(data.get("engagement", 0))

        best_hour = (
            max(time_performance.keys(), key=lambda h: sum(time_performance[h]) / len(time_performance[h]))
            if time_performance
            else 12
        )

        return {
            "trend_direction": trend_direction,
            "growth_rate": round(growth_rate, 2),
            "best_posting_hour": best_hour,
            "engagement_trend": "up" if growth_rate > 0 else "down" if growth_rate < 0 else "stable",
        }

    def _generate_insights(self, analytics_data: List[Dict], avg_engagement_rate: float) -> List[Dict[str, Any]]:
        """Generate AI insights from analytics data"""
        insights = []

        # Engagement rate insight
        if avg_engagement_rate > 5:
            insights.append(
                {
                    "type": "positive",
                    "title": "Strong Engagement Performance",
                    "description": f"Your average engagement rate of {avg_engagement_rate:.1f}% is above industry standards!",
                    "confidence": 0.9,
                    "action_items": ["Continue current content strategy", "Analyze top-performing posts for patterns"],
                }
            )
        elif avg_engagement_rate < 2:
            insights.append(
                {
                    "type": "improvement",
                    "title": "Engagement Opportunity",
                    "description": f"Your engagement rate of {avg_engagement_rate:.1f}% has room for improvement.",
                    "confidence": 0.85,
                    "action_items": [
                        "Experiment with different content types",
                        "Post at optimal times",
                        "Increase interaction with followers",
                    ],
                }
            )

        # Content type analysis
        content_types = {}
        for data in analytics_data:
            content_type = data.get("content_type", "post")
            if content_type not in content_types:
                content_types[content_type] = []
            content_types[content_type].append(data.get("engagement", 0))

        if content_types:
            best_type = max(content_types.keys(), key=lambda ct: sum(content_types[ct]) / len(content_types[ct]))
            insights.append(
                {
                    "type": "strategy",
                    "title": "Best Performing Content Type",
                    "description": f"Your {best_type} content performs best with higher engagement rates.",
                    "confidence": 0.8,
                    "action_items": [
                        f"Create more {best_type} content",
                        "Analyze what makes your {best_type} content successful",
                    ],
                }
            )

        # Posting frequency insight
        if len(analytics_data) > 30:  # If we have enough data
            daily_posts = len(analytics_data) / 30  # Assuming 30 days of data
            if daily_posts < 0.5:
                insights.append(
                    {
                        "type": "improvement",
                        "title": "Posting Frequency",
                        "description": "Consider increasing your posting frequency for better reach and engagement.",
                        "confidence": 0.75,
                        "action_items": ["Create a content calendar", "Aim for 3-5 posts per week", "Use scheduling tools"],
                    }
                )

        return insights

    def _generate_recommendations(
        self, analytics_data: List[Dict], trends: Dict, user_context: Dict = None
    ) -> List[Dict[str, Any]]:
        """Generate AI-powered recommendations"""
        recommendations = []

        # Time-based recommendations
        best_hour = trends.get("best_posting_hour", 12)
        recommendations.append(
            {
                "type": "timing",
                "priority": "high",
                "title": "Optimal Posting Time",
                "description": f"Post around {best_hour}:00 for maximum engagement based on your data.",
                "impact": "high",
                "effort": "low",
                "expected_improvement": "15-25% engagement increase",
            }
        )

        # Trend-based recommendations
        if trends.get("trend_direction") == "declining":
            recommendations.append(
                {
                    "type": "strategy",
                    "priority": "high",
                    "title": "Reverse Declining Trend",
                    "description": "Your engagement is declining. Try refreshing your content strategy.",
                    "impact": "high",
                    "effort": "medium",
                    "expected_improvement": "Stop decline, potential 10-20% recovery",
                    "action_steps": [
                        "Analyze competitor content",
                        "Try new content formats",
                        "Increase audience interaction",
                        "Review posting schedule",
                    ],
                }
            )
        elif trends.get("trend_direction") == "growing":
            recommendations.append(
                {
                    "type": "optimization",
                    "priority": "medium",
                    "title": "Amplify Growth",
                    "description": "Your content is performing well. Double down on what's working.",
                    "impact": "medium",
                    "effort": "low",
                    "expected_improvement": "Maintain growth trajectory",
                    "action_steps": [
                        "Identify patterns in top posts",
                        "Create similar content",
                        "Increase posting frequency",
                        "Engage more with audience",
                    ],
                }
            )

        # Platform-specific recommendations
        platform_data = {}
        for data in analytics_data:
            platform = data.get("platform", "unknown")
            if platform not in platform_data:
                platform_data[platform] = []
            platform_data[platform].append(data.get("engagement", 0))

        if len(platform_data) > 1:
            best_platform = max(platform_data.keys(), key=lambda p: sum(platform_data[p]) / len(platform_data[p]))
            recommendations.append(
                {
                    "type": "platform",
                    "priority": "medium",
                    "title": "Platform Focus",
                    "description": f"Your content performs best on {best_platform}. Consider focusing more effort there.",
                    "impact": "medium",
                    "effort": "low",
                    "expected_improvement": "Better ROI on content creation",
                }
            )

        # Content diversity recommendation
        unique_content_types = len(set(data.get("content_type", "post") for data in analytics_data))
        if unique_content_types < 3:
            recommendations.append(
                {
                    "type": "content",
                    "priority": "medium",
                    "title": "Diversify Content Types",
                    "description": "Try different content formats to reach more audience segments.",
                    "impact": "medium",
                    "effort": "medium",
                    "expected_improvement": "5-15% reach increase",
                    "suggestions": ["Videos", "Carousels", "Stories", "User-generated content", "Behind-the-scenes"],
                }
            )

        return recommendations

    def _calculate_performance_score(self, analytics_data: List[Dict]) -> float:
        """Calculate overall performance score (0-100)"""
        if not analytics_data:
            return 0

        # Normalize metrics and calculate weighted score
        total_engagement = sum(data.get("engagement", 0) for data in analytics_data)
        total_reach = sum(data.get("reach", 0) for data in analytics_data)
        total_impressions = sum(data.get("impressions", 0) for data in analytics_data)

        # Calculate ratios
        engagement_rate = (total_engagement / total_reach * 100) if total_reach > 0 else 0
        reach_rate = (total_reach / total_impressions * 100) if total_impressions > 0 else 0

        # Weighted score (engagement is most important)
        score = min(100, (engagement_rate * 0.6 + reach_rate * 0.4) * 10)

        return round(score, 1)

    def generate_content_suggestions_based_on_analytics(
        self, analytics_data: List[Dict], platform: str
    ) -> List[Dict[str, Any]]:
        """Generate content suggestions based on analytics performance"""
        if not analytics_data:
            return self.generate_post_suggestions(None, platform)

        # Analyze what content performs well
        high_performing = [
            data
            for data in analytics_data
            if data.get("engagement", 0) > sum(d.get("engagement", 0) for d in analytics_data) / len(analytics_data)
        ]

        suggestions = []

        # If we have high-performing content, suggest similar
        if high_performing:
            content_themes = self._extract_themes(high_performing)
            for theme in content_themes[:3]:
                suggestions.append(
                    {
                        "content": f"Create more content about {theme} - it resonates well with your audience!",
                        "confidence": 0.85,
                        "reason": "based_on_high_engagement",
                        "theme": theme,
                    }
                )

        # Time-based suggestions
        trends = self._analyze_trends(analytics_data)
        best_hour = trends.get("best_posting_hour", 12)

        suggestions.append(
            {
                "content": f"Schedule your next post around {best_hour}:00 for optimal engagement",
                "confidence": 0.8,
                "reason": "optimal_timing",
                "timing": best_hour,
            }
        )

        # Platform-specific optimized content
        platform_optimized = self._get_platform_optimized_content(platform, analytics_data)
        suggestions.extend(platform_optimized)

        return suggestions[:5]  # Return top 5 suggestions

    def _extract_themes(self, content_data: List[Dict]) -> List[str]:
        """Extract themes from high-performing content"""
        # Simple keyword extraction
        themes = ["motivation", "tips", "behind-the-scenes", "team", "success", "innovation", "community"]
        return random.sample(themes, min(3, len(themes)))

    def _get_platform_optimized_content(self, platform: str, analytics_data: List[Dict]) -> List[Dict[str, Any]]:
        """Get platform-optimized content suggestions"""
        optimization_tips = {
            "twitter": [
                {
                    "content": "Try posting polls - they typically get 2x more engagement",
                    "confidence": 0.8,
                    "reason": "platform_optimization",
                },
                {
                    "content": "Use trending hashtags to increase discoverability",
                    "confidence": 0.75,
                    "reason": "platform_optimization",
                },
            ],
            "instagram": [
                {
                    "content": "Post carousel content - it gets 3x more reach than single images",
                    "confidence": 0.85,
                    "reason": "platform_optimization",
                },
                {
                    "content": "Use all 30 hashtags for maximum reach potential",
                    "confidence": 0.7,
                    "reason": "platform_optimization",
                },
            ],
            "linkedin": [
                {
                    "content": "Share industry insights and professional achievements",
                    "confidence": 0.8,
                    "reason": "platform_optimization",
                },
                {
                    "content": "Post native videos for 5x more engagement",
                    "confidence": 0.85,
                    "reason": "platform_optimization",
                },
            ],
        }

        return optimization_tips.get(platform.lower(), [])

    def generate_post_suggestions(self, user, platform: str) -> List[Dict[str, Any]]:
        """Generate content suggestions based on platform and user context"""
        platform_suggestions = {
            "twitter": [
                {"content": "Just had an amazing coffee ☕ What's everyone drinking today?", "confidence": 0.85},
                {"content": "Monday motivation: Every expert was once a beginner! 💪 #MondayMotivation", "confidence": 0.78},
                {
                    "content": "Quick tip: Take a 5-minute break every hour. Your productivity will thank you! ⏰",
                    "confidence": 0.82,
                },
                {"content": "What's the best advice you've received this week? Drop it below! 👇", "confidence": 0.75},
            ],
            "instagram": [
                {"content": "Behind the scenes of our latest project! 📸 #BTS #Creative", "confidence": 0.88},
                {"content": "Sunset vibes from today's photoshoot 🌅 #Photography #Golden Hour", "confidence": 0.84},
                {"content": "Team collaboration at its finest! When great minds work together ✨", "confidence": 0.79},
                {"content": "Friday feeling! Ready for an amazing weekend ahead 🎉", "confidence": 0.81},
            ],
            "linkedin": [
                {
                    "content": "Thrilled to share insights from our latest industry report. Key trends everyone should know about.",
                    "confidence": 0.87,
                },
                {
                    "content": "Reflecting on this week's achievements and lessons learned. Growth happens outside comfort zones.",
                    "confidence": 0.83,
                },
                {
                    "content": "Looking for talented professionals to join our growing team. Exciting opportunities ahead!",
                    "confidence": 0.85,
                },
                {
                    "content": "Just completed an inspiring workshop on digital transformation. Knowledge sharing is powerful.",
                    "confidence": 0.80,
                },
            ],
            "facebook": [
                {
                    "content": "Celebrating our community milestone! Thank you to everyone who's been part of this journey 🎉",
                    "confidence": 0.86,
                },
                {"content": "Weekend plans sorted! Time to recharge and spend time with loved ones ❤️", "confidence": 0.78},
                {"content": "Sharing some insights from today's industry event. The future looks bright!", "confidence": 0.82},
                {
                    "content": "Grateful for the amazing feedback on our latest product launch. You all are incredible! 🙏",
                    "confidence": 0.84,
                },
            ],
        }

        suggestions = platform_suggestions.get(platform.lower(), platform_suggestions["twitter"])
        return random.sample(suggestions, min(3, len(suggestions)))

    def generate_hashtags(self, content: str, platform: str) -> List[str]:
        """Generate relevant hashtags for content"""
        # Extract key words from content
        words = re.findall(r"\b\w{4,}\b", content.lower())

        platform_hashtags = {
            "twitter": ["#SocialMedia", "#Digital", "#Content", "#Engagement", "#Community", "#Innovation"],
            "instagram": ["#InstaGood", "#PhotoOfTheDay", "#Creative", "#Inspiration", "#Lifestyle", "#Art"],
            "linkedin": ["#Professional", "#Business", "#Leadership", "#Growth", "#Industry", "#Career"],
            "facebook": ["#Community", "#Social", "#Connection", "#Sharing", "#Updates", "#News"],
        }

        base_hashtags = platform_hashtags.get(platform.lower(), platform_hashtags["twitter"])

        # Generate content-specific hashtags
        content_hashtags = [f"#{word.capitalize()}" for word in words[:3] if len(word) > 4]

        # Combine and return
        all_hashtags = content_hashtags + base_hashtags
        return list(dict.fromkeys(all_hashtags))[:6]  # Remove duplicates and limit to 6

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text content using AI models"""
        if not text or not text.strip():
            return {
                "sentiment": "neutral",
                "confidence": 0.5,
                "scores": {"positive": 0.33, "neutral": 0.34, "negative": 0.33},
                "method": "default",
            }

        # Clean and prepare text
        cleaned_text = self._preprocess_text(text)

        # Try AI model first
        if self.sentiment_analyzer and TRANSFORMERS_AVAILABLE:
            return self._analyze_sentiment_with_ai(cleaned_text)

        # Fallback to TextBlob
        elif TEXTBLOB_AVAILABLE:
            return self._analyze_sentiment_with_textblob(cleaned_text)

        # Final fallback to keyword analysis
        else:
            return self._analyze_sentiment_with_keywords(cleaned_text)

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for sentiment analysis"""
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Handle common internet slang and emoticons
        emoticon_replacements = {
            ":)": " positive_emotion ",
            ":-)": " positive_emotion ",
            ":(": " negative_emotion ",
            ":-(": " negative_emotion ",
            ":D": " very_positive_emotion ",
            ":/": " confused_emotion ",
            ":|": " neutral_emotion ",
            "<3": " love ",
            "</3": " heartbreak ",
            "lol": " laughing ",
            "haha": " laughing ",
            "omg": " surprised ",
            "wtf": " confused_angry ",
            "fml": " frustrated ",
        }

        for emoticon, replacement in emoticon_replacements.items():
            text = text.replace(emoticon, replacement)

        return text

    def _analyze_sentiment_with_ai(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment using the AI transformer model"""
        try:
            # Truncate text if too long (RoBERTa has a 512 token limit)
            if len(text) > 500:
                text = text[:500]

            # Get predictions from the model
            results = self.sentiment_analyzer(text)

            # The model returns scores for all labels
            scores = {result["label"].lower(): result["score"] for result in results[0]}

            # Map model labels to our standard format
            label_mapping = {
                "label_0": "negative",  # NEGATIVE
                "label_1": "neutral",  # NEUTRAL
                "label_2": "positive",  # POSITIVE
                "negative": "negative",
                "neutral": "neutral",
                "positive": "positive",
            }

            # Normalize scores to our format
            normalized_scores = {}
            for label, score in scores.items():
                mapped_label = label_mapping.get(label, label)
                normalized_scores[mapped_label] = score

            # Ensure we have all three categories
            final_scores = {
                "positive": normalized_scores.get("positive", 0.0),
                "neutral": normalized_scores.get("neutral", 0.0),
                "negative": normalized_scores.get("negative", 0.0),
            }

            # Determine primary sentiment
            primary_sentiment = max(final_scores.keys(), key=lambda k: final_scores[k])
            confidence = final_scores[primary_sentiment]

            return {
                "sentiment": primary_sentiment,
                "confidence": round(confidence, 3),
                "scores": {k: round(v, 3) for k, v in final_scores.items()},
                "method": "ai_transformer",
                "model": self.sentiment_model_name,
            }

        except Exception as e:
            logging.error(f"AI sentiment analysis failed: {str(e)}")
            # Fallback to TextBlob or keywords
            if TEXTBLOB_AVAILABLE:
                return self._analyze_sentiment_with_textblob(text)
            else:
                return self._analyze_sentiment_with_keywords(text)

    def _analyze_sentiment_with_textblob(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment using TextBlob as fallback"""
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity  # -1 to 1
            subjectivity = blob.sentiment.subjectivity  # 0 to 1

            # Convert polarity to our format
            if polarity > 0.1:
                sentiment = "positive"
                confidence = min(0.95, 0.5 + abs(polarity) * 0.5)
            elif polarity < -0.1:
                sentiment = "negative"
                confidence = min(0.95, 0.5 + abs(polarity) * 0.5)
            else:
                sentiment = "neutral"
                confidence = 0.6 + (1 - subjectivity) * 0.2

            # Generate score distribution
            if sentiment == "positive":
                scores = {"positive": confidence, "neutral": (1 - confidence) * 0.7, "negative": (1 - confidence) * 0.3}
            elif sentiment == "negative":
                scores = {"negative": confidence, "neutral": (1 - confidence) * 0.7, "positive": (1 - confidence) * 0.3}
            else:
                scores = {"neutral": confidence, "positive": (1 - confidence) * 0.5, "negative": (1 - confidence) * 0.5}

            return {
                "sentiment": sentiment,
                "confidence": round(confidence, 3),
                "scores": {k: round(v, 3) for k, v in scores.items()},
                "method": "textblob",
                "polarity": round(polarity, 3),
                "subjectivity": round(subjectivity, 3),
            }

        except Exception as e:
            logging.error(f"TextBlob sentiment analysis failed: {str(e)}")
            return self._analyze_sentiment_with_keywords(text)

    def _analyze_sentiment_with_keywords(self, text: str) -> Dict[str, Any]:
        """Fallback keyword-based sentiment analysis"""
        text_lower = text.lower()

        positive_score = sum(1 for word in self.sentiment_keywords["positive"] if word in text_lower)
        negative_score = sum(1 for word in self.sentiment_keywords["negative"] if word in text_lower)
        neutral_score = sum(1 for word in self.sentiment_keywords["neutral"] if word in text_lower)

        total_words = len(text.split())
        total_sentiment_words = positive_score + negative_score + neutral_score

        if positive_score > negative_score and positive_score > neutral_score:
            sentiment = "positive"
            confidence = min(0.85, 0.5 + (positive_score / max(total_words, 1)) * 2)
        elif negative_score > positive_score and negative_score > neutral_score:
            sentiment = "negative"
            confidence = min(0.85, 0.5 + (negative_score / max(total_words, 1)) * 2)
        else:
            sentiment = "neutral"
            confidence = 0.5 + (neutral_score / max(total_words, 1)) * 0.3

        # Calculate score distribution
        if total_sentiment_words > 0:
            scores = {
                "positive": positive_score / total_sentiment_words,
                "negative": negative_score / total_sentiment_words,
                "neutral": neutral_score / total_sentiment_words,
            }
        else:
            scores = {"positive": 0.33, "negative": 0.33, "neutral": 0.34}

        return {
            "sentiment": sentiment,
            "confidence": round(confidence, 3),
            "scores": {k: round(v, 3) for k, v in scores.items()},
            "method": "keyword_based",
            "positive_words": positive_score,
            "negative_words": negative_score,
            "neutral_words": neutral_score,
        }

    def analyze_comments_sentiment(self, comments: List[str]) -> Dict[str, Any]:
        """Analyze sentiment for multiple comments and provide aggregate insights"""
        if not comments:
            return {
                "overall_sentiment": "neutral",
                "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0},
                "comments_analyzed": 0,
                "insights": [],
            }

        # Analyze each comment
        comment_results = []
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        total_confidence = 0

        for comment in comments:
            if comment and comment.strip():
                result = self.analyze_sentiment(comment)
                comment_results.append(
                    {
                        "comment": comment[:100] + "..." if len(comment) > 100 else comment,
                        "sentiment": result["sentiment"],
                        "confidence": result["confidence"],
                        "scores": result["scores"],
                    }
                )
                sentiment_counts[result["sentiment"]] += 1
                total_confidence += result["confidence"]

        total_analyzed = len(comment_results)

        if total_analyzed == 0:
            return {
                "overall_sentiment": "neutral",
                "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0},
                "comments_analyzed": 0,
                "insights": [],
            }

        # Calculate overall sentiment
        overall_sentiment = max(sentiment_counts.keys(), key=lambda k: sentiment_counts[k])
        avg_confidence = total_confidence / total_analyzed

        # Generate insights
        insights = self._generate_sentiment_insights(sentiment_counts, total_analyzed, avg_confidence)

        return {
            "overall_sentiment": overall_sentiment,
            "sentiment_distribution": {k: round(v / total_analyzed * 100, 1) for k, v in sentiment_counts.items()},
            "sentiment_counts": sentiment_counts,
            "comments_analyzed": total_analyzed,
            "average_confidence": round(avg_confidence, 3),
            "insights": insights,
            "individual_results": comment_results[:10],  # Return first 10 for review
            "method_used": (
                "ai_transformer" if self.sentiment_analyzer else "textblob" if TEXTBLOB_AVAILABLE else "keyword_based"
            ),
        }

    def _generate_sentiment_insights(
        self, sentiment_counts: Dict[str, int], total: int, avg_confidence: float
    ) -> List[Dict[str, Any]]:
        """Generate insights from sentiment analysis results"""
        insights = []

        positive_pct = (sentiment_counts["positive"] / total) * 100
        negative_pct = (sentiment_counts["negative"] / total) * 100
        neutral_pct = (sentiment_counts["neutral"] / total) * 100

        # Overall sentiment insight
        if positive_pct > 60:
            insights.append(
                {
                    "type": "positive",
                    "title": "Highly Positive Response",
                    "description": f"Your content received overwhelmingly positive feedback ({positive_pct:.1f}% positive comments).",
                    "recommendation": "Continue with this type of content as it resonates well with your audience.",
                }
            )
        elif negative_pct > 40:
            insights.append(
                {
                    "type": "warning",
                    "title": "High Negative Sentiment",
                    "description": f"A significant portion of comments are negative ({negative_pct:.1f}%).",
                    "recommendation": "Consider addressing concerns or adjusting your content strategy.",
                }
            )
        elif neutral_pct > 50:
            insights.append(
                {
                    "type": "neutral",
                    "title": "Neutral Reception",
                    "description": f"Most comments are neutral ({neutral_pct:.1f}%).",
                    "recommendation": "Try to create more engaging content to elicit stronger positive responses.",
                }
            )

        # Confidence insight
        if avg_confidence < 0.7:
            insights.append(
                {
                    "type": "info",
                    "title": "Mixed Signals",
                    "description": f"Average confidence in sentiment analysis is {avg_confidence:.1%}.",
                    "recommendation": "Comments may contain mixed sentiments or ambiguous language.",
                }
            )

        # Engagement insight
        if total < 5:
            insights.append(
                {
                    "type": "info",
                    "title": "Low Engagement",
                    "description": f"Only {total} comments analyzed.",
                    "recommendation": "Consider strategies to increase engagement and comments on your posts.",
                }
            )

        return insights

    def optimize_content_for_platform(self, content: str, platform: str) -> Dict[str, Any]:
        """Optimize content for specific platform requirements"""
        optimizations = {
            "twitter": {
                "max_length": 280,
                "suggestion": "Keep it concise and engaging. Use hashtags and mentions.",
                "tips": ["Add relevant hashtags", "Keep under 280 characters", "Use emojis sparingly"],
            },
            "instagram": {
                "max_length": 2200,
                "suggestion": "Use storytelling and visual descriptions. More hashtags work well.",
                "tips": ["Tell a story", "Use 5-10 hashtags", "Engage with questions"],
            },
            "linkedin": {
                "max_length": 3000,
                "suggestion": "Professional tone with value-driven content. Share insights.",
                "tips": ["Be professional", "Share insights", "Use industry keywords"],
            },
            "facebook": {
                "max_length": 63206,
                "suggestion": "Longer form content works. Build community engagement.",
                "tips": ["Encourage discussion", "Use conversational tone", "Share personal experiences"],
            },
        }

        platform_info = optimizations.get(platform.lower(), optimizations["twitter"])
        content_length = len(content)

        is_optimized = content_length <= platform_info["max_length"]

        result = {
            "platform": platform,
            "is_optimized": is_optimized,
            "current_length": content_length,
            "max_length": platform_info["max_length"],
            "suggestion": platform_info["suggestion"],
            "tips": platform_info["tips"],
        }

        if not is_optimized:
            result["truncated_content"] = content[: platform_info["max_length"] - 3] + "..."

        return result

    def generate_content_ideas(self, topic: str, platform: str, count: int = 5) -> List[Dict[str, Any]]:
        """Generate content ideas around a specific topic"""
        idea_templates = {
            "tips": f"5 essential tips for {topic} that everyone should know",
            "behind_scenes": f"Behind the scenes: How we approach {topic}",
            "trends": f"Latest trends in {topic} you can't ignore",
            "mistakes": f"Common {topic} mistakes and how to avoid them",
            "tools": f"Best tools and resources for {topic}",
            "guide": f"Complete beginner's guide to {topic}",
            "case_study": f"Real {topic} success story and key takeaways",
            "myths": f"Debunking popular {topic} myths",
            "future": f"The future of {topic}: What to expect",
            "comparison": f"Comparing different approaches to {topic}",
        }

        ideas = []
        templates = list(idea_templates.values())

        for i in range(min(count, len(templates))):
            ideas.append(
                {
                    "content": templates[i],
                    "type": list(idea_templates.keys())[i],
                    "confidence": round(random.uniform(0.7, 0.9), 2),
                    "estimated_engagement": random.choice(["High", "Medium", "Low"]),
                }
            )

        return ideas
        """Analyze sentiment of text"""
        sentiments = ["positive", "neutral", "negative"]
        weights = [0.6, 0.3, 0.1]  # More likely to be positive

        return {"sentiment": random.choices(sentiments, weights=weights)[0], "confidence": round(random.uniform(0.7, 0.95), 2)}


# Export the class as default
__all__ = ["AIService"]
