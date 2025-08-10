# WhatsApp University Group Chat Scraper

A powerful Node.js application that scrapes WhatsApp group chats using Puppeteer and WhatsApp Web API. This tool helps you extract messages, member information, and statistics from university WhatsApp groups for analysis and data management.

## 🏗️ Architecture Overview

The scraper uses:
- **Puppeteer**: Controls a headless Chrome browser to interact with WhatsApp Web
- **whatsapp-web.js**: A WhatsApp Web API wrapper that handles the WhatsApp protocol
- **QR Code Authentication**: Scans QR code with your phone to authenticate
- **Local Session Storage**: Saves authentication to avoid re-scanning QR codes

## 📋 Prerequisites

- Node.js (v16 or higher)
- Chrome/Chromium browser installed
- WhatsApp account with access to target groups
- Stable internet connection

## 🚀 Installation & Setup

### 1. Navigate to the scraper directory
```bash
cd scraper
```

### 2. Install dependencies
```bash
npm install
```

### 3. Verify installation
```bash
node src/main.js help
```

## 📱 How to Get WhatsApp Group IDs

Before scraping, you need to find the IDs of the WhatsApp groups you want to scrape.

### Step 1: Run the Group ID Finder
```bash
node src/utils/list-groups.js
```

### Step 2: Scan QR Code
1. The tool will display a QR code in your terminal
2. Open WhatsApp on your phone
3. Go to **Settings** > **WhatsApp Web/Desktop**
4. Tap **"Scan QR Code"**
5. Scan the QR code displayed in your terminal

### Step 3: Get Group Information
The tool will output all your groups like this:
```
Found 308 groups:

1. "University Housing"
   ID: 120363309080465383@g.us
   Members: 156

2. "Study Group - CS101"
   ID: 120363318360134573@g.us
   Members: 25
```

**Save the Group ID** (the long string ending in `@g.us`) for groups you want to scrape.

## ⚙️ Configure Groups for Scraping

### Step 1: Edit the configuration file
```bash
nano src/config/groups.js
```

### Step 2: Add your groups
Replace the example groups with your actual groups:

```javascript
const universityGroups = {
    'UNIVERSITY_HOUSING': {
        id: '120363309080465383@g.us',        // Use the actual ID from list-groups
        name: 'University Housing',
        university: 'Your University',
        categories: ['housing'],
        active: true
    },
    'STUDY_GROUP_CS': {
        id: '120363318360134573@g.us',        // Use the actual ID from list-groups
        name: 'Study Group - CS101',
        university: 'Your University', 
        categories: ['academic'],
        active: true
    }
};
```

**Configuration Options:**
- `id`: The WhatsApp group ID (get from list-groups command)
- `name`: Human-readable name for the group
- `university`: University name for organization
- `categories`: Tags like 'housing', 'academic', 'marketplace', 'general'
- `active`: Set to `true` to enable scraping, `false` to disable

## 🔧 Scraping Commands

### Basic Scraping Command
```bash
node src/main.js scrape <GROUP_NAME>
```

### Available Commands

#### 1. List Configured Groups
```bash
node src/main.js list-groups
```
Shows all groups configured in your `groups.js` file.

#### 2. Scrape a Group (Default: 100 messages)
```bash
node src/main.js scrape UNIVERSITY_HOUSING
```

#### 3. Scrape with Custom Message Limit
```bash
node src/main.js scrape UNIVERSITY_HOUSING 500
```
Scrapes up to 500 messages from the group.

#### 4. Scrape with Media Download
```bash
node src/main.js scrape UNIVERSITY_HOUSING 100 --include-media
```
Downloads and processes media files (images, videos, documents).

#### 5. Get Help
```bash
node src/main.js help
```

### Message Limit Options
- **Default**: 100 messages
- **Minimum**: 1 message
- **Maximum**: 5000 messages (WhatsApp Web limitation)
- **Recommended**: 100-1000 for best performance

## 📊 How the Scraping Process Works

### Step 1: Initialization
```bash
node src/main.js scrape UNIVERSITY_HOUSING 200
```

1. **Loads Configuration**: Reads your group settings from `groups.js`
2. **Starts Puppeteer**: Launches a Chrome browser instance
3. **Opens WhatsApp Web**: Navigates to web.whatsapp.com

### Step 2: Authentication
1. **QR Code Display**: Shows QR code in terminal
2. **Phone Scanning**: You scan with WhatsApp on your phone
3. **Session Storage**: Saves login session for future use
4. **Ready State**: Waits for WhatsApp Web to fully load

### Step 3: Data Extraction
1. **Group Access**: Connects to the specified group using group ID
2. **Member Processing**: 
   - Gets participant list
   - Fetches contact details for each member
   - Extracts names, phone numbers, admin status
3. **Message Extraction**:
   - Fetches messages in batches (respects rate limits)
   - Processes message content, timestamps, senders
   - Handles different message types (text, media, links)
   - Extracts reactions and mentions

### Step 4: Data Processing & Storage
1. **Data Structuring**: Organizes data into JSON format
2. **File Generation**: Creates timestamped output file
3. **Statistics**: Generates message type counts and time ranges
4. **Cleanup**: Closes browser and terminates session

## 📁 Output Files

Scraped data is saved to: `outputs/<group_name>_data_<date>.json`

