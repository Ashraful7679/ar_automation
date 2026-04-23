// Format Profile to CustomerCode Base Mapping
const FORMAT_CUSTOMER_CODES = {
    'ARABIAN_SHIELD': 'ARABI',
    'AXA_PPP': 'AXAPP',
    'GEMS': 'GUNIO',
    'HEALIX': 'HEALI',
    'SOS': 'SOSIN',
    'MSH': 'MSHDU',
    'ALLIANZ': 'ALLIA',
    'ACIG': 'ACIGC',
    'AL_ETIHAD': 'ALETI',
    'BUPA': 'BUPAI',
    'CIGNA': 'CIGNA',
    'GLOBMED': 'ARIGI',
    'GIG_KSA': 'AXAKS',
    'GIG_GULF': 'AXAIN',
    'HEALTH360_OP': 'HEALT',
    'HEALTH360_EN_IP': 'HLENI',
    'HEALTH360_IP': 'HLGNI',
    'HEALTH360_EN_OP': 'HLTEN',
    'MEDNET': 'MEDNE',
    'NAS': 'NASIN',
    'NEURON': 'NEURO',
    'NEXTCARE': 'NEXTC',
    'NOW_HEALTH': 'NHISD',
    'QATAR_INS': 'QICIN',
    'SAICO': 'SAICO',
    'TAWUNIYA': 'TICIN',
    'WAPMED': 'WAPME'
};

// Function to get CustomerCode based on format and invoice prefix
function getCustomerCode(formatProfile, invNo) {
    const baseCode = FORMAT_CUSTOMER_CODES[formatProfile];
    if (!baseCode) return ''; // No mapping for this format

    // Get first character of invoice number
    const firstChar = (invNo || '').toString().trim().charAt(0).toUpperCase();

    // Determine suffix based on first character
    let suffix = '100'; // Default
    if (firstChar === 'B') suffix = '101';
    else if (firstChar === 'C') suffix = '102';

    return baseCode + suffix;
}
