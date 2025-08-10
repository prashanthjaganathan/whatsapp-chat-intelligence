const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

async function listMyGroups() {
    console.log('🎓 WhatsApp Group ID Finder');
    console.log('==========================');
    console.log('📱 Initializing WhatsApp Web...');

    const client = new Client({
        authStrategy: new LocalAuth({
            clientId: 'group-id-finder'
        }),
        puppeteer: {
            headless: false,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        }
    });

    client.on('qr', (qr) => {
        console.log('📱 Scan this QR code with WhatsApp:');
        qrcode.generate(qr, { small: true });
    });

    client.on('ready', async () => {
        console.log('✅ WhatsApp Web connected!');
        console.log('📊 Fetching your groups...\n');

        try {
            const chats = await client.getChats();
            const groups = chats.filter(chat => chat.isGroup);

            if (groups.length === 0) {
                console.log('❌ No groups found. Make sure you are a member of the groups you want to scrape.');
            } else {
                console.log(`Found ${groups.length} groups:\n`);
                groups.forEach((group, index) => {
                    console.log(`${index + 1}. "${group.name}"`);
                    console.log(`   ID: ${group.id._serialized}`);
                    console.log(`   Members: ${group.participants.length}`);
                    console.log('');
                });
            }
        } catch (error) {
            console.error('❌ Error fetching groups:', error);
        }

        console.log('\n🛑 Closing WhatsApp Web...');
        await client.destroy();
        process.exit();
    });

    client.initialize();
}

// Run the script
listMyGroups();
