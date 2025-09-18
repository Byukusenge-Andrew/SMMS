"""
Views for social media sets functionality
"""

from django.db import transaction
from django.db.models import Count, Sum, Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SocialMediaSet, SocialMediaSetMembership, SocialMediaAccount
from .set_serializers import (
    SocialMediaSetSerializer,
    SocialMediaSetMembershipSerializer,
    BulkSetMembershipSerializer,
    SetQuickCreateSerializer,
    SocialMediaSetStatsSerializer
)


class SocialMediaSetViewSet(viewsets.ModelViewSet):
    """ViewSet for managing social media sets"""
    
    serializer_class = SocialMediaSetSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get user's social media sets"""
        return SocialMediaSet.objects.filter(
            user=self.request.user
        ).prefetch_related('social_accounts').order_by('-is_global', 'name')
    
    def perform_create(self, serializer):
        """Create social media set"""
        # If this is the first set for the user, make it global
        existing_sets = SocialMediaSet.objects.filter(user=self.request.user)
        if not existing_sets.exists():
            serializer.save(user=self.request.user, is_global=True)
        else:
            serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_accounts(self, request, pk=None):
        """Add accounts to a set"""
        social_set = self.get_object()
        account_ids = request.data.get('account_ids', [])
        
        if not account_ids:
            return Response(
                {'error': 'account_ids is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate accounts belong to user
        accounts = SocialMediaAccount.objects.filter(
            id__in=account_ids,
            user=request.user
        )
        
        if len(accounts) != len(account_ids):
            return Response(
                {'error': 'Some account IDs are invalid'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add accounts to set
        added_count = 0
        for account in accounts:
            if account.add_to_set(social_set, added_by=request.user):
                added_count += 1
        
        return Response({
            'message': f'Added {added_count} accounts to set',
            'set': SocialMediaSetSerializer(social_set, context={'request': request}).data
        })
    
    @action(detail=True, methods=['post'])
    def remove_accounts(self, request, pk=None):
        """Remove accounts from a set"""
        social_set = self.get_object()
        account_ids = request.data.get('account_ids', [])
        
        if not account_ids:
            return Response(
                {'error': 'account_ids is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Remove accounts from set
        removed_count = 0
        for account_id in account_ids:
            try:
                account = SocialMediaAccount.objects.get(
                    id=account_id,
                    user=request.user
                )
                if account.remove_from_set(social_set):
                    removed_count += 1
            except SocialMediaAccount.DoesNotExist:
                continue
        
        return Response({
            'message': f'Removed {removed_count} accounts from set',
            'set': SocialMediaSetSerializer(social_set, context={'request': request}).data
        })
    
    @action(detail=True, methods=['post'])
    def set_as_default(self, request, pk=None):
        """Set this set as default for posting"""
        social_set = self.get_object()
        
        # Remove default flag from other sets
        SocialMediaSet.objects.filter(
            user=request.user
        ).update(is_default_for_posting=False)
        
        # Set this set as default
        social_set.is_default_for_posting = True
        social_set.save()
        
        return Response({
            'message': f'Set "{social_set.name}" is now the default for posting',
            'set': SocialMediaSetSerializer(social_set, context={'request': request}).data
        })
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate a set with its accounts"""
        original_set = self.get_object()
        new_name = request.data.get('name', f"{original_set.name} Copy")
        
        # Check if name already exists
        if SocialMediaSet.objects.filter(user=request.user, name=new_name).exists():
            return Response(
                {'error': 'A set with this name already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Create new set
            new_set = SocialMediaSet.objects.create(
                user=request.user,
                name=new_name,
                description=f"Copy of {original_set.name}",
                color=original_set.color,
                icon=original_set.icon,
                auto_assign_new_accounts=original_set.auto_assign_new_accounts,
                auto_assign_platforms=original_set.auto_assign_platforms
            )
            
            # Copy memberships
            for membership in original_set.socialmediasetmembership_set.all():
                SocialMediaSetMembership.objects.create(
                    social_set=new_set,
                    social_account=membership.social_account,
                    added_by=request.user,
                    posting_enabled=membership.posting_enabled,
                    post_order=membership.post_order
                )
        
        return Response(
            SocialMediaSetSerializer(new_set, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get statistics about user's sets"""
        user = request.user
        
        # Get basic stats
        total_sets = SocialMediaSet.objects.filter(user=user).count()
        total_accounts = SocialMediaAccount.objects.filter(user=user, is_active=True).count()
        
        # Get global and default sets
        global_set = SocialMediaSet.objects.filter(user=user, is_global=True).first()
        default_set = SocialMediaSet.objects.filter(user=user, is_default_for_posting=True).first()
        
        # Get accounts without sets
        accounts_with_sets = SocialMediaSetMembership.objects.filter(
            social_set__user=user
        ).values_list('social_account_id', flat=True)
        
        accounts_without_sets = SocialMediaAccount.objects.filter(
            user=user,
            is_active=True
        ).exclude(id__in=accounts_with_sets).count()
        
        # Platform distribution
        platform_distribution = dict(
            SocialMediaAccount.objects.filter(
                user=user,
                is_active=True
            ).values_list('platform').annotate(
                count=Count('id')
            ).order_by('platform')
        )
        
        # Set summary
        set_summary = []
        for social_set in SocialMediaSet.objects.filter(user=user).order_by('-is_global', 'name'):
            set_summary.append({
                'id': str(social_set.id),
                'name': social_set.name,
                'color': social_set.color,
                'icon': social_set.icon,
                'is_global': social_set.is_global,
                'is_default': social_set.is_default_for_posting,
                'account_count': social_set.social_accounts.filter(is_active=True).count(),
                'total_followers': social_set.social_accounts.filter(
                    is_active=True
                ).aggregate(total=Sum('followers_count'))['total'] or 0
            })
        
        stats_data = {
            'total_sets': total_sets,
            'global_set_id': str(global_set.id) if global_set else None,
            'default_set_id': str(default_set.id) if default_set else None,
            'total_accounts': total_accounts,
            'accounts_without_sets': accounts_without_sets,
            'platform_distribution': platform_distribution,
            'set_summary': set_summary
        }
        
        return Response(stats_data)


class SocialMediaSetMembershipViewSet(viewsets.ModelViewSet):
    """ViewSet for managing set memberships"""
    
    serializer_class = SocialMediaSetMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get user's set memberships"""
        return SocialMediaSetMembership.objects.filter(
            social_set__user=self.request.user
        ).select_related('social_set', 'social_account')
    
    def perform_create(self, serializer):
        """Create membership"""
        serializer.save(added_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def set_as_primary(self, request, pk=None):
        """Set this set as primary for the account"""
        membership = self.get_object()
        
        # Remove primary flag from other memberships for this account
        SocialMediaSetMembership.objects.filter(
            social_account=membership.social_account
        ).update(is_primary_set=False)
        
        # Set this membership as primary
        membership.is_primary_set = True
        membership.save()
        
        return Response({
            'message': 'Set as primary set for this account',
            'membership': SocialMediaSetMembershipSerializer(
                membership, context={'request': request}
            ).data
        })


class BulkSetMembershipView(APIView):
    """View for bulk membership operations"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Perform bulk add/remove operations"""
        serializer = BulkSetMembershipSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        account_ids = serializer.validated_data['account_ids']
        set_ids = serializer.validated_data['set_ids']
        action = serializer.validated_data['action']
        posting_enabled = serializer.validated_data['posting_enabled']
        
        accounts = SocialMediaAccount.objects.filter(
            id__in=account_ids,
            user=request.user
        )
        
        sets = SocialMediaSet.objects.filter(
            id__in=set_ids,
            user=request.user
        )
        
        results = []
        
        with transaction.atomic():
            for social_set in sets:
                for account in accounts:
                    if action == 'add':
                        success = account.add_to_set(
                            social_set,
                            added_by=request.user,
                            posting_enabled=posting_enabled
                        )
                        results.append({
                            'set': social_set.name,
                            'account': f"{account.platform}:{account.username}",
                            'action': 'added' if success else 'already_exists'
                        })
                    elif action == 'remove':
                        success = account.remove_from_set(social_set)
                        results.append({
                            'set': social_set.name,
                            'account': f"{account.platform}:{account.username}",
                            'action': 'removed' if success else 'not_found'
                        })
        
        return Response({
            'message': f'Bulk {action} operation completed',
            'results': results
        })


class SetQuickCreateView(APIView):
    """View for quickly creating a set with accounts"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Create set with accounts"""
        serializer = SetQuickCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        social_set = serializer.save()
        
        return Response(
            SocialMediaSetSerializer(social_set, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )


class AccountSetsView(APIView):
    """View for getting sets for a specific account"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, account_id):
        """Get all sets for a specific account"""
        try:
            account = SocialMediaAccount.objects.get(
                id=account_id,
                user=request.user
            )
        except SocialMediaAccount.DoesNotExist:
            return Response(
                {'error': 'Account not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get sets this account belongs to
        memberships = SocialMediaSetMembership.objects.filter(
            social_account=account
        ).select_related('social_set')
        
        # Get all user's sets for comparison
        all_sets = SocialMediaSet.objects.filter(user=request.user)
        
        sets_data = []
        for social_set in all_sets:
            membership = memberships.filter(social_set=social_set).first()
            sets_data.append({
                'id': str(social_set.id),
                'name': social_set.name,
                'color': social_set.color,
                'icon': social_set.icon,
                'is_global': social_set.is_global,
                'is_member': membership is not None,
                'is_primary': membership.is_primary_set if membership else False,
                'posting_enabled': membership.posting_enabled if membership else True,
                'added_at': membership.added_at if membership else None
            })
        
        return Response({
            'account': {
                'id': str(account.id),
                'platform': account.platform,
                'username': account.username,
                'display_name': account.display_name
            },
            'sets': sets_data
        })