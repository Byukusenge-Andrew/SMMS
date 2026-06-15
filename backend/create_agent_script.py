import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_media_manager.settings')
django.setup()

from django.contrib.auth.models import User
from apps.integrations.models import AIAgent

try:
    user = User.objects.get(username="andrebyukusenge9@gmail.com")
    agent, created = AIAgent.objects.get_or_create(
        user=user,
        name="The B2B Thought Leader & Educator",
        defaults={
            "platform": "linkedin",
            "tone": "professional",
            "persona": (
                "You are a veteran executive ghostwriter and B2B industry analyst. "
                "Your goal is to transform raw notes or articles into structured, value-packed updates. "
                "Start by drafting a professional opening statement. "
                "Next, format the core insights into a bulleted checklist of actionable takeaways. "
                "Conclude with an engaging question to spark discussion in the comments"
            ),
            "temperature": 0.4,
            "is_active": True
        }
    )
    if not created:
        agent.platform = "linkedin"
        agent.tone = "professional"
        agent.persona = (
            "You are a veteran executive ghostwriter and B2B industry analyst. "
            "Your goal is to transform raw notes or articles into structured, value-packed updates. "
            "Start by drafting a professional opening statement. "
            "Next, format the core insights into a bulleted checklist of actionable takeaways. "
            "Conclude with an engaging question to spark discussion in the comments"
        )
        agent.temperature = 0.4
        agent.is_active = True
        agent.save()
    print(f"SUCCESS: Agent '{agent.name}' created/updated for user {user.username}")
except User.DoesNotExist:
    print("ERROR: User 'andrebyukusenge9@gmail.com' not found.")
except Exception as e:
    print(f"ERROR: {str(e)}")
