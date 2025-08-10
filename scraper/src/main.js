#!/usr/bin/env node
const { UniversityGroupScraper } = require('./scrapers/group-scraper');
const { getAllActiveGroups } = require('./config/groups');
const path = require('path');

async function main() {
    const args = process.argv.slice(2);
    const command = args[0];
    
    console.log('🎓 University Group Chat Scraper');
    console.log('='.repeat(50));
    
    switch (command) {
        case 'scrape':
            await handleScrapeCommand(args.slice(1));
            break;
        case 'list-groups':
            listAvailableGroups();
            break;
        case 'help':
        default:
            showHelp();
            break;
    }
}

async function handleScrapeCommand(args) {
    const groupName = args[0];
    const messageLimit = parseInt(args[1]) || 5000;
    const includeMedia = args.includes('--include-media');
    
    if (!groupName) {
        console.error('❌ Error: Group name is required');
        console.log('Usage: npm run scrape <GROUP_NAME> [MESSAGE_LIMIT] [--include-media]');
        console.log('Example: npm run scrape MIT_AI_HACKS 1000');
        return;
    }
    
    const scraper = new UniversityGroupScraper({
        outputDir: path.join(__dirname, '../outputs'),
        sessionName: `scraper-${groupName.toLowerCase()}`
    });
    
    try {
        await scraper.initialize();
        
        // Wait a moment for full initialization
        await new Promise(resolve => setTimeout(resolve, 5000));
        
        const groupData = await scraper.scrapeGroupByName(groupName, {
            messageLimit,
            includeMedia
        });
        
        console.log('\n✅ Scraping completed successfully!');
        console.log(`📊 Statistics:`);
        console.log(`   Messages: ${groupData.messages.length}`);
        console.log(`   Members: ${groupData.members.length}`);
        console.log(`   Time Range: ${groupData.statistics.timeRange?.earliest} to ${groupData.statistics.timeRange?.latest}`);
        
    } catch (error) {
        console.error('❌ Scraping failed:', error.message);
    } finally {
        await scraper.shutdown();
        process.exit(0);
    }
}

function listAvailableGroups() {
    console.log('📋 Available Groups:');
    console.log('-'.repeat(30));
    
    const groups = getAllActiveGroups();
    groups.forEach(group => {
        console.log(`• ${group.name}`);
        console.log(`  University: ${group.university}`);
        console.log(`  Categories: ${group.categories.join(', ')}`);
        console.log(`  Command: npm run scrape ${Object.keys(require('./config/groups').universityGroups).find(key => require('./config/groups').universityGroups[key] === group)}`);
        console.log('');
    });
}

function showHelp() {
    console.log('Available commands:');
    console.log('  scrape <GROUP_NAME> [LIMIT] [--include-media]  Scrape a specific group');
    console.log('  list-groups                                    List all available groups');
    console.log('  help                                           Show this help message');
    console.log('');
    console.log('Examples:');
    console.log('  npm run scrape MIT_AI_HACKS 1000');
    console.log('  npm run scrape HARVARD_HOUSING 500 --include-media');
    console.log('  npm run list-groups');
}

// Handle graceful shutdown
process.on('SIGINT', async () => {
    console.log('\n🛑 Received shutdown signal...');
    process.exit(0);
});

process.on('SIGTERM', async () => {
    console.log('\n🛑 Received termination signal...');
    process.exit(0);
});

// Run main function
if (require.main === module) {
    main().catch(error => {
        console.error('❌ Fatal error:', error);
        process.exit(1);
    });
}