**Example**: `outputs/university_housing_data_2025-08-07.json`

### Output File Structure
```json
{
  "groupInfo": {
    "id": "120363309080465383@g.us",
    "name": "University Housing",
    "description": "Housing discussion group",
    "participantCount": 156,
    "scrapedAt": "2025-08-07T10:30:00.000Z"
  },
  "members": [
    {
      "id": "1234567890@c.us",
      "phone": "1234567890",
      "name": "John Doe",
      "isAdmin": false
    }
  ],
  "messages": [
    {
      "id": "message_id_123",
      "timestamp": 1691398200,
      "from": "1234567890@c.us",
      "author": "1234567890@c.us",
      "body": "Looking for a roommate for fall semester",
      "type": "chat",
      "hasMedia": false
    }
  ],
  "statistics": {
    "totalMessages": 200,
    "totalMembers": 156,
    "messageTypes": {
      "chat": 180,
      "image": 15,
      "document": 5
    },
    "timeRange": {
      "earliest": "2025-07-01T00:00:00.000Z",
      "latest": "2025-08-07T10:30:00.000Z"
    }
  }
}
```

## 🛠️ Advanced Usage

### Multiple Group Scraping
Create a script to scrape multiple groups:

```bash
# Scrape all configured groups
node src/main.js scrape UNIVERSITY_HOUSING 200
node src/main.js scrape STUDY_GROUP_CS 500
node src/main.js scrape MARKETPLACE 300
```

### Automated Scraping
Set up a cron job for regular scraping:

```bash
# Add to crontab for daily scraping at 2 AM
0 2 * * * cd /path/to/scraper && node src/main.js scrape UNIVERSITY_HOUSING 100
```

### Rate Limiting & Safety
- **Built-in delays**: 1 second between member processing
- **Batch processing**: Messages fetched in manageable chunks
- **Error handling**: Continues processing if individual items fail
- **Session reuse**: Avoids repeated QR code scanning

## 🔍 Troubleshooting

### Common Issues

#### 1. "Group not found in configuration"
```
❌ Error: Group 'MY_GROUP' not found in configuration
```
**Solution**: Check that the group name matches exactly what's in `groups.js`

#### 2. "Cannot read properties of undefined"
```
❌ Error: Cannot read properties of undefined (reading 'getChat')
```
**Solution**: Wait longer for WhatsApp Web to load, or restart the scraper

#### 3. "Authentication failed"
```
❌ Authentication failed: Session expired
```
**Solution**: Delete `.wwebjs_auth` folder and re-scan QR code

#### 4. Rate limiting errors
```
⚠️ Error processing member: Rate limit exceeded
```
**Solution**: Reduce message limit or increase delay in scraper settings

### Debug Mode
Run with verbose logging:
```bash
DEBUG=* node src/main.js scrape UNIVERSITY_HOUSING
```

### Clear Authentication
If having login issues:
```bash
rm -rf .wwebjs_auth/
node src/main.js scrape UNIVERSITY_HOUSING
```

## 📝 Example Workflow

Here's a complete example of setting up and running the scraper:

### 1. Find Group IDs
```bash
node src/utils/list-groups.js
# Scan QR code when prompted
# Note down the group IDs you want
```

### 2. Configure Groups
Edit `src/config/groups.js`:
```javascript
const universityGroups = {
    'NEU_HOUSING': {
        id: '120363309080465383@g.us',
        name: 'NEU Housing Community',
        university: 'Northeastern University',
        categories: ['housing'],
        active: true
    }
};
```

### 3. Run Scraper
```bash
node src/main.js scrape NEU_HOUSING 200
```

### 4. Check Output
```bash
ls outputs/
cat outputs/neu_housing_data_2025-08-07.json
```

## 🚀 Integration with Backend

The scraped JSON data can be processed by your backend API:

```bash
# Example: Send data to your FastAPI backend
curl -X POST "http://localhost:8000/api/v1/process-whatsapp-data" \
  -H "Content-Type: application/json" \
  -d @outputs/neu_housing_data_2025-08-07.json
```

## ⚠️ Important Notes

1. **Respect Privacy**: Only scrape groups you're a member of
2. **Rate Limits**: WhatsApp has rate limits; don't scrape too aggressively
3. **Storage**: Large groups can generate big files (10MB+ for 1000+ messages)
4. **Legal**: Ensure compliance with data protection laws in your jurisdiction
5. **WhatsApp Terms**: Use responsibly according to WhatsApp's Terms of Service

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Verify your Node.js version: `node --version`
3. Ensure all dependencies are installed: `npm list`
4. Check if Chrome/Chromium is properly installed
5. Try clearing authentication cache: `rm -rf .wwebjs_auth/`

## 📄 File Structure

```
scraper/
├── src/
│   ├── main.js                 # Main CLI interface
│   ├── config/
│   │   └── groups.js          # Group configurations
│   ├── scrapers/
│   │   └── group-scraper.js   # Main scraper class
│   └── utils/
│       └── list-groups.js     # Group ID finder utility
├── outputs/                   # Scraped data files
├── package.json              # Dependencies
└── README.md                 # This file
```

---

**Happy Scraping! 🎉**

Remember to use this tool responsibly and in compliance with WhatsApp's terms of service and applicable data protection laws.
