# Stub file for the Slack service integration

class SlackService:
    """Simplified Slack service for development"""
    
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url
    
    def send_message(self, channel, message, blocks=None):
        """Simulate sending a message to Slack"""
        return {
            'success': True,
            'channel': channel,
            'ts': '1625097600.123456'  # Slack timestamp format
        }
    
    def send_notification(self, user, title, message, data=None):
        """Send a notification to a user via Slack"""
        return {
            'success': True,
            'user': getattr(user, 'username', 'unknown'),
            'title': title
        }

# Export the class as default
__all__ = ['SlackService']
