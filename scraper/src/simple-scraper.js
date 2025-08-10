const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const fs = require('fs-extra');
const path = require('path');

class GroupScraper {
    constructor(groupId, outputDir = 'outputs') {
        this.groupId = groupId;
        this.outputDir = outputDir;
        
        this.client = new Client({
            authStrategy: new LocalAuth({
                clientId: 'whatsapp-scraper'
            }),
            puppeteer: {
                headless: false,
                args: ['--no-sandbox', '--disable-setuid-sandbox']
            }
        });

        this.setupEvents();
    }

    setupEvents() {
        this.client.on('qr', (qr) => {
            console.log('📱 Scan this QR code with WhatsApp:');
            qrcode.generate(qr, { small: true });
        });

        this.client.on('ready', () => {
            console.log('✅ WhatsApp Web is ready!');
            this.startScraping();
        });

        this.client.on('error', (error) => {
            console.error('❌ Error:', error);
        });
    }

    async startScraping() {
        try {
            console.log('🔍 Getting chat...');
            const chat = await this.client.getChatById(this.groupId);
            
            console.log('📥 Fetching messages...');
            const messages = await chat.fetchMessages({ limit: 100 });
            
            console.log(`✨ Found ${messages.length} messages`);
            
            const processedMessages = messages.map(msg => ({
                id: msg.id.id,
                timestamp: msg.timestamp,
                from: msg.from,
                author: msg.author,
                body: msg.body,
                hasMedia: msg.hasMedia,
                type: msg.type
            }));

            const outputPath = path.join(this.outputDir, `${chat.name.replace(/[^a-z0-9]/gi, '_')}_messages.json`);
            await fs.outputJson(outputPath, {
                groupName: chat.name,
                groupId: this.groupId,
                memberCount: chat.participants.length,
                messages: processedMessages
            }, { spaces: 2 });

            console.log(`✅ Messages saved to ${outputPath}`);
        } catch (error) {
            console.error('❌ Error while scraping:', error);
        } finally {
            await this.client.destroy();
            console.log('👋 Done! You can close this window.');
        }
    }

    start() {
        console.log('🚀 Starting WhatsApp Web...');
        this.client.initialize();
    }
}

// Start the scraper
const scraper = new GroupScraper('120363025923230723@g.us');
scraper.start();
