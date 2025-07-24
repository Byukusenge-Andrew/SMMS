import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone  # Add this import

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def send_message(message_id):
    """Send a message to social media platform"""
    try:
        from .models import Message

        message = Message.objects.get(id=message_id)

        # Implement actual platform sending logic here
        if message.platform == "instagram":
            success = send_instagram_message(message)
        elif message.platform == "twitter":
            success = send_twitter_message(message)
        elif message.platform == "facebook":
            success = send_facebook_message(message)
        elif message.platform == "linkedin":
            success = send_linkedin_message(message)
        else:
            # Default simulation
            success = True

        if success:
            message.status = "sent"
            message.sent_at = timezone.now()
        else:
            message.status = "failed"

        message.save()

        logger.info(f"Message {message_id} processed with status: {message.status}")
        return success

    except Exception as e:
        logger.error(f"Error sending message {message_id}: {str(e)}")
        try:
            from .models import Message

            message = Message.objects.get(id=message_id)
            message.status = "failed"
            message.save()
        except:
            pass
        return False


def send_instagram_message(message):
    """Send message via Instagram API"""
    try:
        # Implement Instagram Graph API logic
        # This would use the user's connected Instagram account
        logger.info(f"Sending Instagram message to {message.recipient}")
        return True
    except Exception as e:
        logger.error(f"Instagram message failed: {str(e)}")
        return False


def send_twitter_message(message):
    """Send message via Twitter API"""
    try:
        # Implement Twitter API v2 logic
        logger.info(f"Sending Twitter message to {message.recipient}")
        return True
    except Exception as e:
        logger.error(f"Twitter message failed: {str(e)}")
        return False


def send_facebook_message(message):
    """Send message via Facebook Graph API"""
    try:
        # Implement Facebook Graph API logic
        logger.info(f"Sending Facebook message to {message.recipient}")
        return True
    except Exception as e:
        logger.error(f"Facebook message failed: {str(e)}")
        return False


def send_linkedin_message(message):
    """Send message via LinkedIn API"""
    try:
        # Implement LinkedIn API logic
        logger.info(f"Sending LinkedIn message to {message.recipient}")
        return True
    except Exception as e:
        logger.error(f"LinkedIn message failed: {str(e)}")
        return False


@shared_task
def share_calendar_slack(user_id, calendar_data, recipients):
    """Share calendar via Slack"""
    try:
        from django.contrib.auth.models import User

        user = User.objects.get(id=user_id)

        # Format calendar data for Slack
        slack_message = format_calendar_for_slack(calendar_data)

        # Send to Slack channels/users
        for recipient in recipients:
            success = send_slack_message(user, recipient, slack_message)
            if not success:
                logger.warning(f"Failed to send calendar to Slack recipient: {recipient}")

        logger.info(f"Calendar shared via Slack to {len(recipients)} recipients")
        return True

    except Exception as e:
        logger.error(f"Error sharing calendar via Slack: {str(e)}")
        return False


@shared_task
def share_calendar_email(user_id, calendar_data, recipients):
    """Share calendar via email"""
    try:
        from django.contrib.auth.models import User

        user = User.objects.get(id=user_id)

        # Format calendar data for email
        email_subject = f"Social Media Calendar from {user.username}"
        email_body = format_calendar_for_email(calendar_data)

        # Send emails
        send_mail(
            subject=email_subject,
            message=email_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )

        logger.info(f"Calendar shared via email to {len(recipients)} recipients")
        return True

    except Exception as e:
        logger.error(f"Error sharing calendar via email: {str(e)}")
        return False


def format_calendar_for_slack(calendar_data):
    """Format calendar data for Slack message"""
    message = "📅 *Social Media Calendar*\n\n"

    for post in calendar_data:
        message += f"• *{post['platform'].title()}* - {post['scheduled_time']}\n"
        message += f"  {post['title']}\n"
        message += f"  Status: {post['status']}\n\n"

    return message


def format_calendar_for_email(calendar_data):
    """Format calendar data for email"""
    message = "Social Media Calendar\n"
    message += "=" * 50 + "\n\n"

    for post in calendar_data:
        message += f"Platform: {post['platform'].title()}\n"
        message += f"Scheduled: {post['scheduled_time']}\n"
        message += f"Content: {post['title']}\n"
        message += f"Status: {post['status']}\n"
        message += "-" * 30 + "\n\n"

    return message


def send_slack_message(user, recipient, message):
    """Send message to Slack"""
    try:
        # Implement Slack API integration
        # This would use the user's connected Slack workspace
        logger.info(f"Sending Slack message to {recipient}")
        return True
    except Exception as e:
        logger.error(f"Slack message failed: {str(e)}")
        return False


@shared_task
def send_automated_message(automated_message_id, trigger_data=None):
    """Process automated message triggers"""
    try:
        from .models import AutomatedMessage, Message

        automated_msg = AutomatedMessage.objects.get(id=automated_message_id)

        if not automated_msg.active:
            logger.info(f"Automated message {automated_message_id} is inactive")
            return False

        # Process template with dynamic data
        content = process_message_template(automated_msg.content_template, trigger_data or {})

        # Create and send message
        message = Message.objects.create(
            user=automated_msg.user,
            platform=automated_msg.platform,
            recipient=trigger_data.get("recipient", ""),
            content=content,
            message_type="automated",
            priority="normal",
        )

        # Delay if specified
        if automated_msg.delay_minutes > 0:
            send_message.apply_async(args=[message.id], countdown=automated_msg.delay_minutes * 60)
        else:
            send_message.delay(message.id)

        logger.info(f"Automated message {automated_message_id} processed")
        return True

    except Exception as e:
        logger.error(f"Error processing automated message {automated_message_id}: {str(e)}")
        return False


def process_message_template(template, data):
    """Process message template with dynamic data"""
    try:
        # Simple template processing
        # Replace placeholders like {username}, {follower_count}, etc.
        processed = template
        for key, value in data.items():
            placeholder = "{" + key + "}"
            processed = processed.replace(placeholder, str(value))

        return processed
    except Exception as e:
        logger.error(f"Error processing template: {str(e)}")
        return template
