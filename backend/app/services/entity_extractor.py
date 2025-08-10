import re
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session

from ..models.database import Message, ItemForSale, Apartment, User
from .llm_extractor import LLMExtractor
from .chat_export_parser import _extract_links  # reuse link extractor

PRICE_REGEX = re.compile(r"(?:\$\s*)?(\d{2,5})(?:\.\d{1,2})?", re.IGNORECASE)
PHONE_REGEX = re.compile(r"\+?\d[\d\s\-()]{6,}")
EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

ITEM_KEYWORDS = [
    "for sale", "selling", "price", "available", "condition", "pickup",
    "microwave", "sofa", "chair", "table", "desk", "laptop", "iphone",
    "textbook", "bike", "cycle", "vacuum", "mattress", "bed frame",
]
HOUSING_KEYWORDS = [
    "accommodation", "room", "bed", "bath", "lease", "sublet",
    "rent", "apartment", "roommate", "spot available", "move in",
]

CATEGORY_KEYWORDS = {
    "furniture": ["sofa", "chair", "table", "desk", "mattress", "bed", "dresser"],
    "electronics": ["laptop", "iphone", "ipad", "tv", "monitor", "camera"],
    "kitchen": ["microwave", "toaster", "kettle", "blender", "pan", "pot"],
    "textbooks": ["textbook", "book", "course"],
    "appliances": ["vacuum", "washer", "dryer"],
}


def _contains_any(text: str, keywords: List[str]) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)


def _extract_price(text: str) -> Optional[float]:
    m = PRICE_REGEX.search(text.replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _extract_phone(text: str) -> Optional[str]:
    m = PHONE_REGEX.search(text)
    if not m:
        return None
    return re.sub(r"[^\d+]", "", m.group(0))


def _extract_email(text: str) -> Optional[str]:
    m = EMAIL_REGEX.search(text)
    if not m:
        return None
    return m.group(0)


def _infer_category(text: str) -> str:
    t = text.lower()
    for cat, words in CATEGORY_KEYWORDS.items():
        if any(w in t for w in words):
            return cat
    return "other"


def _infer_listing_type(text: str) -> str:
    t = text.lower()
    if "sublet" in t:
        return "sublet"
    if "roommate" in t or ("looking for" in t and "roommate" in t):
        return "roommate_wanted"
    if "room available" in t or "spot available" in t:
        return "room_available"
    return "rental"


class EntityExtractor:
    """Processes DB messages into ItemForSale/Apartment entities.
    Uses LLM if configured; falls back to regex-based heuristics.
    """
    def __init__(self, db: Session, use_llm: bool = False):
        self.db = db
        self.use_llm = use_llm
        self.llm = LLMExtractor() if use_llm else None

    async def process_unprocessed(self, limit: int = 200) -> Dict[str, int]:
        q = (
            self.db.query(Message)
            .filter(Message.processed == False)  # noqa: E712
            .order_by(Message.timestamp.asc())
            .limit(limit)
        )
        messages: List[Message] = q.all()
        stats = {"messages": 0, "items": 0, "apartments": 0}

        for msg in messages:
            content = (msg.content or "").strip()
            if not content:
                msg.processed = True
                stats["messages"] += 1
                continue

            category = None
            item_data: Optional[Dict[str, Any]] = None
            apt_data: Optional[Dict[str, Any]] = None

            if self.use_llm and self.llm:
                try:
                    category = await self.llm.categorize_message(content)
                except Exception:
                    category = None

            # Heuristic categorization if no LLM or failure
            if not category:
                if _contains_any(content, HOUSING_KEYWORDS):
                    category = "APARTMENT_LISTING"
                elif _contains_any(content, ITEM_KEYWORDS):
                    category = "ITEM_FOR_SALE"
                else:
                    category = "GENERAL"

            if category == "ITEM_FOR_SALE":
                if self.use_llm and self.llm:
                    item_data = await self.llm.extract_item_data(content)
                if not item_data:
                    item_data = {
                        "title": content.splitlines()[0][:80],
                        "description": content,
                        "price": _extract_price(content),
                        "category": _infer_category(content),
                        "condition": None,
                        "contact_phone": _extract_phone(content),
                        "contact_email": _extract_email(content),
                        "location": None,
                    }
                await self._create_item(msg, item_data)
                stats["items"] += 1

            elif category == "APARTMENT_LISTING":
                if self.use_llm and self.llm:
                    apt_data = await self.llm.extract_housing_data(content)
                if not apt_data:
                    apt_data = {
                        "listing_type": _infer_listing_type(content),
                        "address": None,
                        "price": _extract_price(content),
                        "bedrooms": None,
                        "bathrooms": None,
                        "lease_duration": None,
                        "available_from": None,
                        "available_until": None,
                        "amenities": [],
                        "furnished": None,
                        "utilities_included": None,
                        "pet_friendly": None,
                        "contact_phone": _extract_phone(content),
                        "contact_email": _extract_email(content),
                        "key_features": [],
                    }
                await self._create_apartment(msg, apt_data)
                stats["apartments"] += 1

            # Mark processed regardless
            msg.processed = True
            stats["messages"] += 1

        self.db.commit()
        return stats

    async def _create_item(self, message: Message, data: Dict[str, Any]) -> None:
        contact_info: Dict[str, Any] = {}
        if data.get("contact_phone"):
            contact_info["phone"] = data["contact_phone"]
        if data.get("contact_email"):
            contact_info["email"] = data["contact_email"]
        # Links as fallback contact
        links = _extract_links(message.content or "")
        if not contact_info and links:
            contact_info["link"] = links[0]

        item = ItemForSale(
            item_id=f"item::{message.message_id}",
            message_id=message.id,
            user_id=message.user_id,
            title=data.get("title") or "Untitled",
            description=data.get("description") or message.content,
            price=data.get("price"),
            category=data.get("category") or "other",
            condition=data.get("condition"),
            contact_info=contact_info,
            location=data.get("location"),
            availability_status="available",
            posted_date=message.timestamp,
        )
        self.db.add(item)

    async def _create_apartment(self, message: Message, data: Dict[str, Any]) -> None:
        contact_info: Dict[str, Any] = {}
        if data.get("contact_phone"):
            contact_info["phone"] = data["contact_phone"]
        if data.get("contact_email"):
            contact_info["email"] = data["contact_email"]
        links = _extract_links(message.content or "")
        if not contact_info and links:
            contact_info["link"] = links[0]

        apt = Apartment(
            listing_id=f"apt::{message.message_id}",
            message_id=message.id,
            user_id=message.user_id,
            listing_type=data.get("listing_type") or "rental",
            address=data.get("address"),
            price_per_month=data.get("price"),
            bedrooms=data.get("bedrooms"),
            bathrooms=data.get("bathrooms"),
            amenities=data.get("amenities") or [],
            lease_duration=data.get("lease_duration"),
            available_from=None,
            available_until=None,
            contact_info=contact_info,
            key_features=data.get("key_features") or [],
            utilities_included=data.get("utilities_included"),
            furnished=data.get("furnished"),
            pet_friendly=data.get("pet_friendly"),
            availability_status="available",
            posted_date=message.timestamp,
        )
        self.db.add(apt)
