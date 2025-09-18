"""
Django signals for social media sets functionality
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import SocialMediaAccount, SocialMediaSet


User = get_user_model()


@receiver(post_save, sender=SocialMediaAccount)
def auto_assign_to_sets(sender, instance, created, **kwargs):
    """
    Automatically assign new social media accounts to relevant sets
    """
    if created and instance.is_active:
        try:
            # Get or create global set for the user
            global_set = SocialMediaSet.get_or_create_global_set(instance.user)
            
            # Add to global set if it has auto-assignment enabled
            if global_set and global_set.auto_assign_new_accounts:
                instance.add_to_set(global_set, added_by=instance.user)
            
            # Check for other sets with auto-assignment for this platform
            auto_assign_sets = SocialMediaSet.objects.filter(
                user=instance.user,
                auto_assign_new_accounts=True,
                auto_assign_platforms__contains=[instance.platform]
            ).exclude(id=global_set.id if global_set else None)
            
            for social_set in auto_assign_sets:
                instance.add_to_set(social_set, added_by=instance.user)
        except Exception as e:
            # Gracefully handle any errors in auto-assignment
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to auto-assign social account {instance.id} to sets: {e}")


@receiver(post_save, sender=User)
def create_global_set_for_new_user(sender, instance, created, **kwargs):
    """
    Create a global social media set for new users
    """
    if created:
        try:
            # Create global set for new user
            SocialMediaSet.objects.create(
                user=instance,
                name="All Accounts",
                description="Global set containing all your social media accounts",
                color="#3B82F6",
                icon="globe",
                is_global=True,
                is_active=True,
                is_default_for_posting=True,
                auto_assign_new_accounts=True,
                auto_assign_platforms=["twitter", "linkedin", "facebook", "tiktok", "instagram"]
            )
        except Exception as e:
            # Gracefully handle any errors in global set creation
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to create global set for new user {instance.id}: {e}")