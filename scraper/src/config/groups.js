// University group configurations
const universityGroups = {
    'TOP_GS': {
        id: '120363025923230723@g.us',
        name: 'Top Gs',
        university: 'NEU',
        categories: ['general'],
        active: true
    },
    // 'MIT_AI_HACKS': {
    //     id: '120363199877384683@g.us',
    //     name: 'MIT AI Hacks',
    //     university: 'MIT',
    //     categories: ['general', 'marketplace', 'housing'],
    //     active: true
    // },
    // 'HARVARD_HOUSING': {
    //     id: '1234567890123456@g.us', 
    //     name: 'Harvard Housing Exchange',
    //     university: 'Harvard',
    //     categories: ['housing', 'roommates'],
    //     active: true
    // },
    // 'STANFORD_MARKETPLACE': {
    //     id: '9876543210987654@g.us',
    //     name: 'Stanford Student Marketplace', 
    //     university: 'Stanford',
    //     categories: ['marketplace', 'items'],
    //     active: true
    // }
};

function getGroupByName(groupName) {
    return universityGroups[groupName.toUpperCase()] || null;
}

function getAllActiveGroups() {
    return Object.values(universityGroups).filter(group => group.active);
}

function getGroupsByUniversity(university) {
    return Object.values(universityGroups).filter(group => 
        group.university.toLowerCase() === university.toLowerCase() && group.active
    );
}

module.exports = {
    universityGroups,
    getGroupByName,
    getAllActiveGroups,
    getGroupsByUniversity
};