"""
Authentication-related Celery tasks
"""

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .models import Team, TeamMember

logger = logging.getLogger(__name__)


@shared_task
def send_team_invitation_email(team_id, invited_email, inviter_name):
    """Send team invitation email"""
    try:
        team = Team.objects.get(id=team_id)

        subject = f"You've been invited to join {team.name}"

        # Create invitation URL (you can customize this based on your frontend)
        invitation_url = f"{settings.FRONTEND_URL}/teams/invitation/{team_id}"

        context = {
            "team_name": team.name,
            "inviter_name": inviter_name,
            "invitation_url": invitation_url,
            "invited_email": invited_email,
        }

        # Try to render HTML template, fallback to plain text
        try:
            html_message = render_to_string("emails/team_invitation.html", context)
        except:
            html_message = None

        # Plain text message
        plain_message = f"""
Hi there!

{inviter_name} has invited you to join the team "{team.name}" on Social Media Manager.

To accept this invitation, please click the link below:
{invitation_url}

If you don't have an account yet, you'll be able to create one during the process.

Best regards,
The Social Media Manager Team
        """.strip()

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invited_email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Team invitation email sent to {invited_email} for team {team.name}")
        return True

    except Team.DoesNotExist:
        logger.error(f"Team {team_id} not found when sending invitation email")
        return False
    except Exception as e:
        logger.error(f"Error sending team invitation email: {str(e)}")
        return False


@shared_task
def cleanup_expired_invitations():
    """Clean up expired team invitations"""
    from datetime import timedelta

    from django.utils import timezone

    try:
        # Remove invitations older than 7 days that are not active
        cutoff_date = timezone.now() - timedelta(days=7)
        expired_invitations = TeamMember.objects.filter(
            is_active=False, invited_at__lt=cutoff_date, invited_email__isnull=False
        )

        count = expired_invitations.count()
        expired_invitations.delete()

        logger.info(f"Cleaned up {count} expired team invitations")
        return count

    except Exception as e:
        logger.error(f"Error cleaning up expired invitations: {str(e)}")
        return 0


@shared_task
def send_welcome_email(user_id):
    """Send welcome email to new users"""
    try:
        from django.contrib.auth.models import User

        user = User.objects.get(id=user_id)

        subject = "Welcome to Social Media Manager!"

        context = {
            "user_name": user.get_full_name() or user.username,
            "username": user.username,
            "dashboard_url": f"{settings.FRONTEND_URL}/dashboard",
        }

        # Try to render HTML template, fallback to plain text
        try:
            html_message = render_to_string("emails/welcome.html", context)
        except:
            html_message = None

        plain_message = f"""
Welcome to Social Media Manager, {user.get_full_name() or user.username}!

We're excited to have you on board. Here's what you can do to get started:

1. Connect your social media accounts
2. Create your first post
3. Schedule content for optimal engagement
4. Track your performance with our analytics

Visit your dashboard: {settings.FRONTEND_URL}/dashboard

If you have any questions, don't hesitate to reach out to our support team.

Best regards,
The Social Media Manager Team
        """.strip()

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Welcome email sent to {user.email}")
        return True

    except Exception as e:
        logger.error(f"Error sending welcome email: {str(e)}")
        return False
