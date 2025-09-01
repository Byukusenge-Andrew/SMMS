"""
Authentication-related Celery tasks
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from celery import shared_task

from .models import Team, TeamMember, UserProfile

logger = logging.getLogger(__name__)


@shared_task
def send_team_invitation_email(team_id, invited_email, inviter_name):
    """Send team invitation email"""
    try:
        team = Team.objects.get(id=team_id)

        subject = f"You've been invited to join {team.name}"

        # Create invitation URL (you can customize this based on your frontend)
        invitation_url = f"{settings.FRONTEND_URL}/teams/invitation/{team_id}?email={invited_email}"

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

If you don't have an account yet, you'll be able to create one during the process. You'll also need to verify your email address to activate your account before joining the team.

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


@shared_task
def check_expired_trials():
    """Check for expired trials and downgrade users to free tier"""
    try:
        from django.utils import timezone
        from apps.core.models.payment_models import SubscriptionTier
        
        # Get profiles with active trials that have expired
        expired_profiles = UserProfile.objects.filter(
            is_trial_active=True,
            trial_end_date__lt=timezone.now(),
            trial_expired_notified=False
        )
        
        free_tier = SubscriptionTier.objects.filter(name="free", is_active=True).first()
        if not free_tier:
            logger.error("Free tier not found - cannot downgrade expired trials")
            return False
        
        downgraded_count = 0
        
        for profile in expired_profiles:
            # Check if user has paid subscription
            if not profile.has_paid_subscription():
                # Send notification email before downgrading
                send_trial_expired_notification.delay(profile.user.id)
                
                # Downgrade to free tier
                profile.end_trial_and_downgrade()
                downgraded_count += 1
                
                logger.info(f"Downgraded user {profile.user.username} from trial to free tier")
        
        logger.info(f"Processed {downgraded_count} expired trials")
        return True
        
    except Exception as e:
        logger.error(f"Error checking expired trials: {str(e)}")
        return False


@shared_task 
def send_trial_expired_notification(user_id):
    """Send notification email when trial expires"""
    try:
        from django.contrib.auth.models import User
        
        user = User.objects.get(id=user_id)
        profile = user.profile
        
        subject = "Your free trial has ended - Time to upgrade!"
        
        context = {
            "user_name": user.first_name or user.username,
            "upgrade_url": f"{settings.FRONTEND_URL}/billing/upgrade",
            "subscription_tier": profile.subscription_tier.display_name if profile.subscription_tier else "Premium"
        }
        
        # Try to render HTML template
        try:
            html_message = render_to_string("emails/trial_expired.html", context)
        except:
            html_message = None
        
        plain_message = f"""
Hi {context['user_name']},

Your 14-day free trial of {context['subscription_tier']} has ended. 

Your account has been moved to our free plan, but you can upgrade anytime to regain access to all premium features.

Upgrade now: {context['upgrade_url']}

Thanks for trying our premium features!

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
        
        logger.info(f"Trial expired notification sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending trial expired notification: {str(e)}")
        return False


@shared_task
def send_trial_reminder_notification(user_id, days_left):
    """Send reminder when trial is about to expire"""
    try:
        from django.contrib.auth.models import User
        
        user = User.objects.get(id=user_id)
        profile = user.profile
        
        subject = f"Your free trial ends in {days_left} days"
        
        context = {
            "user_name": user.first_name or user.username,
            "days_left": days_left,
            "upgrade_url": f"{settings.FRONTEND_URL}/billing/upgrade",
            "subscription_tier": profile.subscription_tier.display_name if profile.subscription_tier else "Premium"
        }
        
        # Try to render HTML template
        try:
            html_message = render_to_string("emails/trial_reminder.html", context)
        except:
            html_message = None
        
        plain_message = f"""
Hi {context['user_name']},

Your {context['subscription_tier']} free trial ends in {days_left} days.

Don't lose access to your premium features! Upgrade now to continue enjoying:
- Unlimited social accounts
- Advanced analytics
- Team collaboration
- And much more!

Upgrade now: {context['upgrade_url']}

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
        
        logger.info(f"Trial reminder sent to {user.email} ({days_left} days left)")
        return True
        
    except Exception as e:
        logger.error(f"Error sending trial reminder: {str(e)}")
        return False


@shared_task
def send_trial_reminders():
    """Send reminders for trials ending soon"""
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        # Check for trials ending in 3 days
        reminder_date = timezone.now() + timedelta(days=3)
        
        profiles_to_remind = UserProfile.objects.filter(
            is_trial_active=True,
            trial_end_date__date=reminder_date.date()
        )
        
        reminded_count = 0
        
        for profile in profiles_to_remind:
            if not profile.has_paid_subscription():
                days_left = profile.days_left_in_trial()
                send_trial_reminder_notification.delay(profile.user.id, days_left)
                reminded_count += 1
        
        logger.info(f"Sent trial reminders to {reminded_count} users")
        return True
        
    except Exception as e:
        logger.error(f"Error sending trial reminders: {str(e)}")
        return False
