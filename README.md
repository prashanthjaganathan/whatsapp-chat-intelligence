# Whatsapp Chat Intelligence

A FastAPI backend for ingesting, searching, and extracting structured data from WhatsApp chat exports. Features deduplication, full-text search, and entity extraction for items and apartments.

## Features

- **WhatsApp Chat Import**: Parse and ingest `_chat.txt` export files
- **Message Deduplication**: Global and per-group deduplication using content hashing
- **Full-Text Search**: Fast PostgreSQL-based search across all messages
- **Entity Extraction**: Extract items for sale and apartment listings
- **Structured Exports**: JSON exports with seller and group information
- **Bot-Friendly APIs**: Simple endpoints for chat bots and applications

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- macOS/Linux/Windows

## Installation

### 1. Install PostgreSQL

**macOS (using Homebrew):**
```bash
brew install postgresql@16
brew services start postgresql@16
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**Windows:**
Download and install from [PostgreSQL official website](https://www.postgresql.org/download/windows/)

### 2. Create Database and User

Connect to PostgreSQL as the default user:

**macOS (Homebrew):**
```bash
psql postgres
```

**Ubuntu/Debian:**
```bash
sudo -u postgres psql
```

**Windows:**
```bash
psql -U postgres
```

Then run these SQL commands:

```sql
-- Create database
CREATE DATABASE university_chat;

CREATE USER postgres WITH PASSWORD 'password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE university_chat TO postgres;

-- Connect to the database
\c university_chat

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO postgres;

-- Exit psql
\q
```

### 3. Setup Python Environment

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment

Create a `.env` file in the `backend` directory:

```bash
# Database configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/university_chat

# Optional: API keys for LLM extraction
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

## Running the Backend

### 1. Start the Server

```bash
# Make sure you're in the backend directory with virtual environment activated
cd backend
source .venv/bin/activate

# Start the FastAPI server
uvicorn app.main:app --reload --port 8000
```

The server will be available at:
- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

### 2. Verify Installation

```bash
# Test the health endpoint
curl http://localhost:8000/health

# Check database connection
curl http://localhost:8000/api/v1/search/messages?limit=1
```

## Usage

### 1. Ingest WhatsApp Chat Export

**Using REST API:**
```bash
# Upload a _chat.txt file
curl -X POST "http://localhost:8000/api/v1/ingest/chat-export" \
  -F "file=@/path/to/your/_chat.txt" \
  -F "since=2024-01-01T00:00:00Z"
```

**Using CLI:**
```bash
# From backend directory
python -m app.cli /path/to/your/_chat.txt --since 2024-01-01T00:00:00
```

### 2. Search Messages

```bash
# Full-text search
curl "http://localhost:8000/api/v1/search/messages?q=microwave&limit=10"

# Search with filters
curl "http://localhost:8000/api/v1/search/messages?q=apartment&after=2024-06-01T00:00:00Z&limit=20"

# Get top ranked results with snippets
curl "http://localhost:8000/api/v1/search/top?q=moveout&limit=5"

# Search canonical messages (deduplicated)
curl "http://localhost:8000/api/v1/search/canonical/top?q=furniture&limit=5"
```

### 3. Extract Items and Apartments

```bash
# Run entity extraction (regex-based, no LLM required)
curl -X POST "http://localhost:8000/api/v1/process/run?use_llm=false&batch=200"

# Backfill canonical messages table (if needed)
curl -X POST "http://localhost:8000/api/v1/process/backfill-canonical?limit=5000"
```

### 4. Get Structured Data

```bash
# Get recent items with seller info
curl "http://localhost:8000/api/v1/bot/most-recent/items?limit=10"

# Search items by seller name
curl "http://localhost:8000/api/v1/bot/most-recent/items?q=John&limit=5"

# Get recent apartments
curl "http://localhost:8000/api/v1/bot/most-recent/apartments?limit=10"

# Export all items as JSON
curl "http://localhost:8000/api/v1/export/items/json?limit=100"
```

## Database Schema

### Key Tables

- **`messages`**: Raw WhatsApp messages with deduplication fields
- **`canonical_messages`**: Global deduplicated messages across all groups
- **`users`**: Message senders with contact information
- **`groups`**: WhatsApp groups
- **`items_for_sale`**: Extracted items for sale
- **`apartments`**: Extracted apartment listings

### Important Fields

- **`content_hash`**: Normalized hash for content-based deduplication
- **`occurrence_count`**: How many times a message appears in a single group
- **`occurrence_total`**: How many times a message appears across all groups
- **`content_tsv`**: Full-text search vector for fast searching
- **`groups_seen`**: Array of groups where a canonical message appeared

## PostgreSQL Commands

### Useful Database Queries

```sql
-- Connect to database
psql postgresql://postgres:password@localhost:5432/university_chat

-- Check message counts
SELECT COUNT(*) as total_messages, COUNT(DISTINCT content_hash) as unique_content FROM messages;

-- Check canonical messages
SELECT COUNT(*) as canonical_count FROM canonical_messages;

-- Find most active groups
SELECT g.group_name, COUNT(*) as message_count 
FROM messages m 
JOIN groups g ON m.group_id = g.id 
GROUP BY g.group_name 
ORDER BY message_count DESC 
LIMIT 10;

-- Find duplicate messages
SELECT content_hash, COUNT(*) as occurrences 
FROM messages 
GROUP BY content_hash 
HAVING COUNT(*) > 1 
ORDER BY occurrences DESC 
LIMIT 10;
```

### Reset Database

```bash
# Drop and recreate database
psql postgres -c "DROP DATABASE IF EXISTS university_chat;"
psql postgres -c "CREATE DATABASE university_chat;"
psql postgresql://postgres:password@localhost:5432/university_chat -c "GRANT ALL PRIVILEGES ON DATABASE university_chat TO postgres;"
```

## Troubleshooting

### Common Issues

1. **PostgreSQL connection error**:
   - Check if PostgreSQL is running: `brew services list` (macOS) or `sudo systemctl status postgresql` (Linux)
   - Verify database exists: `psql -l`
   - Check credentials in `.env` file

2. **Permission denied**:
   - Ensure user has proper privileges: `GRANT ALL PRIVILEGES ON DATABASE university_chat TO your postgres;`

3. **Import errors**:
   - Check file format is valid WhatsApp export
   - Verify file encoding is UTF-8
   - Check file permissions

4. **Search not working**:
   - Ensure `content_tsv` column exists: `\d messages` in psql
   - Recreate indexes if needed: restart the server

### Logs

```bash
# View server logs
tail -f backend/logs/app.log

# Check database logs (macOS)
tail -f /usr/local/var/log/postgres.log
```

## API Documentation

Visit http://localhost:8000/docs for interactive API documentation with examples and testing interface.

## Development

### Project Structure

```
backend/
├── app/
│   ├── api/           # REST endpoints
│   ├── core/          # Configuration
│   ├── db/            # Database setup
│   ├── models/        # SQLAlchemy models
│   ├── schemas/       # Pydantic schemas
│   └── services/      # Business logic
├── requirements.txt   # Python dependencies
└── .env              # Environment variables
```

### Adding New Features

1. Create new models in `app/models/database.py`
2. Add schemas in `app/schemas/`
3. Create API endpoints in `app/api/`
4. Add business logic in `app/services/`
5. Update this README with new endpoints

## License

This project is for educational and personal use only.
