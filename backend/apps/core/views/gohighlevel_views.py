"""
API views for GoHighLevel CRM integration
"""
import logging
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse
from django.db import models
from django.db.models import Q

from ..models.crm_models import GoHighLevelIntegration, CRMContact
from ..models.payment_models import UserSubscription
from ..services import GoHighLevelService
from ..serializers.crm_serializers import (
    GoHighLevelIntegrationSerializer,
    CRMContactSerializer,
    CRMContactCreateUpdateSerializer,
)

logger = logging.getLogger(__name__)


@extend_schema(
    operation_id="setup_gohighlevel_integration",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'api_key': {'type': 'string', 'description': 'GoHighLevel API key'},
                'location_id': {'type': 'string', 'description': 'GoHighLevel location ID'},
                'sync_contacts': {'type': 'boolean', 'description': 'Enable contact synchronization'},
                'sync_opportunities': {'type': 'boolean', 'description': 'Enable opportunity synchronization'},
                'sync_campaigns': {'type': 'boolean', 'description': 'Enable campaign synchronization'},
            },
            'required': ['api_key', 'location_id']
        }
    },
    responses={
        200: OpenApiResponse(description="Integration setup successfully"),
        400: OpenApiResponse(description="Invalid request data"),
        403: OpenApiResponse(description="Feature not available in current plan"),
    },
    summary="Setup GoHighLevel integration",
    description="Setup or update GoHighLevel CRM integration settings"
)
@api_view(['POST', 'PUT'])
@permission_classes([permissions.IsAuthenticated])
def setup_gohighlevel_integration(request):
    """Setup GoHighLevel integration for the user"""
    try:
        # Check if user has access to GoHighLevel integration
        try:
            subscription = UserSubscription.objects.get(user=request.user)
            if not subscription.tier.gohighlevel_integration:
                return Response({
                    'success': False,
                    'error': 'GoHighLevel integration is not available in your current plan'
                }, status=status.HTTP_403_FORBIDDEN)
        except UserSubscription.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Please upgrade your plan to access GoHighLevel integration'
            }, status=status.HTTP_403_FORBIDDEN)
        
        data = request.data
        api_key = data.get('api_key')
        location_id = data.get('location_id')
        
        if not api_key or not location_id:
            return Response({
                'success': False,
                'error': 'api_key and location_id are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Test connection before saving
        ghl_service = GoHighLevelService(api_key=api_key, location_id=location_id)
        connection_test = ghl_service.test_connection()
        
        if not connection_test['success']:
            return Response({
                'success': False,
                'error': f'Failed to connect to GoHighLevel: {connection_test["error"]}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create or update integration
        integration, created = GoHighLevelIntegration.objects.update_or_create(
            user=request.user,
            defaults={
                'api_key': api_key,
                'location_id': location_id,
                'sync_contacts': data.get('sync_contacts', True),
                'sync_opportunities': data.get('sync_opportunities', True),
                'sync_campaigns': data.get('sync_campaigns', True),
                'is_active': True,
            }
        )
        
        return Response({
            'success': True,
            'message': 'GoHighLevel integration setup successfully',
            'integration_id': str(integration.id),
            'location_name': connection_test.get('location_name'),
        })
        
    except Exception as e:
        logger.error(f"Error setting up GoHighLevel integration: {e}")
        return Response({
            'success': False,
            'error': 'Failed to setup integration'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="test_gohighlevel_connection",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'api_key': {'type': 'string', 'description': 'GoHighLevel API key'},
                'location_id': {'type': 'string', 'description': 'GoHighLevel location ID'},
            },
            'required': ['api_key', 'location_id']
        }
    },
    responses={
        200: OpenApiResponse(description="Connection test result"),
        400: OpenApiResponse(description="Invalid request data"),
    },
    summary="Test GoHighLevel connection",
    description="Test GoHighLevel CRM integration settings without saving"
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def test_gohighlevel_connection(request):
    """Test GoHighLevel integration connection"""
    try:
        data = request.data
        api_key = data.get('api_key')
        location_id = data.get('location_id')
        
        if not api_key or not location_id:
            return Response({
                'success': False,
                'error': 'api_key and location_id are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        ghl_service = GoHighLevelService(api_key=api_key, location_id=location_id)
        connection_test = ghl_service.test_connection()
        
        return Response(connection_test)
        
    except Exception as e:
        logger.error(f"Error testing GoHighLevel connection: {e}")
        return Response({
            'success': False,
            'error': 'Failed to test connection'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="get_gohighlevel_integration",
    responses={
        200: OpenApiResponse(description="Integration details"),
        404: OpenApiResponse(description="No integration found"),
    },
    summary="Get GoHighLevel integration",
    description="Get current GoHighLevel integration settings"
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_gohighlevel_integration(request):
    """Get user's GoHighLevel integration details"""
    try:
        try:
            integration = GoHighLevelIntegration.objects.get(user=request.user, is_active=True)
        except GoHighLevelIntegration.DoesNotExist:
            return Response({
                'success': False,
                'error': 'No GoHighLevel integration found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Test current connection
        ghl_service = GoHighLevelService(user=request.user)
        connection_test = ghl_service.test_connection()
        
        return Response({
            'success': True,
            'integration': {
                'id': str(integration.id),
                'location_id': integration.location_id,
                'sync_contacts': integration.sync_contacts,
                'sync_opportunities': integration.sync_opportunities,
                'sync_campaigns': integration.sync_campaigns,
                'is_active': integration.is_active,
                'last_sync_date': integration.last_sync_date,
                'created_at': integration.created_at,
                'connection_status': connection_test,
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching GoHighLevel integration: {e}")
        return Response({
            'success': False,
            'error': 'Failed to fetch integration details'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="delete_gohighlevel_integration",
    responses={
        200: OpenApiResponse(description="Integration deleted successfully"),
        404: OpenApiResponse(description="No integration found"),
    },
    summary="Delete GoHighLevel integration",
    description="Delete GoHighLevel integration and all synced data"
)
@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_gohighlevel_integration(request):
    """Delete GoHighLevel integration"""
    try:
        try:
            integration = GoHighLevelIntegration.objects.get(user=request.user)
            integration.delete()
            
            # Also delete all synced contacts
            CRMContact.objects.filter(user=request.user).delete()
            
            return Response({
                'success': True,
                'message': 'GoHighLevel integration deleted successfully'
            })
            
        except GoHighLevelIntegration.DoesNotExist:
            return Response({
                'success': False,
                'error': 'No GoHighLevel integration found'
            }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        logger.error(f"Error deleting GoHighLevel integration: {e}")
        return Response({
            'success': False,
            'error': 'Failed to delete integration'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="sync_gohighlevel_contacts",
    responses={
        200: OpenApiResponse(description="Contacts synced successfully"),
        404: OpenApiResponse(description="No integration found"),
        400: OpenApiResponse(description="Sync failed"),
    },
    summary="Sync GoHighLevel contacts",
    description="Manually trigger contact synchronization from GoHighLevel"
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def sync_gohighlevel_contacts(request):
    """Manually trigger contact sync from GoHighLevel"""
    try:
        # Check if user has an active integration
        try:
            integration = GoHighLevelIntegration.objects.get(user=request.user, is_active=True)
        except GoHighLevelIntegration.DoesNotExist:
            return Response({
                'success': False,
                'error': 'No active GoHighLevel integration found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if not integration.sync_contacts:
            return Response({
                'success': False,
                'error': 'Contact synchronization is disabled'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Perform sync
        ghl_service = GoHighLevelService(user=request.user)
        sync_result = ghl_service.sync_contacts_to_local()
        
        return Response(sync_result)
        
    except Exception as e:
        logger.error(f"Error syncing GoHighLevel contacts: {e}")
        return Response({
            'success': False,
            'error': 'Failed to sync contacts'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="get_crm_contacts",
    parameters=[
        OpenApiParameter('limit', int, description='Number of contacts to return'),
        OpenApiParameter('offset', int, description='Offset for pagination'),
        OpenApiParameter('status', str, description='Filter by contact status'),
        OpenApiParameter('search', str, description='Search contacts by name or email'),
    ],
    responses={
        200: OpenApiResponse(description="CRM contacts list"),
    },
    summary="Get CRM contacts",
    description="Get list of CRM contacts synced from GoHighLevel"
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_crm_contacts(request):
    """Get user's CRM contacts"""
    try:
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))
        status_filter = request.GET.get('status')
        search = request.GET.get('search')
        
        contacts_query = CRMContact.objects.filter(user=request.user)
        
        if status_filter:
            contacts_query = contacts_query.filter(status=status_filter)
        
        if search:
            contacts_query = contacts_query.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(company__icontains=search)
            )
        
        contacts = contacts_query.order_by('-created_at')[offset:offset + limit]
        
        contact_data = []
        for contact in contacts:
            contact_data.append({
                'id': str(contact.id),
                'ghl_contact_id': contact.ghl_contact_id,
                'first_name': contact.first_name,
                'last_name': contact.last_name,
                'full_name': contact.full_name,
                'email': contact.email,
                'phone': contact.phone,
                'company': contact.company,
                'status': contact.status,
                'tags': contact.tags,
                'social_media_profiles': contact.social_media_profiles,
                'last_contacted': contact.last_contacted,
                'created_at': contact.created_at,
                'last_synced_at': contact.last_synced_at,
            })
        
        total_count = contacts_query.count()
        
        return Response({
            'success': True,
            'contacts': contact_data,
            'results': contact_data,
            'total_count': total_count,
            'count': total_count,
            'has_more': offset + limit < total_count
        })
        
    except Exception as e:
        logger.error(f"Error fetching CRM contacts: {e}")
        return Response({
            'success': False,
            'error': 'Failed to fetch contacts'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="create_gohighlevel_contact",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'first_name': {'type': 'string', 'description': 'Contact first name'},
                'last_name': {'type': 'string', 'description': 'Contact last name'},
                'email': {'type': 'string', 'description': 'Contact email'},
                'phone': {'type': 'string', 'description': 'Contact phone number'},
                'company': {'type': 'string', 'description': 'Contact company'},
                'tags': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Contact tags'},
                'custom_fields': {'type': 'object', 'description': 'Custom field values'},
            },
            'required': ['first_name', 'email']
        }
    },
    responses={
        201: OpenApiResponse(description="Contact created successfully"),
        400: OpenApiResponse(description="Invalid request data"),
        404: OpenApiResponse(description="No integration found"),
    },
    summary="Create GoHighLevel contact",
    description="Create a new contact in GoHighLevel CRM"
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_gohighlevel_contact(request):
    """Create a new contact in GoHighLevel"""
    try:
        # Check if user has an active integration
        try:
            integration = GoHighLevelIntegration.objects.get(user=request.user, is_active=True)
        except GoHighLevelIntegration.DoesNotExist:
            return Response({
                'success': False,
                'error': 'No active GoHighLevel integration found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        data = request.data
        first_name = data.get('first_name')
        email = data.get('email')
        
        if not first_name or not email:
            return Response({
                'success': False,
                'error': 'first_name and email are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create contact in GoHighLevel
        ghl_service = GoHighLevelService(user=request.user)
        
        contact_data = {
            'firstName': first_name,
            'lastName': data.get('last_name', ''),
            'email': email,
            'phone': data.get('phone', ''),
            'companyName': data.get('company', ''),
            'tags': data.get('tags', []),
            'customFields': data.get('custom_fields', {}),
        }
        
        result = ghl_service.create_contact(contact_data)
        
        if result['success']:
            # Sync the created contact to local database
            ghl_contact = result['contact']
            local_contact = ghl_service._sync_single_contact(ghl_contact)
            
            return Response({
                'success': True,
                'message': 'Contact created successfully',
                'contact': {
                    'id': str(local_contact.id),
                    'ghl_contact_id': local_contact.ghl_contact_id,
                    'full_name': local_contact.full_name,
                    'email': local_contact.email,
                }
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Error creating GoHighLevel contact: {e}")
        return Response({
            'success': False,
            'error': 'Failed to create contact'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def gohighlevel_webhook(request):
    """Handle GoHighLevel webhook events"""
    try:
        import json
        payload = json.loads(request.body.decode('utf-8'))
        
        # Extract location ID from payload or headers
        location_id = payload.get('locationId') or request.META.get('HTTP_X_GHL_LOCATION_ID')
        
        if not location_id:
            logger.warning("GoHighLevel webhook missing location ID")
            return HttpResponse(status=400)
        
        # Find the user with this location ID
        try:
            integration = GoHighLevelIntegration.objects.get(
                location_id=location_id, 
                is_active=True
            )
            user = integration.user
        except GoHighLevelIntegration.DoesNotExist:
            logger.warning(f"No integration found for location ID: {location_id}")
            return HttpResponse(status=404)
        
        # Handle webhook using GoHighLevel service
        ghl_service = GoHighLevelService(user=user)
        result = ghl_service.handle_webhook(payload)
        
        if result['success']:
            return HttpResponse(status=200)
        else:
            logger.error(f"GoHighLevel webhook error: {result['error']}")
            return HttpResponse(status=400)
            
    except Exception as e:
        logger.error(f"Error handling GoHighLevel webhook: {e}")
        return HttpResponse(status=400)


@extend_schema(
    operation_id="create_crm_contact",
    request=CRMContactCreateUpdateSerializer,
    responses={
        201: OpenApiResponse(description="Contact created successfully"),
        400: OpenApiResponse(description="Invalid request data"),
    },
    summary="Create CRM contact",
    description="Create a new contact in the CRM system"
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_crm_contact(request):
    """Create a new CRM contact"""
    try:
        serializer = CRMContactCreateUpdateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            # Generate a unique GHL contact ID for manual contacts
            import uuid
            ghl_contact_id = f"manual_{uuid.uuid4().hex[:12]}"
            
            contact = CRMContact.objects.create(
                user=request.user,
                ghl_contact_id=ghl_contact_id,
                **serializer.validated_data
            )
            
            response_serializer = CRMContactSerializer(contact)
            
            return Response({
                'success': True,
                'contact': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error creating CRM contact: {e}")
        return Response({
            'success': False,
            'error': 'Failed to create contact'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="update_crm_contact",
    request=CRMContactCreateUpdateSerializer,
    responses={
        200: OpenApiResponse(description="Contact updated successfully"),
        400: OpenApiResponse(description="Invalid request data"),
        404: OpenApiResponse(description="Contact not found"),
    },
    summary="Update CRM contact",
    description="Update an existing CRM contact"
)
@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_crm_contact(request, contact_id):
    """Update an existing CRM contact"""
    try:
        # Get contact
        try:
            contact = CRMContact.objects.get(id=contact_id, user=request.user)
        except CRMContact.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Contact not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CRMContactCreateUpdateSerializer(
            contact,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            contact = serializer.save()
            response_serializer = CRMContactSerializer(contact)
            
            return Response({
                'success': True,
                'contact': response_serializer.data
            })
        else:
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error updating CRM contact: {e}")
        return Response({
            'success': False,
            'error': 'Failed to update contact'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="delete_crm_contact",
    responses={
        200: OpenApiResponse(description="Contact deleted successfully"),
        404: OpenApiResponse(description="Contact not found"),
    },
    summary="Delete CRM contact",
    description="Delete a CRM contact"
)
@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_crm_contact(request, contact_id):
    """Delete a CRM contact"""
    try:
        # Get contact
        try:
            contact = CRMContact.objects.get(id=contact_id, user=request.user)
        except CRMContact.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Contact not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        contact.delete()
        
        return Response({
            'success': True,
            'message': 'Contact deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting CRM contact: {e}")
        return Response({
            'success': False,
            'error': 'Failed to delete contact'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    operation_id="get_crm_contact",
    responses={
        200: OpenApiResponse(description="Contact details"),
        404: OpenApiResponse(description="Contact not found"),
    },
    summary="Get CRM contact",
    description="Get details of a specific CRM contact"
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_crm_contact(request, contact_id):
    """Get details of a specific CRM contact"""
    try:
        # Get contact
        try:
            contact = CRMContact.objects.get(id=contact_id, user=request.user)
        except CRMContact.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Contact not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CRMContactSerializer(contact)
        
        return Response({
            'success': True,
            'contact': serializer.data
        })
        
    except Exception as e:
        logger.error(f"Error getting CRM contact: {e}")
        return Response({
            'success': False,
            'error': 'Failed to get contact'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
