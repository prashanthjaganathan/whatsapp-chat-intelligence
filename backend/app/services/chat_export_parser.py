import re
from datetime import datetime, timezone
from typing import Iterator, List, Dict, Any, Optional, Tuple
import hashlib
import re as _re

TIMESTAMP_LINE_REGEX = re.compile(
    r"^\[(?P<date>\d{1,2}/\d{1,2}/\d{2,4}),\s*(?P<time>\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)\]\s*~?\s*(?P<sender>[^:]+):\s?(?P<body>.*?)(?=^\[|\Z)",
    re.DOTALL | re.MULTILINE | re.IGNORECASE
)

URL_REGEX = re.compile(r"https?://[^\s]+", re.IGNORECASE)
PHONE_IN_NAME_REGEX = re.compile(r"\+?\d[\d\s\-()]{6,}")

# Some exports contain a narrow no-break space before AM/PM. Normalize it.
SPACE_NORMALIZER = str.maketrans({
    "\u202F": " ",  # narrow no-break space
    "\u00A0": " ",  # non-breaking space
})

def _try_parse_datetime(date_str: str, time_str: str) -> Optional[datetime]:
    """Try multiple datetime formats commonly found in WhatsApp exports.
    Returns timezone-aware UTC datetime if possible.
    """
    raw = f"{date_str}, {time_str}".translate(SPACE_NORMALIZER).strip()
    patterns: List[Tuple[str, bool]] = [
        ("%d/%m/%y, %I:%M:%S %p", True),
        ("%d/%m/%y, %I:%M %p", True),
        ("%d/%m/%y, %H:%M:%S", True),
        ("%d/%m/%y, %H:%M", True),
        ("%d/%m/%Y, %I:%M:%S %p", True),
        ("%d/%m/%Y, %I:%M %p", True),
        ("%d/%m/%Y, %H:%M:%S", True),
        ("%d/%m/%Y, %H:%M", True),
        # Fallbacks for month-first locales
        ("%m/%d/%y, %I:%M:%S %p", False),
        ("%m/%d/%y, %I:%M %p", False),
        ("%m/%d/%y, %H:%M:%S", False),
        ("%m/%d/%y, %H:%M", False),
        ("%m/%d/%Y, %I:%M:%S %p", False),
        ("%m/%d/%Y, %I:%M %p", False),
        ("%m/%d/%Y, %H:%M:%S", False),
        ("%m/%d/%Y, %H:%M", False),
    ]
    
    for fmt, _ in patterns:
        try:
            dt = datetime.strptime(raw, fmt)
            # Assume local export time; store as UTC naive by default -> convert to UTC-aware
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None

def _extract_links(text: str) -> List[str]:
    return URL_REGEX.findall(text or "")

def _extract_phone_from_name(sender: str) -> Optional[str]:
    m = PHONE_IN_NAME_REGEX.search(sender)
    if m:
        # Normalize digits only with leading + if present
        digits = re.sub(r"[^\d+]", "", m.group(0))
        return digits
    return None

def _make_message_id(group_name: str, timestamp: datetime, sender: str, body: str) -> str:
    base = f"{group_name}|{timestamp.isoformat()}|{sender}|{body[:100]}".encode("utf-8")
    return hashlib.sha256(base).hexdigest()


_WS_RE = _re.compile(r"\s+")
_PUNCT_RE = _re.compile(r"[\s\-_,.!?:;~*`'\"]+")
PHONE_BODY_REGEX = _re.compile(r"\+?\d[\d\s\-()]{6,}")
MONEY_REGEX = _re.compile(r"\$?\b\d[\d,]*(?:\.\d+)?\b")

def compute_content_hash(text: str) -> str:
    """Compute a stable content hash for deduplication.
    Steps:
    - Lowercase
    - Normalize whitespace
    - Strip typical punctuation floods and markdown emphasis
    - Trim
    """
    if not text:
        return hashlib.sha256(b"\x00").hexdigest()
    t = text
    # Remove URLs and phone numbers and money amounts to reduce near-duplicate variance
    t = URL_REGEX.sub(" ", t)
    # t = PHONE_BODY_REGEX.sub(" ", t)
    t = MONEY_REGEX.sub(" ", t)
    t = t.lower()
    # Normalize punctuation and whitespace
    t = _PUNCT_RE.sub(" ", t)
    t = _WS_RE.sub(" ", t)
    t = t.strip()
    return hashlib.sha256(t.encode("utf-8")).hexdigest()

def parse_chat_export(lines: Iterator[str], since: Optional[datetime] = None) -> Dict[str, Any]:
    """Parse a WhatsApp exported chat text file.
    Returns dict with keys:
    - group_name: str
    - messages: List[{
        message_id, sender_name, sender_phone, timestamp (datetime), body, links: List[str]
    }]
    """
    # Join all lines into one text for proper multiline regex matching
    text = ''.join(lines).translate(SPACE_NORMALIZER)
    
    group_name: Optional[str] = None
    messages: List[Dict[str, Any]] = []
    
    # Extract group name from first line if possible
    first_line = text.split('\n')[0] if text else ""
    if group_name is None:
        # Pattern: [dd/mm/yy, time] Group Name: message...
        m = re.match(r"^\[(\d{1,2}/\d{1,2}/\d{2,4}),\s*[^\]]+\]\s*(.+?):", first_line)
        if m:
            group_name = m.group(2).strip()
        else:
            # Fallback group name
            group_name = "Unknown Group"
    
    # Find all timestamp matches in the entire text
    for match in TIMESTAMP_LINE_REGEX.finditer(text):
        date_str = match.group("date")
        time_str = match.group("time")
        sender = match.group("sender").strip()
        body = match.group("body") or ""
        
        # Clean up the body - remove extra whitespace but preserve intentional formatting
        body = body.strip()
        
        ts = _try_parse_datetime(date_str, time_str)

        if ts is not None and since is not None and ts < since:
            # Skip if timestamp cannot be parsed or is before since
            continue
            
        sender_phone = _extract_phone_from_name(sender)
        
        current = {
            "group_name": group_name or "Unknown Group",
            "sender_name": sender,
            "sender_phone": sender_phone,
            "timestamp": ts,
            "body": body,
            "links": _extract_links(body),
        }
        
        # Add message ID
        current["message_id"] = _make_message_id(
            current["group_name"], current["timestamp"], current["sender_name"], current["body"]
        )
        
        messages.append(current)
    
    print(f'Messages: {len(messages)}\nSample: {messages[1]}')
    
    return {"group_name": group_name or "[UNK]", "messages": messages}