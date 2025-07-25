#!/usr/bin/env python3
"""
Test script for AI sentiment analysis functionality
"""

import os
import sys

import django

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "social_media_manager.settings")
django.setup()

from apps.integrations.ai_service import AIService


def test_single_comment_sentiment():
    """Test sentiment analysis on single comments"""
    print("🔍 Testing Single Comment Sentiment Analysis")
    print("=" * 50)

    ai_service = AIService()

    test_comments = [
        "This is absolutely amazing! I love it so much! 😍",
        "This is terrible and I hate it completely 😡",
        "It's okay, nothing special really",
        "Great job on this project! Keep up the excellent work! 👏",
        "Worst thing I've ever seen. Complete waste of time.",
        "Pretty average stuff, could be better or worse",
        "OMG this is fantastic! Best thing ever! 🎉",
        "Meh, it's fine I guess 😐",
    ]

    for i, comment in enumerate(test_comments, 1):
        print(f"\n{i}. Comment: '{comment}'")
        result = ai_service.analyze_sentiment(comment)
        print(f"   Sentiment: {result['sentiment'].upper()} ({result['confidence']:.3f} confidence)")
        print(f"   Method: {result['method']}")
        if "model" in result:
            print(f"   Model: {result['model']}")
        print(f"   Scores: {result['scores']}")


def test_bulk_comments_sentiment():
    """Test sentiment analysis on multiple comments"""
    print("\n\n📊 Testing Bulk Comments Sentiment Analysis")
    print("=" * 50)

    ai_service = AIService()

    bulk_comments = [
        "This is absolutely amazing! I love it!",
        "Great work, keep it up!",
        "Fantastic content, really enjoyed this",
        "This is terrible and boring",
        "Worst post I've ever seen",
        "It's okay, nothing special",
        "Pretty average stuff",
        "Not bad, could be better",
        "Excellent job on this project!",
        "Outstanding work, very impressive!",
    ]

    print(f"Analyzing {len(bulk_comments)} comments...")

    result = ai_service.analyze_comments_sentiment(bulk_comments)

    print(f"\n📈 RESULTS:")
    print(f"Overall Sentiment: {result['overall_sentiment'].upper()}")
    print(f"Comments Analyzed: {result['comments_analyzed']}")
    print(f"Average Confidence: {result['average_confidence']:.3f}")
    print(f"Method Used: {result['method_used']}")

    print(f"\n📊 Sentiment Distribution:")
    for sentiment, percentage in result["sentiment_distribution"].items():
        print(f"  {sentiment.capitalize()}: {percentage}%")

    print(f"\n💡 Insights:")
    for insight in result["insights"]:
        print(f"  • {insight['title']}: {insight['description']}")
        if "recommendation" in insight:
            print(f"    Recommendation: {insight['recommendation']}")


def test_ai_model_availability():
    """Test which AI models are available"""
    print("\n\n🤖 Testing AI Model Availability")
    print("=" * 50)

    try:
        import torch
        from transformers import pipeline

        print("✅ Transformers library is available")
        print(f"✅ PyTorch version: {torch.__version__}")
        print(f"✅ CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"✅ CUDA device count: {torch.cuda.device_count()}")
    except ImportError as e:
        print(f"❌ Transformers not available: {e}")

    try:
        from textblob import TextBlob

        print("✅ TextBlob library is available")
    except ImportError as e:
        print(f"❌ TextBlob not available: {e}")

    # Test AI service initialization
    print("\n🔧 Testing AI Service Initialization...")
    ai_service = AIService()

    if ai_service.sentiment_analyzer:
        print("✅ AI sentiment model loaded successfully")
        print(f"✅ Model: {ai_service.sentiment_model_name}")
    else:
        print("⚠️  AI sentiment model not loaded, using fallback methods")


if __name__ == "__main__":
    print("🚀 Starting AI Sentiment Analysis Tests")
    print("=" * 60)

    try:
        test_ai_model_availability()
        test_single_comment_sentiment()
        test_bulk_comments_sentiment()

        print("\n\n✅ All tests completed successfully!")
        print("🎉 AI sentiment analysis is ready to use!")

    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        import traceback

        traceback.print_exc()
