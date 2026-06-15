from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import patch
import json
from apps.integrations.models import AIAgent
from apps.integrations.serializers import AIAgentSerializer

class AIAgentTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")

    def test_agent_creation(self):
        agent = AIAgent.objects.create(
            user=self.user,
            name="Test Bot",
            persona="Act as a tech blogger.",
            platform="twitter",
            tone="humorous",
            temperature=0.8
        )
        self.assertEqual(agent.name, "Test Bot")
        self.assertEqual(agent.platform, "twitter")
        self.assertEqual(agent.tone, "humorous")
        self.assertEqual(agent.temperature, 0.8)
        self.assertTrue(agent.is_active)
        self.assertEqual(str(agent), "Test Bot (testuser)")

    def test_serializer_validation(self):
        # Valid temperature
        valid_data = {
            "name": "Valid Agent",
            "persona": "Persona rules.",
            "temperature": 0.5
        }
        serializer = AIAgentSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid())

        # Invalid temperature (too high)
        invalid_data_high = {
            "name": "Invalid Agent",
            "persona": "Persona rules.",
            "temperature": 1.5
        }
        serializer_high = AIAgentSerializer(data=invalid_data_high)
        self.assertFalse(serializer_high.is_valid())
        self.assertIn("temperature", serializer_high.errors)

        # Invalid temperature (too low)
        invalid_data_low = {
            "name": "Invalid Agent",
            "persona": "Persona rules.",
            "temperature": -0.2
        }
        serializer_low = AIAgentSerializer(data=invalid_data_low)
        self.assertFalse(serializer_low.is_valid())
        self.assertIn("temperature", serializer_low.errors)

    @patch("apps.integrations.ai_service.AIService._call_gemini")
    @patch("apps.integrations.ai_service.os.getenv")
    def test_deliberative_pipeline_success(self, mock_getenv, mock_call_gemini):
        # Setup mock environment API key
        mock_getenv.side_effect = lambda key, default=None: "fake-api-key" if key == "GEMINI_API_KEY" else None
        
        # Mock responses for Step 1 (Plan), Step 2 (Write), Step 3 (Review)
        plan_response = json.dumps({
            "platform": "twitter",
            "plan": [
                {
                    "topic": "Topic A",
                    "hook": "Hook A",
                    "key_message": "Msg A",
                    "cta": "CTA A",
                    "hashtag_strategy": ["tagA"],
                    "format_notes": "Notes A"
                }
            ]
        })
        
        write_response = json.dumps([
            {
                "content": "Draft A",
                "confidence": 0.8,
                "plan_topic": "Topic A"
            }
        ])
        
        review_response = json.dumps([
            {
                "content": "Polished A",
                "confidence": 0.95,
                "plan_topic": "Topic A"
            }
        ])
        
        mock_call_gemini.side_effect = [plan_response, write_response, review_response]
        
        agent = AIAgent.objects.create(
            user=self.user,
            name="Deliberate Agent",
            persona="Persona info",
            platform="twitter",
            tone="humorous",
            temperature=0.8
        )
        
        from apps.integrations.ai_service import AIService
        service = AIService()
        
        results = service.generate_post_suggestions(self.user, "twitter", agent=agent)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["content"], "Polished A")
        self.assertEqual(results[0]["agent_name"], "Deliberate Agent")
        self.assertEqual(results[0]["generation_method"], "deliberative")
        self.assertIn("plan", results[0])
        self.assertEqual(results[0]["plan"]["topic"], "Topic A")
        self.assertEqual(results[0]["plan"]["hook"], "Hook A")
        self.assertEqual(results[0]["plan"]["cta"], "CTA A")

