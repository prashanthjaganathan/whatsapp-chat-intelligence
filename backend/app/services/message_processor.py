import asyncio
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid

from ..models.database import User, Group, Message, ItemForSale, Apartment, ProcessingLog
from .llm_extractor import LLMExtractor
from ..core.config import settings

class MessageProcessor:
    def __init__(self, db: Session):
        self.db = db
        self.llm_extractor = LLMExtractor()
    
    async def process_scraped_data(self, scraped_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process scraped WhatsApp group data."""
        results = {
            "group_processed": False,
            "users_created": 0,
            "users_updated": 0,
            "messages_processed": 0,
            "items_extracted": 0,
            "apartments_extracted": 0,
            "errors": []
        }
        
        try:
            # Process group info
            group = await self._process_group_info(scraped_data["groupInfo"])
            results["group_processed"] = True
            
            # Process members (users)
            user_stats = await self._process_members(scraped_data["members"])
            results["users_created"] = user_stats["created"]
            results["users_updated"] = user_stats["updated"]
            
            # Process messages
            message_stats = await self._process_messages(scraped_data["messages"], group.id)
            results["messages_processed"] = message_stats["processed"]
            results["items_extracted"] = message_stats["items_extracted"]
            results["apartments_extracted"] = message_stats["apartments_extracted"]
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            results["errors"].append(f"Processing failed: {str(e)}")
        
        return results
    
    async def _process_group_info(self, group_info: Dict[str, Any]) -> Group:
        """Process and store group information."""
        existing_group = self.db.query(Group).filter(
            Group.group_id == group_info["id"]
        ).first()
        
        if existing_group:
            # Update existing group
            existing_group.group_name = group_info["name"]
            existing_group.member_count = group_info["participantCount"]
            existing_group.last_scraped = datetime.utcnow()
            return existing_group
        else:
            # Create new group
            new_group = Group(
                group_id=group_info["id"],
                group_name=group_info["name"],
                university=group_info.get("university", "Unknown"),
                category=",".join(group_info.get("categories", ["general"])),
                member_count=group_info["participantCount"],
                last_scraped=datetime.utcnow()
            )
            self.db.add(new_group)
            self.db.flush()  # Get ID
            return new_group
    
    async def _process_members(self, members: List[Dict[str, Any]]) -> Dict[str, int]:
        """Process group members and create/update users."""
        stats = {"created": 0, "updated": 0}
        
        for member_data in members:
            try:
                phone = member_data.get("phone", "").strip()
                if not phone:
                    continue
                
                # Check if user exists
                existing_user = self.db.query(User).filter(
                    User.phone_number == phone
                ).first()
                
                if existing_user:
                    # Update existing user
                    existing_user.display_name = member_data.get("name", "Unknown")
                    existing_user.last_active_date = datetime.utcnow()
                    stats["updated"] += 1
                else:
                    # Create new user
                    new_user = User(
                        unique_id=f"user_{uuid.uuid4().hex[:12]}",
                        phone_number=phone,
                        display_name=member_data.get("name", "Unknown"),
                        groups_joined=[],  # Will be updated when processing messages
                        first_seen_date=datetime.utcnow(),
                        last_active_date=datetime.utcnow()
                    )
                    self.db.add(new_user)
                    stats["created"] += 1
                    
            except Exception as e:
                print(f"Error processing member {member_data}: {e}")
                continue
        
        return stats
    
    async def _process_messages(self, messages: List[Dict[str, Any]], group_id: str) -> Dict[str, int]:
        """Process messages and extract items/apartments."""
        stats = {
            "processed": 0,
            "items_extracted": 0,
            "apartments_extracted": 0
        }
        
        # Process messages in batches to avoid overwhelming the LLM APIs
        batch_size = settings.PROCESSING_BATCH_SIZE
        
        for i in range(0, len(messages), batch_size):
            batch = messages[i:i + batch_size]
            
            for message_data in batch:
                try:
                    message_stats = await self._process_single_message(message_data, group_id)
                    stats["processed"] += message_stats["processed"]
                    stats["items_extracted"] += message_stats["items_extracted"] 
                    stats["apartments_extracted"] += message_stats["apartments_extracted"]
                    
                except Exception as e:
                    print(f"Error processing message {message_data.get('id', 'unknown')}: {e}")
                    continue
            
            # Rate limiting between batches
            await asyncio.sleep(settings.LLM_RATE_LIMIT_DELAY)
        
        return stats
    
    async def _process_single_message(self, message_data: Dict[str, Any], group_id: str) -> Dict[str, int]:
        """Process a single message."""
        stats = {"processed": 0, "items_extracted": 0, "apartments_extracted": 0}
        
        # Check if message already exists
        existing_message = self.db.query(Message).filter(
            Message.message_id == message_data["id"]
        ).first()
        
        if existing_message and existing_message.processed:
            return stats  # Already processed
        
        # Get or create user
        user = await self._get_or_create_user_from_message(message_data)
        if not user:
            return stats
        
        # Get group
        group = self.db.query(Group).filter(Group.id == group_id).first()
        if not group:
            return stats
        
        # Create or update message
        if existing_message:
            message = existing_message
        else:
            message = Message(
                message_id=message_data["id"],
                user_id=user.id,
                group_id=group.id,
                content=message_data.get("body", ""),
                timestamp=datetime.fromtimestamp(message_data["timestamp"]),
                message_type=message_data.get("type", "text"),
                reactions=message_data.get("reactions", []),
                links=message_data.get("links", []),
                has_media=message_data.get("hasMedia", False),
                media_info=message_data.get("media"),
                processed=False
            )
            self.db.add(message)
            self.db.flush()  # Get ID
        
        # Skip empty messages
        content = message_data.get("body", "").strip()
        if not content or len(content) < 10:
            message.processed = True
            stats["processed"] = 1
            return stats
        
        # Categorize and extract via LLM with structured outputs
        try:
            category = await self.llm_extractor.categorize_message(content)
            if category == "ITEM_FOR_SALE":
                item_data = await self.llm_extractor.extract_item_data(content)
                if item_data:
                    await self._create_item_for_sale(item_data, message, user)
                    stats["items_extracted"] = 1
            elif category == "APARTMENT_LISTING":
                apartment_data = await self.llm_extractor.extract_housing_data(content)
                if apartment_data:
                    await self._create_apartment_listing(apartment_data, message, user)
                    stats["apartments_extracted"] = 1
            
            # Store extracted entities
            message.extracted_entities = {
                "category": category,
                "processed_at": datetime.utcnow().isoformat()
            }
            message.processed = True
            stats["processed"] = 1
        except Exception as e:
            print(f"Error processing message content: {e}")
            # Mark as processed even if extraction failed
            message.processed = True
            stats["processed"] = 1
        
        return stats
    
    async def _get_or_create_user_from_message(self, message_data: Dict[str, Any]) -> Optional[User]:
        """Get or create user from message data."""
        phone = message_data.get("authorPhone", "").strip()
        if not phone:
            return None
        
        # Check if user exists
        user = self.db.query(User).filter(User.phone_number == phone).first()
        
        if not user:
            # Create new user
            user = User(
                unique_id=f"user_{uuid.uuid4().hex[:12]}",
                phone_number=phone,
                display_name="Unknown",  # Will be updated from member data
                groups_joined=[],
                first_seen_date=datetime.utcnow(),
                last_active_date=datetime.utcnow()
            )
            self.db.add(user)
            self.db.flush()
        
        return user
    
    async def _create_item_for_sale(self, item_data: Dict[str, Any], message: Message, user: User):
        """Create ItemForSale from extracted data."""
        try:
            contact_info: Dict[str, Any] = {}
            if item_data.get("contact_phone"):
                contact_info["phone"] = item_data["contact_phone"]
            if item_data.get("contact_email"):
                contact_info["email"] = item_data["contact_email"]
            if not contact_info and (message.links or []):
                contact_info["link"] = (message.links or [None])[0]

            item = ItemForSale(
                item_id=f"item_{uuid.uuid4().hex[:12]}",
                message_id=message.id,
                user_id=user.id,
                title=item_data.get("title", ""),
                description=item_data.get("description", ""),
                price=item_data.get("price"),
                category=item_data.get("category", "other"),
                condition=item_data.get("condition"),
                contact_info=contact_info,
                location=item_data.get("location"),
                availability_status="available",
                posted_date=message.timestamp
            )
            self.db.add(item)
        except Exception as e:
            print(f"Error creating item for sale: {e}")
    
    async def _create_apartment_listing(self, apartment_data: Dict[str, Any], message: Message, user: User):
        """Create Apartment from extracted data."""
        try:
            contact_info: Dict[str, Any] = {}
            if apartment_data.get("contact_phone"):
                contact_info["phone"] = apartment_data["contact_phone"]
            if apartment_data.get("contact_email"):
                contact_info["email"] = apartment_data["contact_email"]
            if not contact_info and (message.links or []):
                contact_info["link"] = (message.links or [None])[0]

            apartment = Apartment(
                listing_id=f"apt_{uuid.uuid4().hex[:12]}",
                message_id=message.id,
                user_id=user.id,
                listing_type=apartment_data.get("listing_type", ""),
                address=apartment_data.get("address"),
                price_per_month=apartment_data.get("price"),
                bedrooms=apartment_data.get("bedrooms"),
                bathrooms=apartment_data.get("bathrooms"),
                amenities=apartment_data.get("amenities", []),
                lease_duration=apartment_data.get("lease_duration"),
                contact_info=contact_info,
                key_features=apartment_data.get("key_features", []),
                utilities_included=apartment_data.get("utilities_included"),
                furnished=apartment_data.get("furnished"),
                pet_friendly=apartment_data.get("pet_friendly"),
                availability_status="available",
                posted_date=message.timestamp
            )
            
            # Parse dates if provided
            if apartment_data.get("available_from"):
                try:
                    apartment.available_from = datetime.fromisoformat(str(apartment_data["available_from"]))
                except:
                    pass
                    
            if apartment_data.get("available_until"):
                try:
                    apartment.available_until = datetime.fromisoformat(str(apartment_data["available_until"]))
                except:
                    pass
            
            self.db.add(apartment)
        except Exception as e:
            print(f"Error creating apartment listing: {e}")