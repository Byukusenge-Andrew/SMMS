# AI service integration for content generation and analysis
import json
import logging
import os
import requests
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
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

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
        # Ensure GEMINI_API_KEY is populated in os.environ from .env (via decouple)
        if not os.getenv("GEMINI_API_KEY"):
            try:
                from decouple import config
                key = config("GEMINI_API_KEY", default=None)
                if key:
                    os.environ["GEMINI_API_KEY"] = key
            except Exception:
                pass

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

    def _call_gemini(self, prompt: str, system_instruction: str = None, json_mode: bool = False, temperature: float = None) -> str:
        """Call the Google Gemini API using raw HTTP requests"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logging.warning("GEMINI_API_KEY not found in environment, skipping Gemini API call.")
            return ""

        # Using gemini-2.5-flash which is a free model with active quotas
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

        contents = {
            "parts": [
                {"text": prompt}
            ]
        }

        payload = {
            "contents": [contents],
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        generation_config = {}
        if json_mode:
            generation_config["responseMimeType"] = "application/json"
        if temperature is not None:
            generation_config["temperature"] = temperature

        if generation_config:
            payload["generationConfig"] = generation_config

        try:
            logging.info("Sending request to Gemini API...")
            response = requests.post(url, json=payload, timeout=25)
            if response.status_code == 200:
                res_json = response.json()
                text = res_json["candidates"][0]["content"]["parts"][0]["text"]
                return text
            else:
                logging.error(f"Gemini API returned error {response.status_code}: {response.text}")
                return ""
        except Exception as e:
            logging.error(f"Error calling Gemini API: {str(e)}")
            return ""

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
        self, analytics_data: List[Dict], platform: str, agent=None, content: str = None
    ) -> List[Dict[str, Any]]:
        """Generate content suggestions based on analytics performance"""
        if not analytics_data:
            return self.generate_post_suggestions(None, platform, agent=agent, content=content)

        # Try Gemini API if key is available
        if os.getenv("GEMINI_API_KEY"):
            # Prepare summary of analytics to give as context to Gemini
            analytics_summary = f"Platform: {platform}. Total records: {len(analytics_data)}. "
            engagements = [d.get("engagement", 0) for d in analytics_data if d.get("engagement") is not None]
            avg_eng = sum(engagements)/len(engagements) if engagements else 0
            analytics_summary += f"Average Engagement: {avg_eng:.1f}. "
            
            system_instruction = None
            temp = None
            tone_str = ""
            if agent:
                system_instruction = agent.persona
                temp = agent.temperature
                tone_str = f" Ensure the suggestions reflect a '{agent.tone}' tone."
            else:
                system_instruction = "You are an expert Social Media AI Planner."

            content_str = f" based on the user's draft/prompt: \"{content}\"" if content else ""
            prompt = f"""
            Analyze the following analytics summary of a user's performance and generate exactly 4 ready-to-publish, high-performing post suggestions tailored for {platform}{content_str}.{tone_str}
            
            Performance Summary: {analytics_summary}
            
            Provide the response in raw JSON format as a list of objects, where each object has:
            - "content": The full post text (make sure it is a complete, publish-ready post containing engaging body copy, emojis, and hashtags where appropriate, not just a recommendation or one-sentence suggestion).
            - "confidence": A float between 0.5 and 0.99.
            - "reason": A brief reason identifier (e.g. "based_on_high_engagement", "optimal_timing").
            
            Do not include any markdown formatting like ```json in the output. Return only raw valid JSON list.
            """
            
            res_text = self._call_gemini(prompt, system_instruction=system_instruction, json_mode=True, temperature=temp)
            if res_text:
                try:
                    res_text = res_text.strip()
                    if res_text.startswith("```json"):
                        res_text = res_text.split("```json")[1].split("```")[0].strip()
                    elif res_text.startswith("```"):
                        res_text = res_text.split("```")[1].split("```")[0].strip()
                    data = json.loads(res_text)
                    if isinstance(data, list):
                        return data[:5]
                except Exception as e:
                    logging.error(f"Failed to parse Gemini analytics suggestions: {str(e)}")

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
            theme_posts = [
                (
                    "motivation",
                    "🔥 Success doesn't happen overnight — it's built one consistent action at a time.\n\nWhether you're just starting out or scaling up, the key is to stay focused, keep learning, and never stop showing up. Your audience is watching, and your story matters more than you think.\n\n💬 Drop a comment below: What's the ONE habit that changed everything for you?\n\n#Motivation #GrowthMindset #SuccessStory #Consistency #Entrepreneurship"
                ),
                (
                    "tips",
                    "✅ 5 quick wins to level up your content game this week:\n\n1️⃣ Post at peak hours when your audience is most active\n2️⃣ Use a strong hook in your first line — make them stop scrolling\n3️⃣ Add a clear call-to-action at the end of every post\n4️⃣ Engage with comments within the first 30 minutes of posting\n5️⃣ Repurpose your best-performing content across platforms\n\nWhich of these are you already doing? Let us know 👇\n\n#SocialMediaTips #ContentStrategy #DigitalMarketing #GrowthHacks"
                ),
                (
                    "behind-the-scenes",
                    "👀 Ever wonder what goes on behind the scenes?\n\nWe're pulling back the curtain today! From brainstorming ideas at 7am to scheduling posts and analysing performance, building a strong social media presence takes real work — and we love every minute of it.\n\nHere's what our typical content day looks like 👇\n🕖 Morning: Research & ideation\n🕛 Noon: Content creation & design\n🕒 Afternoon: Scheduling & engagement\n🕕 Evening: Analytics review\n\nWhat does YOUR content routine look like? Share below! 💡\n\n#BehindTheScenes #ContentCreation #DayInTheLife #SocialMediaManager"
                ),
                (
                    "team",
                    "🤝 Great content starts with great people.\n\nOur team is the secret sauce behind everything we do. From designers and writers to strategists and analysts — every role matters, and every voice shapes our brand.\n\nThis week, we're celebrating the unsung heroes who make the magic happen behind every post, every campaign, every milestone.\n\n💬 Tag a teammate who goes above and beyond! ⬇️\n\n#TeamWork #CompanyCulture #PeopleFirst #BehindTheBrand #Gratitude"
                ),
                (
                    "innovation",
                    "🚀 The future belongs to those who adapt.\n\nIn a world where platforms change overnight and trends shift by the hour, the brands that win are those willing to experiment, learn fast, and pivot without fear.\n\nHere's what we've been testing this quarter:\n✅ AI-assisted content drafts\n✅ Cross-platform scheduling automation\n✅ Audience sentiment analysis\n\nThe results? Game-changing. 📊\n\nWhat innovations are YOU exploring in your social strategy? Drop your thoughts below 👇\n\n#Innovation #AIMarketing #FutureOfSocial #DigitalStrategy #Automation"
                ),
                (
                    "community",
                    "💙 This community is what drives everything we do.\n\nEvery like, comment, share, and DM reminds us why we show up every single day. You're not just followers — you're partners in this journey.\n\nWe started with a simple idea: make meaningful connections online. And thanks to each of you, that idea has grown into something far bigger than we ever imagined.\n\nThank you. Truly. 🙏\n\nWhat's been your favourite thing about being part of this community? Tell us below 💬\n\n#CommunityFirst #Grateful #ThankYou #BuildingTogether #SocialMedia"
                ),
            ]
            for theme in content_themes[:3]:
                post_text = next((p for t, p in theme_posts if t == theme), theme_posts[0][1])
                suggestions.append(
                    {
                        "content": post_text,
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
                "content": (
                    f"⏰ Timing is EVERYTHING on social media.\n\n"
                    f"Our analytics show that posting around {best_hour}:00 consistently delivers the highest engagement for our audience — more eyes, more clicks, more conversations.\n\n"
                    f"Are you posting at the right time? Here's a quick checklist:\n"
                    f"✅ Know your audience's timezone\n"
                    f"✅ Test different posting windows weekly\n"
                    f"✅ Use scheduling tools so you never miss peak hours\n"
                    f"✅ Review your analytics monthly and adjust\n\n"
                    f"💬 What time of day gets the best response for YOU? Drop it in the comments!\n\n"
                    f"#SocialMediaStrategy #Timing #ContentPlanning #Analytics #GrowthTips"
                ),
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
                    "content": (
                        "📊 Did you know Twitter polls can get up to 2x more engagement than a regular tweet?\n\n"
                        "We decided to put it to the test this week, and the results blew us away. People LOVE sharing their opinions — and it's one of the easiest ways to spark a conversation with your audience.\n\n"
                        "🗳️ Here's a quick poll for you:\n"
                        "What type of content do you enjoy most?\n"
                        "A) Tips & tutorials\n"
                        "B) Behind-the-scenes\n"
                        "C) Industry news\n"
                        "D) Memes & humor\n\n"
                        "Vote below and let us know! 👇 #TwitterMarketing #ContentStrategy #Engagement"
                    ),
                    "confidence": 0.8,
                    "reason": "platform_optimization",
                },
                {
                    "content": (
                        "🔥 Trending now — and here's why it matters for YOUR brand.\n\n"
                        "Jumping on trending hashtags isn't just about visibility. It's about showing up where the conversation already is — meeting your audience in the moment they're most engaged.\n\n"
                        "Here's how to do it without looking out of place:\n"
                        "✅ Make sure the trend is relevant to your niche\n"
                        "✅ Add genuine value — don't just slap a hashtag and go\n"
                        "✅ Act fast — trending windows are short on Twitter\n"
                        "✅ Engage with others using the same tag\n\n"
                        "Are you using trending hashtags strategically? 🤔 #TwitterGrowth #HashtagStrategy #SocialMediaTips"
                    ),
                    "confidence": 0.75,
                    "reason": "platform_optimization",
                },
            ],
            "instagram": [
                {
                    "content": (
                        "🎠 Carousels are having a MOMENT on Instagram — and your brand should be riding the wave.\n\n"
                        "Studies show carousel posts get up to 3x more reach than single images. Why? Because every swipe is a new chance to hook your audience — and the algorithm rewards the extra time people spend on your content.\n\n"
                        "Here's a carousel formula that works every time:\n"
                        "Slide 1️⃣: Bold hook or question\n"
                        "Slides 2–5️⃣: Value-packed tips or story beats\n"
                        "Last slide: Clear CTA (save, share, comment, follow)\n\n"
                        "Are you using carousels yet? Drop a 🔥 in the comments if you want us to break this down further!\n\n"
                        "#InstagramGrowth #CarouselPost #ContentStrategy #InstagramTips #Reels"
                    ),
                    "confidence": 0.85,
                    "reason": "platform_optimization",
                },
                {
                    "content": (
                        "#️⃣ Let's talk hashtags — because most people are using them WRONG on Instagram.\n\n"
                        "The platform allows up to 30 hashtags per post, but it's not just about quantity. It's about relevance, reach, and rotation.\n\n"
                        "Here's the winning formula we recommend:\n"
                        "🔹 5 niche-specific hashtags (small, loyal communities)\n"
                        "🔹 10 mid-range hashtags (100K–500K posts)\n"
                        "🔹 10 broad hashtags (trending, high-volume)\n"
                        "🔹 5 branded or campaign-specific hashtags\n\n"
                        "Rotate your sets weekly to avoid shadowban risk and keep discovery fresh.\n\n"
                        "Save this post for your next upload! 💾 #InstagramHashtags #ReachMore #IGStrategy #ContentCreator"
                    ),
                    "confidence": 0.7,
                    "reason": "platform_optimization",
                },
            ],
            "linkedin": [
                {
                    "content": (
                        "💼 The posts that perform best on LinkedIn aren't the polished press releases — they're the honest, human stories.\n\n"
                        "Share what you've learned. Share what you've failed at. Share what surprised you this quarter. Industry insights and real professional experiences resonate far more than corporate speak.\n\n"
                        "Here's a simple format that consistently outperforms on LinkedIn:\n"
                        "📌 Open with a bold statement or counterintuitive opinion\n"
                        "📌 Share your personal experience or data point\n"
                        "📌 Give your audience 3 actionable takeaways\n"
                        "📌 End with a question to drive comments\n\n"
                        "What's the best professional lesson you've learned this year? Share below 👇\n\n"
                        "#LinkedIn #ThoughtLeadership #ProfessionalGrowth #B2BMarketing #Networking"
                    ),
                    "confidence": 0.8,
                    "reason": "platform_optimization",
                },
                {
                    "content": (
                        "🎥 Native video on LinkedIn gets 5x more engagement than any other content type — and most brands are still sleeping on it.\n\n"
                        "You don't need a production crew. You don't need a studio. You need a clear message, a phone camera, and 60–90 seconds of your time.\n\n"
                        "Here's what makes LinkedIn video WORK:\n"
                        "✅ Always add subtitles (85% of viewers watch on mute)\n"
                        "✅ Front-load your key message in the first 5 seconds\n"
                        "✅ Upload directly to LinkedIn — don't link from YouTube\n"
                        "✅ End with a genuine question to spark discussion\n\n"
                        "Have you tried native LinkedIn video yet? What was your experience? 💬\n\n"
                        "#LinkedInVideo #VideoMarketing #LinkedInGrowth #ContentMarketing #B2B"
                    ),
                    "confidence": 0.85,
                    "reason": "platform_optimization",
                },
            ],
        }

        return optimization_tips.get(platform.lower(), [])

    # ──────────────────────────────────────────────────────────────────────
    #  Helper: robust JSON extraction from Gemini text
    # ──────────────────────────────────────────────────────────────────────
    def _parse_json_response(self, raw_text: str):
        """Safely extract JSON from a Gemini response, handling markdown fences."""
        if not raw_text:
            return None
        text = raw_text.strip()
        # Strip markdown code fences if present
        if text.startswith("```json"):
            text = text.split("```json", 1)[1].rsplit("```", 1)[0].strip()
        elif text.startswith("```"):
            text = text.split("```", 1)[1].rsplit("```", 1)[0].strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logging.error(f"JSON parse error: {e} — raw text: {text[:200]}")
            return None

    # ──────────────────────────────────────────────────────────────────────
    #  Main dispatcher
    # ──────────────────────────────────────────────────────────────────────
    def generate_post_suggestions(self, user, platform: str, agent=None, content: str = None) -> List[Dict[str, Any]]:
        """Generate content suggestions based on platform and user context.

        When a custom **AIAgent** is provided the method runs the *deliberative*
        pipeline (Plan → Write → Review) for higher-quality output.  Otherwise
        the fast *reactive* single-step path is used.
        """
        if not os.getenv("GEMINI_API_KEY"):
            return self._fallback_post_suggestions(platform)

        # Deliberative mode when a custom agent is attached
        if agent:
            try:
                result = self._generate_post_suggestions_deliberative(platform, agent, content=content)
                if result:
                    return result
                logging.warning("Deliberative pipeline returned empty — falling back to reactive.")
            except Exception as e:
                logging.error(f"Deliberative pipeline failed: {e} — falling back to reactive.")

        # Default reactive single-call path
        return self._generate_post_suggestions_reactive(platform, agent, content=content)

    # ──────────────────────────────────────────────────────────────────────
    #  Reactive (single-step) generation
    # ──────────────────────────────────────────────────────────────────────
    def _generate_post_suggestions_reactive(self, platform: str, agent=None, content: str = None) -> List[Dict[str, Any]]:
        """Single Gemini call — fast, good-enough suggestions."""
        system_instruction = "You are a social media copywriter."
        temp = None
        tone_str = ""
        if agent:
            system_instruction = agent.persona
            temp = agent.temperature
            tone_str = f" Ensure they reflect a '{agent.tone}' tone and match the agent instructions."

        base_prompt = ""
        if content:
            base_prompt = f"based on this draft/idea: \"{content}\""
        else:
            base_prompt = "general posts"

        prompt = f"""
        Generate 3 creative, engaging, and high-performing posts tailored for {platform} {base_prompt}.{tone_str}
        Ensure they match the platform tone and styling conventions.
        Each post must be a complete, fully-written, publish-ready social media post (do NOT return just a single sentence suggestion or recommendation, but write a whole post with hooks, body text, emojis, and call-to-actions where appropriate).

        Provide the response in raw JSON format as a list of objects, where each object has:
        - "content": The full post content (use emojis where appropriate).
        - "confidence": A float between 0.7 and 0.99.

        Do not include any markdown formatting like ```json in the output. Return only raw valid JSON list.
        """
        res_text = self._call_gemini(prompt, system_instruction=system_instruction, json_mode=True, temperature=temp)
        data = self._parse_json_response(res_text)
        if isinstance(data, list) and data:
            return data[:3]

        return self._fallback_post_suggestions(platform)

    # ──────────────────────────────────────────────────────────────────────
    #  Deliberative (Plan → Write → Review) pipeline
    # ──────────────────────────────────────────────────────────────────────
    def _generate_post_suggestions_deliberative(self, platform: str, agent, content: str = None) -> List[Dict[str, Any]]:
        """Multi-step agent pipeline inspired by ReAct / Google ADK patterns.

        Step 1 – **Plan**: Generate a structured content plan (topics, hooks, CTA)
        Step 2 – **Write**: Draft 3 full posts grounded in the plan
        Step 3 – **Review**: Self-critique and refine the drafts
        """
        logging.info(f"🤖 Deliberative Agent [{agent.name}] — starting pipeline for {platform}")

        # ── Step 1: PLAN ────────────────────────────────────────────────
        plan_system = (
            f"You are '{agent.name}', a planning specialist. "
            f"Your persona: {agent.persona}\n"
            f"Your writing tone is '{agent.tone}'.\n"
            "Your job is to create a structured content plan that will guide the writing of 3 social media posts."
        )

        base_plan_prompt = ""
        if content:
            base_plan_prompt = f"based on the following content draft/idea: \"{content}\""
        else:
            base_plan_prompt = "high-performing posts"

        plan_prompt = f"""
Create a content plan for 3 high-performing {platform} posts {base_plan_prompt}.

For each post idea, provide:
- "topic": A concise topic / angle
- "hook": The opening hook strategy (question, bold statement, story, statistic, etc.)
- "key_message": The core message or value proposition
- "cta": A call-to-action or engagement driver
- "hashtag_strategy": 2-3 suggested hashtag themes
- "format_notes": Any formatting recommendations specific to {platform}

Return a JSON object:
{{
  "platform": "{platform}",
  "plan": [
    {{
      "topic": "...",
      "hook": "...",
      "key_message": "...",
      "cta": "...",
      "hashtag_strategy": ["...", "..."],
      "format_notes": "..."
    }}
  ]
}}

Return only raw valid JSON, no markdown fences.
"""
        plan_text = self._call_gemini(
            plan_prompt,
            system_instruction=plan_system,
            json_mode=True,
            temperature=max(0.3, (agent.temperature or 0.7) - 0.2),  # slightly lower temp for planning
        )
        plan_data = self._parse_json_response(plan_text)

        if not plan_data or not isinstance(plan_data.get("plan"), list):
            logging.error("Deliberative Agent — Step 1 (Plan) failed or returned invalid JSON.")
            return []

        plan_items = plan_data["plan"][:3]
        logging.info(f"🤖 Deliberative Agent [{agent.name}] — Plan created: {len(plan_items)} topics")

        # ── Step 2: WRITE ───────────────────────────────────────────────
        write_system = (
            f"You are '{agent.name}', a content writer. "
            f"Your persona: {agent.persona}\n"
            f"Your writing tone is '{agent.tone}'.\n"
            "You must write posts that precisely follow the content plan provided."
        )

        plan_summary = json.dumps(plan_items, indent=2)
        write_prompt = f"""
Based on the following content plan, write exactly {len(plan_items)} complete, publish-ready {platform} posts.

=== CONTENT PLAN ===
{plan_summary}
====================

Requirements:
- Each post must follow its plan item's topic, hook, key message, CTA, and formatting guidance.
- Use emojis where appropriate for {platform}.
- Include relevant hashtags based on the hashtag strategy.
- Respect {platform} character limits and conventions.
- Make each post unique, complete, and engaging (not a brief suggestion, but the full content of the post).

Return a JSON list of objects:
[
  {{
    "content": "The full post text ready to publish",
    "confidence": 0.85,
    "plan_topic": "The topic from the plan this post addresses"
  }}
]

Return only raw valid JSON, no markdown fences.
"""
        write_text = self._call_gemini(
            write_prompt,
            system_instruction=write_system,
            json_mode=True,
            temperature=agent.temperature or 0.7,
        )
        drafts = self._parse_json_response(write_text)

        if not isinstance(drafts, list) or not drafts:
            logging.error("Deliberative Agent — Step 2 (Write) failed or returned invalid JSON.")
            return []

        logging.info(f"🤖 Deliberative Agent [{agent.name}] — Drafts written: {len(drafts)} posts")

        # ── Step 3: REVIEW ──────────────────────────────────────────────
        review_system = (
            f"You are '{agent.name}', acting as a senior content editor and quality reviewer. "
            f"Your persona: {agent.persona}\n"
            f"Your tone standard is '{agent.tone}'.\n"
            "Your job is to review draft posts, improve them if needed, and score their quality."
        )

        drafts_json = json.dumps(drafts, indent=2)
        review_prompt = f"""
Review these {platform} post drafts and improve them. For each post:
1. Fix any awkward phrasing, grammar, or tone inconsistencies.
2. Ensure the hook is strong and attention-grabbing.
3. Verify the CTA drives engagement.
4. Optimize for {platform} best practices.
5. Ensure each draft is expanded into a complete, ready-to-publish post (NOT a single sentence recommendation).
6. Assign a final confidence score (0.7 - 0.99) based on expected performance.

=== DRAFT POSTS ===
{drafts_json}
====================

Return the final polished posts as a JSON list:
[
  {{
    "content": "The final polished post text",
    "confidence": 0.92,
    "agent_name": "{agent.name}",
    "generation_method": "deliberative",
    "plan_topic": "The topic this post addresses"
  }}
]

Return only raw valid JSON, no markdown fences.
"""
        review_text = self._call_gemini(
            review_prompt,
            system_instruction=review_system,
            json_mode=True,
            temperature=max(0.2, (agent.temperature or 0.7) - 0.3),  # lower temp for editing
        )
        final_posts = self._parse_json_response(review_text)

        if not isinstance(final_posts, list) or not final_posts:
            # If review step fails, fall back to the unreviewed drafts
            logging.warning("Deliberative Agent — Step 3 (Review) failed — using raw drafts.")
            for draft in drafts:
                draft["agent_name"] = agent.name
                draft["generation_method"] = "deliberative_unreviewed"
                # Match plans to drafts
                topic = draft.get("plan_topic", "")
                matched_plan = None
                if topic:
                    for item in plan_items:
                        if item.get("topic", "").lower() in topic.lower() or topic.lower() in item.get("topic", "").lower():
                            matched_plan = item
                            break
                if not matched_plan and len(plan_items) > 0:
                    matched_plan = plan_items[0]
                if matched_plan:
                    draft["plan"] = matched_plan
            return drafts[:3]

        # Match plans to final polished posts
        for post in final_posts:
            post["agent_name"] = agent.name
            post["generation_method"] = "deliberative"
            topic = post.get("plan_topic", "")
            matched_plan = None
            if topic:
                for item in plan_items:
                    if item.get("topic", "").lower() in topic.lower() or topic.lower() in item.get("topic", "").lower():
                        matched_plan = item
                        break
            if not matched_plan and len(plan_items) > 0:
                matched_plan = plan_items[0]
            if matched_plan:
                post["plan"] = matched_plan

        logging.info(
            f"🤖 Deliberative Agent [{agent.name}] — Review complete: {len(final_posts)} polished posts"
        )
        return final_posts[:3]

    # ──────────────────────────────────────────────────────────────────────
    #  Static fallback suggestions (no API key / offline)
    # ──────────────────────────────────────────────────────────────────────
    def _fallback_post_suggestions(self, platform: str) -> List[Dict[str, Any]]:
        """Return canned suggestions when Gemini API is unavailable."""
        platform_suggestions = {
            "twitter": [
                {"content": "Just had an amazing coffee at our favorite local spot ☕ What's everyone drinking to power through their Tuesday? Drop your go-to cup in the comments! 👇", "confidence": 0.85},
                {"content": "Tuesday motivation: Every expert was once a beginner! 💪 Keep pushing, stay focused, and remember that growth takes time. What goals are you working on today?", "confidence": 0.78},
                {
                    "content": "Quick tip: Take a 5-minute break every hour. Your productivity will thank you, and it's a great way to clear your head! ⏰ Try it out and let us know if it helps.",
                    "confidence": 0.82,
                },
                {"content": "Reflecting on the best advice I've received this week: 'Focus on progress, not perfection.' 📈 What is the best piece of wisdom you heard recently? Let's chat below! 👇", "confidence": 0.75},
            ],
            "instagram": [
                {"content": "Behind the scenes of our latest project! 📸 We have been working hard to bring this to life, and we cannot wait to share the final result with you all. Stay tuned for updates! ✨ #BTS #Creative #BehindTheScenes #WorkInProgress", "confidence": 0.88},
                {"content": "Golden hour vibes from today's photoshoot 🌅 There is something truly magical about catching the perfect light! Which shot is your favorite? Let us know in the comments! #Photography #GoldenHour #Inspiration #Vibes", "confidence": 0.84},
                {"content": "Team collaboration at its finest! When great minds work together, amazing ideas turn into reality. So grateful for this hardworking and passionate crew. 💼✨ #Teamwork #Collaboration #CompanyCulture #OfficeVibes", "confidence": 0.79},
                {"content": "Friday feeling! Ready for an amazing weekend ahead to recharge, relax, and spend quality time with loved ones. What are your plans for the weekend? 🎉 #FridayVibes #WeekendReady #Recharge #Weekend", "confidence": 0.81},
            ],
            "linkedin": [
                {
                    "content": "Thrilled to share key insights from our latest industry report. Digital transformation is accelerating faster than ever, and automation is leading the way in operational efficiency. How is your team adapting to these changes? Let's discuss in the comments below. #DigitalTransformation #BusinessStrategy #Innovation #TechTrends",
                    "confidence": 0.87,
                },
                {
                    "content": "Reflecting on this week's achievements and lessons learned. Growth always happens outside of your comfort zone, even when it feels challenging. Keep pushing forward! What was your biggest professional win this week? #ProfessionalGrowth #Leadership #CareerDevelopment #Mentorship",
                    "confidence": 0.83,
                },
                {
                    "content": "Looking for talented professionals to join our growing team! We're hiring for several key roles across engineering, product, and design. If you're passionate about innovation and want to make an impact, check out our careers page or DM me directly. 🚀 #Hiring #CareerOpportunities #JobOpening #TechJobs",
                    "confidence": 0.85,
                },
                {
                    "content": "Just completed an inspiring workshop on digital leadership. Knowledge sharing is one of the most powerful tools we have for growth. Here's to learning, adapting, and growing together! #ContinuousLearning #LeadershipDevelopment #B2B #Networking",
                    "confidence": 0.80,
                },
            ],
            "facebook": [
                {
                    "content": "Celebrating an incredible community milestone today! Thank you to everyone who has been part of this journey — your support means the absolute world to us. Here's to many more milestones together! 🎉❤️ #Community #Milestone #ThankYou #Grateful",
                    "confidence": 0.86,
                },
                {"content": "Weekend plans sorted! Time to completely unplug, recharge, and spend quality time with family. How are you spending your weekend? Let us know below! ❤️ #WeekendVibes #FamilyTime #Unplug #Recharge", "confidence": 0.78},
                {"content": "Sharing some exciting insights and key takeaways from today's industry event. The future of our industry looks incredibly bright, and we are thrilled to be at the forefront of this evolution! #Networking #IndustryInsights #FutureOfTech #Evolution", "confidence": 0.82},
                {
                    "content": "Incredibly grateful for the amazing feedback on our latest product launch! You all are absolute rockstars and we couldn't do this without you. Keep the feedback coming! 🙏✨ #ProductLaunch #CustomerFeedback #Grateful #Innovation",
                    "confidence": 0.84,
                },
            ],
        }

        suggestions = platform_suggestions.get(platform.lower(), platform_suggestions["twitter"])
        return random.sample(suggestions, min(3, len(suggestions)))

    def generate_hashtags(self, content: str, platform: str) -> List[str]:
        """Generate relevant hashtags for content"""
        if os.getenv("GEMINI_API_KEY"):
            prompt = f"""
            Generate exactly 6 relevant, high-performing hashtags for the following content on {platform}.
            Ensure they are formatted with '#' and are related to the content topic.
            
            Content: "{content}"
            
            Provide the response in raw JSON format as a list of strings.
            
            Do not include any markdown formatting like ```json in the output. Return only raw valid JSON list.
            """
            res_text = self._call_gemini(prompt, json_mode=True)
            if res_text:
                try:
                    res_text = res_text.strip()
                    if res_text.startswith("```json"):
                        res_text = res_text.split("```json")[1].split("```")[0].strip()
                    elif res_text.startswith("```"):
                        res_text = res_text.split("```")[1].split("```")[0].strip()
                    data = json.loads(res_text)
                    if isinstance(data, list):
                        return [tag if tag.startswith('#') else f"#{tag}" for tag in data[:6]]
                except Exception as e:
                    logging.error(f"Failed to parse Gemini hashtags: {str(e)}")

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

        # Try Gemini API first if key is available
        if os.getenv("GEMINI_API_KEY"):
            prompt = f"""
            Analyze the sentiment of the following social media text:
            "{cleaned_text}"
            
            Provide the response in raw JSON format with the following keys:
            - "sentiment": either "positive", "neutral", or "negative".
            - "confidence": a float between 0.0 and 1.0 representing your confidence.
            - "scores": an object with keys "positive", "neutral", "negative" whose values sum to 1.0.
            
            Do not include any markdown formatting like ```json in the output. Return only raw valid JSON.
            """
            res_text = self._call_gemini(prompt, json_mode=True)
            if res_text:
                try:
                    res_text = res_text.strip()
                    if res_text.startswith("```json"):
                        res_text = res_text.split("```json")[1].split("```")[0].strip()
                    elif res_text.startswith("```"):
                        res_text = res_text.split("```")[1].split("```")[0].strip()
                    data = json.loads(res_text)
                    return {
                        "sentiment": data.get("sentiment", "neutral"),
                        "confidence": round(data.get("confidence", 0.8), 2),
                        "scores": {k: round(v, 2) for k, v in data.get("scores", {"positive": 0.33, "neutral": 0.34, "negative": 0.33}).items()},
                        "method": "gemini_api"
                    }
                except Exception as e:
                    logging.error(f"Failed to parse Gemini sentiment response: {str(e)}")

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

        # Try Gemini API if key is available
        if os.getenv("GEMINI_API_KEY"):
            prompt = f"""
            You are a social media optimization expert.
            Analyze and optimize the following content for {platform}.
            Ensure it fits platform character limits (max {platform_info["max_length"]} characters) and best practices.
            
            Original Content: "{content}"
            
            Provide the response in raw JSON format with the following keys:
            - "optimized_content": A highly optimized version of the post for {platform}.
            - "variations": A list of 3 creative alternative variations of the post (e.g. professional tone, casual/funny tone, question/engaging tone).
            - "tips": A list of 2-3 specific optimization tips for this post on {platform}.
            
            Do not include any markdown formatting like ```json in the output. Return only raw valid JSON.
            """
            res_text = self._call_gemini(prompt, json_mode=True)
            if res_text:
                try:
                    res_text = res_text.strip()
                    if res_text.startswith("```json"):
                        res_text = res_text.split("```json")[1].split("```")[0].strip()
                    elif res_text.startswith("```"):
                        res_text = res_text.split("```")[1].split("```")[0].strip()
                    data = json.loads(res_text)
                    opt_content = data.get("optimized_content", content)
                    return {
                        "platform": platform,
                        "is_optimized": len(opt_content) <= platform_info["max_length"],
                        "current_length": len(content),
                        "max_length": platform_info["max_length"],
                        "suggestion": opt_content,
                        "optimized_content": opt_content,
                        "variations": data.get("variations", []),
                        "tips": data.get("tips", platform_info["tips"]),
                        "method": "gemini_api"
                    }
                except Exception as e:
                    logging.error(f"Failed to parse Gemini optimize content response: {str(e)}")

        is_optimized = content_length <= platform_info["max_length"]

        result = {
            "platform": platform,
            "is_optimized": is_optimized,
            "current_length": content_length,
            "max_length": platform_info["max_length"],
            "suggestion": platform_info["suggestion"],
            "optimized_content": content,
            "variations": [],
            "tips": platform_info["tips"],
            "method": "rules"
        }

        if not is_optimized:
            result["truncated_content"] = content[: platform_info["max_length"] - 3] + "..."

        return result

    def generate_content_ideas(self, topic: str, platform: str, count: int = 5) -> List[Dict[str, Any]]:
        """Generate content ideas around a specific topic"""
        if os.getenv("GEMINI_API_KEY"):
            prompt = f"""
            You are a social media campaign strategist.
            Generate exactly {count} creative content ideas / topics to post about based on the main topic "{topic}" for {platform}.
            Ensure they are tailored to {platform} and are highly engaging.
            
            Provide the response in raw JSON format as a list of objects, where each object has:
            - "content": The post content draft / description of the idea.
            - "type": The category of the idea (e.g. "tips", "behind_scenes", "case_study", "trends", "myths").
            - "confidence": A float between 0.7 and 0.99.
            - "estimated_engagement": either "High", "Medium", or "Low".
            
            Do not include any markdown formatting like ```json in the output. Return only raw valid JSON list.
            """
            res_text = self._call_gemini(prompt, json_mode=True)
            if res_text:
                try:
                    res_text = res_text.strip()
                    if res_text.startswith("```json"):
                        res_text = res_text.split("```json")[1].split("```")[0].strip()
                    elif res_text.startswith("```"):
                        res_text = res_text.split("```")[1].split("```")[0].strip()
                    data = json.loads(res_text)
                    if isinstance(data, list):
                        return data[:count]
                except Exception as e:
                    logging.error(f"Failed to parse Gemini content ideas: {str(e)}")

        idea_templates = [
            {
                "type": "tips",
                "content": (
                    f"✅ 5 essential tips for {topic} that everyone should know:\n\n"
                    f"1️⃣ Start with a clear goal — know what success looks like before you begin\n"
                    f"2️⃣ Invest time in research — understanding your audience changes everything\n"
                    f"3️⃣ Be consistent — small, regular actions outperform big, sporadic ones\n"
                    f"4️⃣ Measure what matters — track the metrics that align with your goals\n"
                    f"5️⃣ Never stop learning — {topic} evolves fast, and so should you\n\n"
                    f"Which of these resonates most with you? 💬 Drop your answer below!\n\n"
                    f"#{topic.replace(' ', '')} #Tips #GrowthHacks #Strategy"
                ),
                "estimated_engagement": "High",
            },
            {
                "type": "behind_scenes",
                "content": (
                    f"👀 Behind the scenes: How we approach {topic}\n\n"
                    f"People often ask us what our process looks like — so today, we're pulling back the curtain entirely.\n\n"
                    f"It starts with research 🔍, moves into strategy 🗺️, then execution ⚙️, and finally analysis 📊. "
                    f"Every step in the {topic} workflow is intentional, tested, and constantly refined based on real data.\n\n"
                    f"The biggest lesson we've learned? There's no shortcut — but there IS a smarter path. And we'd love to show you.\n\n"
                    f"💬 Comment 'GUIDE' below and we'll share our full framework with you!\n\n"
                    f"#BehindTheScenes #{topic.replace(' ', '')} #Process #HowWeWork"
                ),
                "estimated_engagement": "High",
            },
            {
                "type": "trends",
                "content": (
                    f"🔥 Latest {topic} trends you absolutely cannot ignore in 2025:\n\n"
                    f"The landscape is shifting fast — and the brands that adapt now will be miles ahead of the competition by year end.\n\n"
                    f"Here's what's reshaping {topic} right now:\n"
                    f"📌 AI-powered automation is changing the speed of execution\n"
                    f"📌 Personalisation at scale is no longer optional — it's expected\n"
                    f"📌 Short-form content continues to dominate attention and reach\n"
                    f"📌 Community-led growth is overtaking traditional ad-driven funnels\n\n"
                    f"Which trend do you think will have the biggest impact? 🤔 Vote in the comments!\n\n"
                    f"#{topic.replace(' ', '')} #Trends2025 #FutureOfMarketing #StayAhead"
                ),
                "estimated_engagement": "High",
            },
            {
                "type": "mistakes",
                "content": (
                    f"⚠️ Common {topic} mistakes that are quietly killing your results — and how to fix them:\n\n"
                    f"❌ Mistake 1: Skipping the strategy phase and jumping straight to execution\n"
                    f"✅ Fix: Spend 20% of your time planning — it saves 80% later\n\n"
                    f"❌ Mistake 2: Chasing vanity metrics instead of meaningful KPIs\n"
                    f"✅ Fix: Define 2–3 core metrics that directly tie to business outcomes\n\n"
                    f"❌ Mistake 3: Treating every platform the same\n"
                    f"✅ Fix: Tailor your content format and tone to each platform's audience\n\n"
                    f"❌ Mistake 4: Ignoring audience feedback and engagement signals\n"
                    f"✅ Fix: Review comments and DMs weekly — your audience is telling you what they want\n\n"
                    f"Save this post — you'll want to revisit it! 💾\n\n"
                    f"#{topic.replace(' ', '')} #Mistakes #ContentStrategy #Lessons"
                ),
                "estimated_engagement": "Medium",
            },
            {
                "type": "tools",
                "content": (
                    f"🛠️ The best tools and resources for {topic} in 2025 (our honest recommendations):\n\n"
                    f"After years of testing dozens of platforms and workflows, these are the ones we keep coming back to:\n\n"
                    f"📌 For planning & scheduling — save time with smart automation\n"
                    f"📌 For analytics & reporting — track what actually matters\n"
                    f"📌 For content creation — produce high-quality assets at speed\n"
                    f"📌 For audience research — understand your community deeply\n"
                    f"📌 For collaboration — keep your team aligned and efficient\n\n"
                    f"💬 What tools are YOU using for {topic}? Drop your favourites below — we might feature them next! 👇\n\n"
                    f"#{topic.replace(' ', '')} #Tools #Productivity #ResourceGuide"
                ),
                "estimated_engagement": "Medium",
            },
            {
                "type": "guide",
                "content": (
                    f"📖 Complete beginner's guide to {topic} — everything you need to get started today:\n\n"
                    f"If you're new to {topic}, this is for you. We've broken it down into the simplest possible steps so you can go from zero to confident fast.\n\n"
                    f"Step 1️⃣: Understand the fundamentals — build a solid foundation before diving in\n"
                    f"Step 2️⃣: Set clear, measurable goals — vague intentions lead to vague results\n"
                    f"Step 3️⃣: Choose the right tools — don't overcomplicate it at the start\n"
                    f"Step 4️⃣: Take consistent action — progress beats perfection every time\n"
                    f"Step 5️⃣: Review and refine — the best practitioners are always iterating\n\n"
                    f"📌 Save this guide and share it with someone who needs it!\n\n"
                    f"#{topic.replace(' ', '')} #BeginnerGuide #LearnSomethingNew #GetStarted"
                ),
                "estimated_engagement": "High",
            },
            {
                "type": "case_study",
                "content": (
                    f"📈 A real {topic} success story — and the key takeaways you can apply today:\n\n"
                    f"We started with a challenge that felt impossible: limited resources, a tight timeline, and a highly competitive space. But by applying a focused, data-driven {topic} strategy, the results exceeded every expectation.\n\n"
                    f"🔑 Here's what made the difference:\n"
                    f"✅ We focused on ONE primary goal instead of spreading thin\n"
                    f"✅ We let data guide every creative decision\n"
                    f"✅ We tested, learned, and iterated rapidly\n"
                    f"✅ We engaged authentically with our audience at every step\n\n"
                    f"The result? Measurable growth, a stronger community, and a repeatable playbook.\n\n"
                    f"💬 What would YOU do differently with a proven {topic} playbook? Tell us below!\n\n"
                    f"#{topic.replace(' ', '')} #CaseStudy #SuccessStory #Results #Strategy"
                ),
                "estimated_engagement": "High",
            },
            {
                "type": "myths",
                "content": (
                    f"🚫 Let's debunk the most popular {topic} myths — because bad advice is everywhere:\n\n"
                    f"Myth 1: 'You need a huge budget to see results'\n"
                    f"Truth: Strategy and consistency beat budget almost every time 💡\n\n"
                    f"Myth 2: 'More content always means more growth'\n"
                    f"Truth: Quality and relevance outperform volume — always 🎯\n\n"
                    f"Myth 3: 'You need to be on every platform'\n"
                    f"Truth: Dominate 1–2 platforms first before spreading your efforts 🏆\n\n"
                    f"Myth 4: 'Results happen overnight'\n"
                    f"Truth: Sustainable growth takes time, testing, and patience ⏳\n\n"
                    f"Which of these myths have you believed? Be honest! 👇\n\n"
                    f"#{topic.replace(' ', '')} #MythVsFact #MarketingTruths #DebunkingMyths"
                ),
                "estimated_engagement": "Medium",
            },
            {
                "type": "future",
                "content": (
                    f"🔮 The future of {topic} — what to expect in the next 12–24 months:\n\n"
                    f"The pace of change in {topic} is accelerating. What worked last year might already be outdated — and the brands preparing NOW will have a massive advantage.\n\n"
                    f"Here's what we see coming:\n"
                    f"🤖 AI will handle more of the execution — humans will focus on strategy & creativity\n"
                    f"📊 Data literacy will become a non-negotiable skill for every marketer\n"
                    f"🌍 Hyper-localisation will replace one-size-fits-all campaigns\n"
                    f"🎥 Video (especially short-form) will continue to dominate all platforms\n"
                    f"🤝 Community and trust will be the most valuable currency\n\n"
                    f"Are you prepared for what's coming? 💬 Tell us your biggest prediction below!\n\n"
                    f"#{topic.replace(' ', '')} #FutureTrends #Innovation #Predictions2025"
                ),
                "estimated_engagement": "High",
            },
            {
                "type": "comparison",
                "content": (
                    f"⚖️ Comparing the top approaches to {topic} — which one is right for you?\n\n"
                    f"There's no single 'best' way to tackle {topic}. The right approach depends entirely on your goals, audience, and resources. Here's a clear breakdown:\n\n"
                    f"🔹 Approach A (DIY / Organic): Lower cost, higher time investment, great for building authentic connections. Best for startups and personal brands.\n\n"
                    f"🔹 Approach B (Paid / Boosted): Faster results, requires budget, excellent for scaling proven content. Best for established businesses ready to grow.\n\n"
                    f"🔹 Approach C (Hybrid): Combines organic consistency with strategic paid amplification. Best for brands balancing growth and sustainability.\n\n"
                    f"💬 Which approach are you currently using for {topic}? And which are you considering? Let's discuss!\n\n"
                    f"#{topic.replace(' ', '')} #Strategy #Comparison #MarketingApproach #GrowthPlan"
                ),
                "estimated_engagement": "Medium",
            },
        ]

        ideas = []
        for i in range(min(count, len(idea_templates))):
            item = idea_templates[i].copy()
            item["confidence"] = round(random.uniform(0.7, 0.9), 2)
            ideas.append(item)

        return ideas


# Export the class as default
__all__ = ["AIService"]
