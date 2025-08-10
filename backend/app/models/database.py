from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ARRAY, JSON, ForeignKey, Float, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from ..db.base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unique_id = Column(String, unique=True, index=True)
    phone_number = Column(String, unique=True, index=True)
    display_name = Column(String)
    groups_joined = Column(ARRAY(String), default=[])
    first_seen_date = Column(DateTime(timezone=True), server_default=func.now())
    last_active_date = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    messages = relationship("Message", back_populates="user")
    items_for_sale = relationship("ItemForSale", back_populates="user")
    apartments = relationship("Apartment", back_populates="user")

class Group(Base):
    __tablename__ = "groups"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(String, unique=True, index=True)  # WhatsApp group ID
    group_name = Column(String, index=True)
    university = Column(String, index=True)
    category = Column(String)  # general, housing, marketplace, etc.
    member_count = Column(Integer)
    last_scraped = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    
    # Relationships
    messages = relationship("Message", back_populates="group")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(String, unique=True, index=True)  # WhatsApp message ID
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), index=True)
    content = Column(Text)
    timestamp = Column(DateTime(timezone=True))
    message_type = Column(String)  # text, image, document, etc.
    processed = Column(Boolean, default=False)
    extracted_entities = Column(JSON)
    reactions = Column(JSON)
    links = Column(ARRAY(String))
    has_media = Column(Boolean, default=False)
    media_info = Column(JSON)
    # Deduplication and analytics
    content_hash = Column(String, index=True)
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now())
    occurrence_count = Column(Integer, default=1)
    
    # Relationships
    user = relationship("User", back_populates="messages")
    group = relationship("Group", back_populates="messages")
    items_for_sale = relationship("ItemForSale", back_populates="message")
    apartments = relationship("Apartment", back_populates="message")

class ItemForSale(Base):
    __tablename__ = "items_for_sale"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(String, unique=True, index=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    
    # Item Details
    title = Column(String, index=True)
    description = Column(Text)
    price = Column(DECIMAL(10, 2))
    category = Column(String, index=True)
    condition = Column(String)  # new, like_new, good, fair, poor
    images = Column(ARRAY(String))
    contact_info = Column(JSON)
    location = Column(String)
    
    # Status
    availability_status = Column(String, default="available")  # available, sold, pending
    posted_date = Column(DateTime(timezone=True), server_default=func.now())
    expires_date = Column(DateTime(timezone=True))
    
    # Search and ranking
    view_count = Column(Integer, default=0)
    inquiry_count = Column(Integer, default=0)
    
    # Relationships
    message = relationship("Message", back_populates="items_for_sale")
    user = relationship("User", back_populates="items_for_sale")

class Apartment(Base):
    __tablename__ = "apartments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(String, unique=True, index=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    
    # Listing Details
    listing_type = Column(String, index=True)  # roommate, sublet, rental
    address = Column(String)
    price_per_month = Column(DECIMAL(10, 2), index=True)
    bedrooms = Column(Integer)
    bathrooms = Column(Float)
    amenities = Column(ARRAY(String))
    lease_duration = Column(String)
    
    # Dates
    available_from = Column(DateTime(timezone=True))
    available_until = Column(DateTime(timezone=True))
    posted_date = Column(DateTime(timezone=True), server_default=func.now())
    
    # Additional Info
    contact_info = Column(JSON)
    images = Column(ARRAY(String))
    key_features = Column(ARRAY(String))
    utilities_included = Column(Boolean)
    furnished = Column(Boolean)
    pet_friendly = Column(Boolean)
    
    # Status
    availability_status = Column(String, default="available")  # available, rented, pending
    view_count = Column(Integer, default=0)
    inquiry_count = Column(Integer, default=0)
    
    # Relationships
    message = relationship("Message", back_populates="apartments")
    user = relationship("User", back_populates="apartments")

class ProcessingLog(Base):
    __tablename__ = "processing_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(String, index=True)
    message_id = Column(String)
    processing_type = Column(String)  # categorization, extraction, etc.
    status = Column(String)  # processing, completed, failed
    result = Column(JSON)
    error_message = Column(Text)
    processed_at = Column(DateTime(timezone=True), server_default=func.now())
    processing_time_ms = Column(Integer)


class CanonicalMessage(Base):
    __tablename__ = "canonical_messages"

    # One row per unique normalized content across all groups
    content_hash = Column(String, primary_key=True)
    content = Column(Text)
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now())
    occurrence_total = Column(Integer, default=1)
    groups_seen = Column(ARRAY(String), default=[])