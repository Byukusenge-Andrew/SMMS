"""
GoHighLevel CRM integration service
"""
import logging
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from django.contrib.auth.models import User
from django.utils import timezone as django_timezone

from ..models.crm_models import GoHighLevelIntegration, CRMContact

logger = logging.getLogger(__name__)


class GoHighLevelService:
    """Service class for GoHighLevel CRM integration"""
    
    BASE_URL = "https://rest.gohighlevel.com/v1"
    
    def __init__(self, user: User = None, api_key: str = None, location_id: str = None):
        self.user = user
        self.api_key = api_key
        self.location_id = location_id
        
        # If user provided, try to get integration settings
        if user and not (api_key and location_id):
            try:
                integration = GoHighLevelIntegration.objects.get(user=user, is_active=True)
                self.api_key = integration.api_key
                self.location_id = integration.location_id
                self.integration = integration
            except GoHighLevelIntegration.DoesNotExist:
                logger.warning(f"No GoHighLevel integration found for user {user.username}")
                self.integration = None
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
            "Content-Type": "application/json",
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the GoHighLevel API connection"""
        try:
            response = requests.get(
                f"{self.BASE_URL}/locations/{self.location_id}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                location_data = response.json()
                return {
                    "success": True,
                    "message": "Connection successful",
                    "location_name": location_data.get("name", "Unknown"),
                    "location_id": self.location_id
                }
            else:
                return {
                    "success": False,
                    "error": f"API returned status {response.status_code}: {response.text}"
                }
                
        except requests.RequestException as e:
            logger.error(f"GoHighLevel connection test failed: {e}")
            return {"success": False, "error": str(e)}
    
    def get_contacts(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Fetch contacts from GoHighLevel"""
        try:
            params = {
                "locationId": self.location_id,
                "limit": limit,
                "skip": offset
            }
            
            response = requests.get(
                f"{self.BASE_URL}/contacts/",
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "contacts": data.get("contacts", []),
                    "total": data.get("count", 0),
                    "meta": data.get("meta", {})
                }
            else:
                return {
                    "success": False,
                    "error": f"API returned status {response.status_code}: {response.text}"
                }
                
        except requests.RequestException as e:
            logger.error(f"Failed to fetch GoHighLevel contacts: {e}")
            return {"success": False, "error": str(e)}
    
    def get_contact_by_id(self, contact_id: str) -> Dict[str, Any]:
        """Fetch a specific contact by ID"""
        try:
            response = requests.get(
                f"{self.BASE_URL}/contacts/{contact_id}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                contact_data = response.json()
                return {"success": True, "contact": contact_data.get("contact", {})}
            else:
                return {
                    "success": False,
                    "error": f"API returned status {response.status_code}: {response.text}"
                }
                
        except requests.RequestException as e:
            logger.error(f"Failed to fetch GoHighLevel contact {contact_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def create_contact(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new contact in GoHighLevel"""
        try:
            payload = {
                "locationId": self.location_id,
                **contact_data
            }
            
            response = requests.post(
                f"{self.BASE_URL}/contacts/",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                created_contact = response.json()
                return {"success": True, "contact": created_contact.get("contact", {})}
            else:
                return {
                    "success": False,
                    "error": f"API returned status {response.status_code}: {response.text}"
                }
                
        except requests.RequestException as e:
            logger.error(f"Failed to create GoHighLevel contact: {e}")
            return {"success": False, "error": str(e)}
    
    def update_contact(self, contact_id: str, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing contact in GoHighLevel"""
        try:
            response = requests.put(
                f"{self.BASE_URL}/contacts/{contact_id}",
                headers=self.headers,
                json=contact_data,
                timeout=30
            )
            
            if response.status_code == 200:
                updated_contact = response.json()
                return {"success": True, "contact": updated_contact.get("contact", {})}
            else:
                return {
                    "success": False,
                    "error": f"API returned status {response.status_code}: {response.text}"
                }
                
        except requests.RequestException as e:
            logger.error(f"Failed to update GoHighLevel contact {contact_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def delete_contact(self, contact_id: str) -> Dict[str, Any]:
        """Delete a contact from GoHighLevel"""
        try:
            response = requests.delete(
                f"{self.BASE_URL}/contacts/{contact_id}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code in [200, 204]:
                return {"success": True, "message": "Contact deleted successfully"}
            else:
                return {
                    "success": False,
                    "error": f"API returned status {response.status_code}: {response.text}"
                }
                
        except requests.RequestException as e:
            logger.error(f"Failed to delete GoHighLevel contact {contact_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def sync_contacts_to_local(self) -> Dict[str, Any]:
        """Sync contacts from GoHighLevel to local database"""
        if not self.user:
            return {"success": False, "error": "User not provided"}
        
        synced_count = 0
        updated_count = 0
        error_count = 0
        
        try:
            # Fetch all contacts from GoHighLevel
            offset = 0
            limit = 100
            
            while True:
                result = self.get_contacts(limit=limit, offset=offset)
                
                if not result["success"]:
                    logger.error(f"Failed to fetch contacts: {result['error']}")
                    break
                
                contacts = result["contacts"]
                if not contacts:
                    break
                
                # Process each contact
                for ghl_contact in contacts:
                    try:
                        self._sync_single_contact(ghl_contact)
                        
                        # Check if it's an update or new contact
                        if CRMContact.objects.filter(
                            user=self.user, 
                            ghl_contact_id=ghl_contact.get("id")
                        ).exists():
                            updated_count += 1
                        else:
                            synced_count += 1
                            
                    except Exception as e:
                        logger.error(f"Error syncing contact {ghl_contact.get('id')}: {e}")
                        error_count += 1
                
                # Check if we've fetched all contacts
                if len(contacts) < limit:
                    break
                
                offset += limit
            
            # Update integration sync date
            if hasattr(self, 'integration') and self.integration:
                self.integration.last_sync_date = django_timezone.now()
                self.integration.save()
            
            return {
                "success": True,
                "synced_count": synced_count,
                "updated_count": updated_count,
                "error_count": error_count,
                "total_processed": synced_count + updated_count + error_count
            }
            
        except Exception as e:
            logger.error(f"Error during contact sync: {e}")
            return {"success": False, "error": str(e)}
    
    def _sync_single_contact(self, ghl_contact: Dict[str, Any]) -> CRMContact:
        """Sync a single contact to local database"""
        contact_id = ghl_contact.get("id")
        
        # Parse dates
        ghl_created_at = None
        ghl_updated_at = None
        
        if ghl_contact.get("dateAdded"):
            try:
                ghl_created_at = datetime.fromtimestamp(
                    int(ghl_contact["dateAdded"]) / 1000, 
                    tz=timezone.utc
                )
            except (ValueError, TypeError):
                pass
        
        if ghl_contact.get("dateUpdated"):
            try:
                ghl_updated_at = datetime.fromtimestamp(
                    int(ghl_contact["dateUpdated"]) / 1000, 
                    tz=timezone.utc
                )
            except (ValueError, TypeError):
                pass
        
        # Extract social media profiles
        social_profiles = {}
        custom_fields = ghl_contact.get("customFields", {})
        
        for field_name, field_value in custom_fields.items():
            if any(platform in field_name.lower() for platform in ['facebook', 'instagram', 'twitter', 'linkedin', 'tiktok']):
                social_profiles[field_name] = field_value
        
        # Create or update contact
        contact, created = CRMContact.objects.update_or_create(
            user=self.user,
            ghl_contact_id=contact_id,
            defaults={
                'first_name': ghl_contact.get("firstName", ""),
                'last_name': ghl_contact.get("lastName", ""),
                'email': ghl_contact.get("email", ""),
                'phone': ghl_contact.get("phone", ""),
                'company': ghl_contact.get("companyName", ""),
                'status': self._map_ghl_status(ghl_contact.get("tags", [])),
                'tags': ghl_contact.get("tags", []),
                'custom_fields': custom_fields,
                'social_media_profiles': social_profiles,
                'ghl_created_at': ghl_created_at,
                'ghl_updated_at': ghl_updated_at,
            }
        )
        
        if created:
            logger.info(f"Created new CRM contact: {contact.full_name}")
        else:
            logger.info(f"Updated CRM contact: {contact.full_name}")
        
        return contact
    
    def _map_ghl_status(self, tags: List[str]) -> str:
        """Map GoHighLevel tags to contact status"""
        tag_lower = [tag.lower() for tag in tags]
        
        if any(tag in tag_lower for tag in ['customer', 'client', 'paid']):
            return 'customer'
        elif any(tag in tag_lower for tag in ['prospect', 'lead', 'interested']):
            return 'prospect'
        elif any(tag in tag_lower for tag in ['unsubscribed', 'opt-out', 'do not contact']):
            return 'unsubscribed'
        elif any(tag in tag_lower for tag in ['inactive', 'cold', 'lost']):
            return 'inactive'
        else:
            return 'active'
    
    def get_opportunities(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Fetch opportunities from GoHighLevel"""
        try:
            params = {
                "locationId": self.location_id,
                "limit": limit,
                "skip": offset
            }
            
            response = requests.get(
                f"{self.BASE_URL}/opportunities/",
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "opportunities": data.get("opportunities", []),
                    "total": data.get("count", 0),
                    "meta": data.get("meta", {})
                }
            else:
                return {
                    "success": False,
                    "error": f"API returned status {response.status_code}: {response.text}"
                }
                
        except requests.RequestException as e:
            logger.error(f"Failed to fetch GoHighLevel opportunities: {e}")
            return {"success": False, "error": str(e)}
    
    def create_opportunity(self, opportunity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new opportunity in GoHighLevel"""
        try:
            payload = {
                "locationId": self.location_id,
                **opportunity_data
            }
            
            response = requests.post(
                f"{self.BASE_URL}/opportunities/",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                created_opportunity = response.json()
                return {"success": True, "opportunity": created_opportunity.get("opportunity", {})}
            else:
                return {
                    "success": False,
                    "error": f"API returned status {response.status_code}: {response.text}"
                }
                
        except requests.RequestException as e:
            logger.error(f"Failed to create GoHighLevel opportunity: {e}")
            return {"success": False, "error": str(e)}
    
    def get_campaigns(self) -> Dict[str, Any]:
        """Fetch campaigns from GoHighLevel"""
        try:
            params = {"locationId": self.location_id}
            
            response = requests.get(
                f"{self.BASE_URL}/campaigns/",
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "campaigns": data.get("campaigns", [])
                }
            else:
                return {
                    "success": False,
                    "error": f"API returned status {response.status_code}: {response.text}"
                }
                
        except requests.RequestException as e:
            logger.error(f"Failed to fetch GoHighLevel campaigns: {e}")
            return {"success": False, "error": str(e)}
    
    def add_contact_to_campaign(self, contact_id: str, campaign_id: str) -> Dict[str, Any]:
        """Add a contact to a campaign"""
        try:
            payload = {
                "contactId": contact_id,
                "campaignId": campaign_id
            }
            
            response = requests.post(
                f"{self.BASE_URL}/campaigns/{campaign_id}/contacts",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                return {"success": True, "message": "Contact added to campaign"}
            else:
                return {
                    "success": False,
                    "error": f"API returned status {response.status_code}: {response.text}"
                }
                
        except requests.RequestException as e:
            logger.error(f"Failed to add contact to campaign: {e}")
            return {"success": False, "error": str(e)}
    
    def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming webhooks from GoHighLevel"""
        try:
            event_type = payload.get("type")
            data = payload.get("data", {})
            
            if event_type == "contact.create":
                return self._handle_contact_created(data)
            elif event_type == "contact.update":
                return self._handle_contact_updated(data)
            elif event_type == "contact.delete":
                return self._handle_contact_deleted(data)
            else:
                logger.info(f"Unhandled GoHighLevel webhook event: {event_type}")
                return {"success": True, "message": "Event ignored"}
                
        except Exception as e:
            logger.error(f"Error handling GoHighLevel webhook: {e}")
            return {"success": False, "error": str(e)}
    
    def _handle_contact_created(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle contact creation webhook"""
        if not self.user:
            return {"success": False, "error": "User not provided"}
        
        try:
            self._sync_single_contact(contact_data)
            return {"success": True, "message": "Contact synced"}
        except Exception as e:
            logger.error(f"Error syncing new contact: {e}")
            return {"success": False, "error": str(e)}
    
    def _handle_contact_updated(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle contact update webhook"""
        if not self.user:
            return {"success": False, "error": "User not provided"}
        
        try:
            self._sync_single_contact(contact_data)
            return {"success": True, "message": "Contact updated"}
        except Exception as e:
            logger.error(f"Error updating contact: {e}")
            return {"success": False, "error": str(e)}
    
    def _handle_contact_deleted(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle contact deletion webhook"""
        if not self.user:
            return {"success": False, "error": "User not provided"}
        
        try:
            contact_id = contact_data.get("id")
            if contact_id:
                CRMContact.objects.filter(
                    user=self.user, 
                    ghl_contact_id=contact_id
                ).delete()
                logger.info(f"Deleted CRM contact {contact_id}")
            
            return {"success": True, "message": "Contact deleted"}
        except Exception as e:
            logger.error(f"Error deleting contact: {e}")
            return {"success": False, "error": str(e)}
