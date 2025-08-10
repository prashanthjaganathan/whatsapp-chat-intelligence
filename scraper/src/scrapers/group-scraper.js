const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const fs = require('fs-extra');
const path = require('path');
const { getGroupByName, getAllActiveGroups } = require('../config/groups');

class UniversityGroupScraper {
    constructor(options = {}) {
        this.outputDir = options.outputDir || path.join(__dirname, '../../outputs');
        this.sessionName = options.sessionName || 'university-scraper';
        this.safetyDelay = options.safetyDelay || 1000;
        
        this.client = new Client({
            authStrategy: new LocalAuth({
                clientId: this.sessionName
            }),
            puppeteer: {
                headless: false,
                args: [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run'
                ]
            }
        });

        this.setupEventHandlers();
        this.processedMessages = new Set();
    }

    setupEventHandlers() {
        this.client.on('qr', (qr) => {
            console.log('📱 Scan this QR code with WhatsApp:');
            qrcode.generate(qr, { small: true });
        });

        this.client.on('ready', async () => {
            console.log('✅ WhatsApp client is ready!');
            await new Promise(resolve => setTimeout(resolve, 2000));
            if (this.pendingGroupScrape) {
                try {
                    this.pendingResult = await this.scrapeGroup(this.pendingGroupScrape);
                } catch (error) {
                    this.pendingError = error;
                }
            }
        });

        this.client.on('authenticated', () => {
            console.log('🔐 Authentication successful');
        });

        this.client.on('auth_failure', (msg) => {
            console.error('❌ Authentication failed:', msg);
        });

        this.client.on('disconnected', (reason) => {
            console.log('📱 WhatsApp disconnected:', reason);
        });
    }

    async initialize() {
        console.log('🚀 Initializing University Group Scraper...');
        await this.client.initialize();
    }

    async scrapeGroup(groupName, options = {}) {
        try {
            if (!this.client.info) {
                console.log('⏳ Client not ready yet, waiting for initialization...');
                this.pendingGroupScrape = groupName;
                
                // Wait for the client to be ready
                return new Promise((resolve, reject) => {
                    const checkReady = setInterval(() => {
                        if (this.pendingResult) {
                            clearInterval(checkReady);
                            resolve(this.pendingResult);
                        } else if (this.pendingError) {
                            clearInterval(checkReady);
                            reject(this.pendingError);
                        }
                    }, 1000);
                    
                    // Timeout after 30 seconds
                    setTimeout(() => {
                        clearInterval(checkReady);
                        reject(new Error('Timeout waiting for WhatsApp to be ready'));
                    }, 30000);
                });
            }
            
            const groupConfig = getGroupByName(groupName);
            if (!groupConfig) {
                throw new Error(`Group '${groupName}' not found in configuration`);
            }

            console.log(`📂 Scraping group: ${groupConfig.name}`);
            
            const chat = await this.client.getChatById(groupConfig.id);
            const groupData = await this.extractGroupData(chat, groupConfig);
            
            const filename = `${groupName.toLowerCase()}_data_${new Date().toISOString().split('T')[0]}.json`;
            const filepath = path.join(this.outputDir, filename);
            
            await fs.ensureDir(this.outputDir);
            await fs.writeJson(filepath, groupData, { spaces: 2 });
            
            console.log(`✅ Group data saved to: ${filepath}`);
            
            return groupData;
        } catch (error) {
            console.error(`❌ Error scraping group ${groupName}:`, error.message);
            throw error;
        }
    }

    // Alias method for backwards compatibility
    async scrapeGroupByName(groupName, options = {}) {
        return await this.scrapeGroup(groupName, options);
    }

    async extractGroupData(chat, groupConfig) {
        const groupInfo = {
            id: chat.id._serialized,
            name: chat.name,
            description: chat.description,
            participantCount: chat.participants.length,
            scrapedAt: new Date().toISOString()
        };

        console.log('👥 Processing group members...');
        const members = await this.processMembers(chat.participants);

        console.log('📨 Extracting messages...');
        const messages = await this.extractMessages(chat);

        return {
            groupInfo,
            members,
            messages,
            statistics: this.generateStatistics(messages)
        };
    }

    async processMembers(participants) {
        const members = [];
        
        for (const participant of participants) {
            try {
                const contact = await this.client.getContactById(participant.id._serialized);
                
                members.push({
                    id: participant.id._serialized,
                    phone: participant.id.user,
                    name: contact.name || contact.pushname || 'Unknown',
                    isAdmin: participant.isAdmin || false
                });

                await this.sleep(this.safetyDelay);
            } catch (error) {
                console.warn(`⚠️ Error processing member ${participant.id._serialized}`);
            }
        }
        
        return members;
    }

    async extractMessages(chat) {
        try {
            const messages = await chat.fetchMessages({ limit: 100 });
            return messages.map(msg => ({
                id: msg.id._serialized,
                timestamp: msg.timestamp,
                from: msg.from,
                author: msg.author || msg.from,
                body: msg.body || '',
                type: msg.type,
                hasMedia: msg.hasMedia || false
            }));
        } catch (error) {
            console.error('Error fetching messages:', error);
            return [];
        }
    }

    generateStatistics(messages) {
        return {
            totalMessages: messages.length,
            messageTypes: this.countMessageTypes(messages),
            timeRange: this.getMessageTimeRange(messages)
        };
    }

    countMessageTypes(messages) {
        const types = {};
        messages.forEach(msg => {
            types[msg.type] = (types[msg.type] || 0) + 1;
        });
        return types;
    }

    getMessageTimeRange(messages) {
        if (messages.length === 0) return null;
        
        const timestamps = messages.map(m => m.timestamp).sort();
        return {
            earliest: new Date(timestamps[0] * 1000).toISOString(),
            latest: new Date(timestamps[timestamps.length - 1] * 1000).toISOString()
        };
    }

    async sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async shutdown() {
        console.log('🛑 Shutting down scraper...');
        await this.client.destroy();
    }
}

module.exports = { UniversityGroupScraper };