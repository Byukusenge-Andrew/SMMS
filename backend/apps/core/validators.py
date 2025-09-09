"""
Custom password validators for the SMMS application.
"""

from django.contrib.auth.password_validation import CommonPasswordValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class SafeCommonPasswordValidator:
    """
    A safe version of CommonPasswordValidator that handles encoding issues.
    Validates against a predefined list of common passwords.
    """
    
    # Common passwords list (subset of most common passwords)
    COMMON_PASSWORDS = {
        'password', '123456', '123456789', 'qwerty', 'abc123', 
        'password123', 'admin', 'letmein', 'welcome', 'monkey',
        'dragon', 'password1', '123123', 'football', 'iloveyou',
        'admin123', 'welcome123', 'login', 'master', 'hello',
        'guest', 'root', 'user', 'test', 'demo', 'sample',
        'default', 'changeme', 'temp', 'temporary'
    }
    
    def __init__(self, password_list_path=None):
        # We ignore the password_list_path to avoid encoding issues
        pass
    
    def validate(self, password, user=None):
        """
        Validate that the password is not a common password.
        """
        if password and password.lower() in self.COMMON_PASSWORDS:
            raise ValidationError(
                _("This password is too common."),
                code='password_too_common',
            )
    
    def get_help_text(self):
        return _("Your password can't be a commonly used password.")
