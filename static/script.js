let currentHeaders = [];
let originalFormattedData = null; // Store for revert
let rawDataStore = null; // Store raw data for mapping
let pendingUpdates = {}; // Track changes: "rowId-colIdx": {row_id, col_index, value}

// Fixed Schema per user request
const FIXED_SCHEMA = ["Sl. No", "Inv No", "Date", "Patient ID", "Patient Name",
    "Invoice Balance", "Amt To Adjust", "CustomerCode", "Remark 1", "Remark 2", "Remark 3"];

// Clean invoice number - remove /, -1, -2, etc suffixes that are not actual invoice numbers
function cleanInvoiceNumber(invNo) {
    if (!invNo) return "";
    invNo = invNo.toString().trim();
    // Remove patterns like /123, -1, -2, etc at end if they look like continuation markers
    // Keep only alphanumeric and underscores
    // Remove trailing / or /number or -number that looks like a continuation
    invNo = invNo.replace(/\/+$/, '');      // Remove trailing / or /123/ etc
    invNo = invNo.replace(/\/[0-9]+$/, '');  // Remove /123 at end
    invNo = invNo.replace(/-[0-9]+$/, '');   // Remove -1, -2, etc at end
    return invNo;
}

// Convert Excel serial date to YYYY-MM-DD
function excelDateToJSDate(serial) {
    if (!serial || isNaN(serial)) return serial;
    // Handle strings that look like numbers
    serial = parseFloat(serial);
    if (isNaN(serial) || serial < 10000) return serial; // Likely not a serial date if too small

    // Excel 1900 date system
    const date = new Date(Math.round((serial - 25569) * 86400 * 1000));
    
    // Format as YYYY-MM-DD
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
}


// Track totals for cross-validation
let tableTotals = {
    'raw-preview-table': { balance: 0, adjust: 0 },
    'formatted-preview-table': { balance: 0, adjust: 0 },
    'result-preview-table': { balance: 0, adjust: 0 }
};

// Global Customer Codes Map
const FORMAT_CUSTOMER_CODES = {
    'ARABIAN_SHIELD': 'ARABI', 'AXA_PPP': 'AXAPP', 'GEMS': 'GUNIO',
    'HEALIX': 'HEALI', 'SOS': 'SOSIN', 'MSH': 'MSHDU',
    'ALLIANZ': 'ALLIA', 'ACIG': 'ACIGC', 'AL_ETIHAD': 'ALETI',
    'BUPA': 'BUPAI', 'CIGNA': 'CIGNA', 'GLOBMED': 'ARIGI',
    'GIG_KSA': 'AXAKS', 'GIG_GULF': 'AXAIN', 'HEALTH360_OP': 'HEALT',
    'HEALTH360_EN_IP': 'HLENI', 'HEALTH360_IP': 'HLGNI', 'HEALTH360_EN_OP': 'HLTEN',
    'MEDNET': 'MEDNE', 'NAS': 'NASIN', 'NEURON': 'NEURO',
    'NEXTCARE': 'NEXTC', 'NOW_HEALTH': 'NHISD', 'QATAR_INS': 'QICIN',
    'SAICO': 'SAICO', 'TAWUNIYA': 'TICIN', 'WAPMED': 'WAPME'
};

// Auto-Set Rules on Profile Change
document.addEventListener('DOMContentLoaded', () => {
    const fs = document.getElementById('format-select');
    if (fs) {
        fs.addEventListener('change', (e) => {
            const profile = e.target.value;
            const baseCode = FORMAT_CUSTOMER_CODES[profile];

            // Auto-Set Logic & Rules UI
            const container = document.getElementById('rules-container');
            if (container && baseCode) {
                container.innerHTML = ''; // Clear existing

                const defaults = [
                    { p: 'A', c: baseCode + '100' },
                    { p: 'B', c: baseCode + '101' },
                    { p: 'C', c: baseCode + '102' }
                ];

                defaults.forEach(rule => {
                    addRuleRowWithValues(rule.p, '', rule.c);
                });

                updateStatus(`Rules auto-set for ${profile}`);
            } else if (container) {
                container.innerHTML = ''; // Clear if default/unknown
            }



            if (uploadedFile) {
                handleFileSelect({ target: { files: [uploadedFile] } });
            }
        });
    }

    // Initialize Drag and Drop
    setupDragAndDrop();

    // Load Templates
    fetchTemplates();
});

function setupDragAndDrop() {
    const dropZone = document.getElementById('drop-zone');
    if (!dropZone) return;

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight drop zone when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    // Handle dropped files
    dropZone.addEventListener('drop', handleDrop, false);
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function highlight(e) {
    document.getElementById('drop-zone').classList.add('dragover');
}

function unhighlight(e) {
    document.getElementById('drop-zone').classList.remove('dragover');
}

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;

    if (files.length > 0) {
        handleFileSelect({ target: { files: files } });
    }
}



function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    // Show selected
    document.getElementById('tab-' + tabName).classList.add('active');

    // Update Nav
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.classList.remove('active');
    });
    // Simple substring match for button active state if needed, or just iterate
    // For now simple clicks work.
}


// State variables
let uploadedFile = null;
let currentSheets = [];

document.getElementById('file-input').addEventListener('change', handleFileSelect);
document.getElementById('sheet-select').addEventListener('change', loadSelectedSheet);

// Event Listener moved to consolidated block for format-select (Line 60+)


function resetAppState() {
    rawDataStore = null;
    mappedData = null;
    resultData = null;
    originalFormattedData = null;
    mappingState = {};
    pendingUpdates = {};

    // Clear Tables
    ['raw-preview-table', 'formatted-preview-table', 'result-preview-table'].forEach(id => {
        const t = document.getElementById(id);
        if (t) t.innerHTML = '';
    });

    // Clear Mapping Sidebar
    const side = document.getElementById('mapping-sidebar');
    if (side) side.innerHTML = '<p style="color: #6B7280; font-size: 0.8rem;">Load a file to see mapping options.</p>';

    // Collapse All
    ['raw-section', 'formatted-section', 'result-section'].forEach(id => toggleSection(id, false));

    // Reset Export UI
    const container = document.getElementById('download-list-container');
    if (container) {
        container.innerHTML = `
            <button onclick="executeDownload()" id="btn-download" disabled
                style="width: 100%; padding: 10px; background:#6B7280; color:white; border:none; border-radius:4px; font-weight:bold; cursor:not-allowed;">
                Download Result
            </button>
        `;
    }
    preparedFilename = null;
    preparedFiles = []; // For multi-file

    // Reset Split & Group Selections
    // Note: split-by-col dropdown has been removed, now hardcoded to CustomerCode (index 7)

    const consolidate = document.getElementById('rule-consolidate');
    if (consolidate) consolidate.checked = true; // Default to CHECKED per user request
}

// ... (Lines 98-595 omitted for brevity, ensure context matches if editing, but this looks like a large gap. 
// Safer to edit resetAppState specifically).
// Skipping to applyPipeline...

function applyPipeline(stage = 'full', shouldSave = false) {
    if (!mappedData) {
        updateStatus("Please confirm mapping first.");
        return;
    }

    updateStatus("Running Pipeline...");

    // 1. Start with Mapped Data
    let pipelineRows = JSON.parse(JSON.stringify(mappedData.rows)); // Deep Copy

    // Clean invoice numbers - remove /suffix, -1, -2, etc
    const invIndex = 1;
    pipelineRows.forEach(row => {
        if (row[invIndex]) {
            row[invIndex] = cleanInvoiceNumber(row[invIndex]);
        }
    });

    // 2. Consolidate? (Only if stage is 'full' OR standard check if we assume logic separation means explicit action)
    // Actually, user wants separate functionality. 
    // If stage === 'rules', skip consolidation? Yes.

    if (stage === 'full' && document.getElementById('rule-consolidate').checked) {
        // Consolidate by Inv No (Index 1). 
        // Remarks from multiple rows and columns are joined by comma.
        const selectedIndices = [1];
        pipelineRows = consolidateRows(pipelineRows, selectedIndices);
    } else {
        // If not consolidating rows, still concatenate multiple Remark columns per row
        pipelineRows.forEach(row => {
            let remarks = [];
            if (row[8]) remarks.push(row[8]);  // Remark 1
            if (row[9]) remarks.push(row[9]);  // Remark 2
            if (row[10]) remarks.push(row[10]); // Remark 3
            
            if (remarks.length > 0) {
                row[8] = [...new Set(remarks)].join(', ');
                row[9] = ""; 
                row[10] = "";
            }
        });
    }

    // 3. Apply Prefix Rules (Always apply if rules exist)
    const rules = [];
    document.querySelectorAll('#rules-container > div').forEach(div => {
        const prefix = div.querySelector('.rule-prefix').value.trim();
        const suffix = div.querySelector('.rule-suffix').value.trim();
        const code = div.querySelector('.rule-code').value.trim();
        if (prefix || suffix) {
            rules.push({ prefix, suffix, code });
        }
    });

    if (rules.length > 0) {
        const invIndex = 1;
        const custIndex = 7;

        pipelineRows.forEach(row => {
            const invNo = (row[invIndex] || "").toString().toLowerCase();
            let rowMatch = false;
            let newValue = "";

            for (const rule of rules) {
                const p = rule.prefix.toLowerCase();
                const s = rule.suffix.toLowerCase();
                let match = true;
                if (p && !invNo.startsWith(p)) match = false;
                if (match && s && !invNo.endsWith(s)) match = false;

                if (match && (p || s)) {
                    newValue = rule.code;
                    rowMatch = true;
                }
            }

            if (rowMatch) {
                row[custIndex] = newValue;
            }
        });
    }

    // 3.5 Auto-populate CustomerCode based on format profile and invoice prefix
    const formatProfile = document.getElementById('format-select').value;
    const FORMAT_CUSTOMER_CODES = {
        'ARABIAN_SHIELD': 'ARABI', 'AXA_PPP': 'AXAPP', 'GEMS': 'GUNIO',
        'HEALIX': 'HEALI', 'SOS': 'SOSIN', 'MSH': 'MSHDU',
        'ALLIANZ': 'ALLIA', 'ACIG': 'ACIGC', 'AL_ETIHAD': 'ALETI',
        'BUPA': 'BUPAI', 'CIGNA': 'CIGNA', 'GLOBMED': 'ARIGI',
        'GIG_KSA': 'AXAKS', 'GIG_GULF': 'AXAIN', 'HEALTH360_OP': 'HEALT',
        'HEALTH360_EN_IP': 'HLENI', 'HEALTH360_IP': 'HLGNI', 'HEALTH360_EN_OP': 'HLTEN',
        'MEDNET': 'MEDNE', 'NAS': 'NASIN', 'NEURON': 'NEURO',
        'NEXTCARE': 'NEXTC', 'NOW_HEALTH': 'NHISD', 'QATAR_INS': 'QICIN',
        'SAICO': 'SAICO', 'TAWUNIYA': 'TICIN', 'WAPMED': 'WAPME'
    };

    const baseCode = FORMAT_CUSTOMER_CODES[formatProfile];
    if (baseCode) {
        const invIndex = 1; // Inv No column
        const custIndex = 7; // CustomerCode column

        pipelineRows.forEach(row => {
            const invNo = (row[invIndex] || '').toString().trim();
            const firstChar = invNo.charAt(0).toUpperCase();

            // Determine suffix: A→100, B→101, C→102, default→100
            let suffix = '100';
            if (firstChar === 'B') suffix = '101';
            else if (firstChar === 'C') suffix = '102';

            row[custIndex] = baseCode + suffix;
        });
    }

    // 3.6 Filter Empty Rows
    pipelineRows = pipelineRows.filter(r => r[1] && r[1].toString().trim() !== "");

    // Render to RESULT TABLE
    renderTable('result-preview-table', FIXED_SCHEMA, pipelineRows, false, []);

    // Auto-Open Split Section
    toggleSidebarSection('side-split-section');

    // 4. Split Logic (Only if stage is 'full')
    // HARDCODED to split by CustomerCode (index 7) per user request
    splitGroups = null; // Default null
    if (stage === 'full') {
        const splitColIndex = 7; // CustomerCode column (hardcoded)
        const groups = {};
        pipelineRows.forEach(row => {
            // Skip rows with no invoice number (column 1)
            if (!row[1] || !row[1].toString().trim()) return;
            
            const key = (row[splitColIndex] || "Uncategorized").toString().trim();
            if (!groups[key]) groups[key] = [];
            groups[key].push([...row]);
        });
        Object.values(groups).forEach((grp, gIdx) => {
            grp.forEach((r, i) => r[0] = i + 1);
        });
        splitGroups = groups;
    }

    // Validate Totals
    checkTotalMismatch('formatted-preview-table', 'result-preview-table', 'Apply Rules');

    if (shouldSave) {
        saveFullData(pipelineRows);
    } else {
        updateStatus("Rules Applied. Check Result Data below.");
        toggleSection('result-section', true);

        // Only expand export/actions if full stage
        if (stage === 'full') {
            toggleSidebarSection('side-export-section', true);
        }
        // If 'rules', stay in place (or maybe result section is enough)
    }
}

async function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;

    resetAppState();
    uploadedFile = file;

    // Reset UI visibility
    document.getElementById('sheet-selector-container').classList.add('hidden');
    document.getElementById('preview-container').classList.add('hidden');

    // Check if Excel
    const lowerName = file.name.toLowerCase();
    if (lowerName.endsWith('.xlsx') || lowerName.endsWith('.xls') || lowerName.endsWith('.xlsm')) {
        await checkSheets(file);
    } else {
        // Direct upload for CSV/PDF
        uploadFile(file, null);
    }
}

async function checkSheets(file) {
    const formData = new FormData();
    formData.append('file', file);

    updateStatus("Checking file sheets...");

    try {
        const res = await fetch('/api/get_sheets', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.sheets && data.sheets.length > 0) {
            const sel = document.getElementById('sheet-select');
            sel.innerHTML = ''; // Start clean
            data.sheets.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s;
                opt.text = s;
                sel.appendChild(opt);
            });
            document.getElementById('sheet-selector-container').classList.remove('hidden');

            // Auto-Select First Sheet
            const firstSheet = data.sheets[0];
            sel.value = firstSheet;
            uploadFile(file, firstSheet);
        } else {
            // No sheets found or returned, try load directly
            uploadFile(file, null);
        }
    } catch (e) {
        console.error(e);
        uploadFile(file, null); // Fallback
    }
}

function loadSelectedSheet() {
    const sheet = document.getElementById('sheet-select').value;
    if (sheet && uploadedFile) {
        uploadFile(uploadedFile, sheet);
    }
}


async function uploadFile(file, sheetName) {
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    const profile = document.getElementById('format-select').value;
    formData.append('profile', profile);

    if (sheetName) {
        formData.append('sheet', sheetName);
    }

    updateStatus("Uploading...");

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const text = await response.text();
        let data;
        try {
            data = JSON.parse(text);
        } catch (e) {
            console.error("Failed to parse JSON:", text);
            updateStatus("Error: Invalid Server Response");
            return;
        }

        if (response.ok) {
            // Fix: Backend returns raw_preview and formatted_preview, not top-level headers
            if (data.formatted_preview && data.formatted_preview.headers) {
                currentHeaders = data.formatted_preview.headers;
            } else if (data.raw_preview && data.raw_preview.headers) {
                currentHeaders = data.raw_preview.headers;
            } else {
                currentHeaders = [];
            }
            if (data.message) {
                // Show filename
                document.getElementById('file-name-text').innerText = file.name;
                document.getElementById('file-name-text').style.color = "#F9FAFB";

                // Render Raw Input
                if (data.raw_preview) {
                    rawDataStore = data.raw_preview;
                    renderTable('raw-preview-table', data.raw_preview.headers, data.raw_preview.rows);
                    currentHeaders = data.raw_preview.headers; // Used for dropdowns
                    populateFilterColumns(data.raw_preview.headers);
                }

                // Render Formatted Output (Ready for mapping in sidebar)
                let fmtData = data.formatted_preview;

                if (!fmtData || !fmtData.headers || fmtData.headers.length === 0 || profile === 'default') {
                    fmtData = {
                        headers: FIXED_SCHEMA,
                        rows: [] // Start empty until mapped
                    };
                }

                originalFormattedData = fmtData; // Store Original
                renderTable('formatted-preview-table', fmtData.headers, fmtData.rows, false);

                // Auto-Populate Mapping Sidebar
                renderMappingUI();

                // Auto-Expand Input Data & Mapping
                toggleSection('raw-section', true);
                toggleSidebarSection('side-mapping-section', true);
            }
        } else {
            console.error("Server Error:", text);
            updateStatus("Error: " + response.status + " " + response.statusText);
        }
    } catch (error) {
        console.error(error);
        updateStatus("Upload Failed: " + error.message);
    }
}

// Cleaning Functions
// Cleaning Functions
async function setRawHeader() {
    const checked = document.querySelectorAll('#raw-preview-table .row-checkbox:checked');
    if (checked.length !== 1) {
        alert("Please select exactly one row to set as header.");
        return;
    }
    const rowId = checked[0].value;

    updateStatus("Setting Header Row...");
    try {
        const res = await fetch('/api/set_raw_header', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ row_id: rowId })
        });
        const data = await res.json();
        if (data.success) {
            updateStatus("Header updated. Reloading View...");
            await reloadRawData();
        } else {
            alert("Error: " + data.error);
            updateStatus("Set Header Failed.");
        }
    } catch (e) { console.error(e); updateStatus("Header Set Error"); }
}

async function deleteRawRows() {
    const checked = document.querySelectorAll('#raw-preview-table .row-checkbox:checked');
    if (checked.length === 0) {
        alert("Please select rows to delete.");
        return;
    }
    const rowIds = Array.from(checked).map(c => c.value);

    updateStatus(`Deleting ${rowIds.length} rows...`);
    try {
        const res = await fetch('/api/delete_raw_rows', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ row_ids: rowIds })
        });
        const data = await res.json();
        if (data.success) {
            updateStatus("Rows deleted. Reloading View...");
            await reloadRawData();
        } else {
            alert("Error: " + data.error);
            updateStatus("Delete Failed.");
        }
    } catch (e) { console.error(e); updateStatus("Delete Error"); }
}

async function setAsLastRow() {
    const checked = document.querySelectorAll('#raw-preview-table .row-checkbox:checked');
    if (checked.length !== 1) {
        alert("Please select exactly one row to set as the last row.");
        return;
    }
    const rowId = parseInt(checked[0].value);
    
    if (!rawDataStore || !rawDataStore.rows) {
        alert("No data loaded.");
        return;
    }
    
    const lastRowId = rawDataStore.rows.length;
    if (rowId >= lastRowId) {
        alert("Selected row is already the last row or beyond.");
        return;
    }
    
    const rowsToDelete = [];
    for (let i = rowId + 1; i <= lastRowId; i++) {
        rowsToDelete.push(i.toString());
    }
    
    if (!confirm(`This will delete ${rowsToDelete.length} rows below the selected row. Continue?`)) {
        return;
    }
    
    updateStatus(`Deleting ${rowsToDelete.length} rows below selected...`);
    try {
        const res = await fetch('/api/delete_raw_rows', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ row_ids: rowsToDelete })
        });
        const data = await res.json();
        if (data.success) {
            updateStatus("Rows deleted. Reloading View...");
            await reloadRawData();
        } else {
            alert("Error: " + data.error);
            updateStatus("Delete Failed.");
        }
    } catch (e) { console.error(e); updateStatus("Delete Error"); }
}

async function reloadRawData() {
    try {
        const res = await fetch('/api/get_raw_preview');
        const data = await res.json();

        if (data.headers) {
            // Update Global Stores
            rawDataStore = data;
            currentHeaders = data.headers; // IMPORTANT: Updates Mapping Dropdowns

            // Re-render Raw Table
            renderTable('raw-preview-table', data.headers, data.rows);

            // Re-render Mapping UI to reflect new headers
            renderMappingUI();
            
            // Populate Filter Columns
            populateFilterColumns(data.headers);

            updateStatus("View Refreshed.");
        }
    } catch (e) {
        console.error(e);
        updateStatus("Failed to reload data.");
    }
}

function populateFilterColumns(headers) {
    const sel = document.getElementById('filter-column');
    const combineInv = document.getElementById('combine-inv-col');
    const combineRem1 = document.getElementById('combine-rem1-col');
    const combineRem2 = document.getElementById('combine-rem2-col');
    const combineRem3 = document.getElementById('combine-rem3-col');
    
    if (!sel) return;
    
    // Save current selections
    const currentSel = sel.value;
    const currentInv = combineInv ? combineInv.value : "";
    const currentRem1 = combineRem1 ? combineRem1.value : "";
    const currentRem2 = combineRem2 ? combineRem2.value : "";
    const currentRem3 = combineRem3 ? combineRem3.value : "";
    
    sel.innerHTML = '<option value="">Select Column...</option>';
    if (combineInv) combineInv.innerHTML = '<option value="">Invoice Column...</option>';
    if (combineRem1) combineRem1.innerHTML = '<option value="">Remark 1 Column...</option>';
    if (combineRem2) combineRem2.innerHTML = '<option value="">Remark 2 Column...</option>';
    if (combineRem3) combineRem3.innerHTML = '<option value="">Remark 3 Column...</option>';

    headers.forEach(h => {
        if (h === '_id') return;
        
        // Filter dropdown
        const opt = document.createElement('option');
        opt.value = h;
        opt.text = h;
        sel.appendChild(opt);

        // Combine Invoice dropdown
        if (combineInv) {
            const optInv = document.createElement('option');
            optInv.value = h;
            optInv.text = h;
            combineInv.appendChild(optInv);
        }

        // Combine Remark 1 dropdown
        if (combineRem1) {
            const optRem1 = document.createElement('option');
            optRem1.value = h;
            optRem1.text = h;
            combineRem1.appendChild(optRem1);
        }

        // Combine Remark 2 dropdown
        if (combineRem2) {
            const optRem2 = document.createElement('option');
            optRem2.value = h;
            optRem2.text = h;
            combineRem2.appendChild(optRem2);
        }

        // Combine Remark 3 dropdown
        if (combineRem3) {
            const optRem3 = document.createElement('option');
            optRem3.value = h;
            optRem3.text = h;
            combineRem3.appendChild(optRem3);
        }
    });
    
    // Restore if exists
    if (currentSel) sel.value = currentSel;
    if (currentInv && combineInv) combineInv.value = currentInv;
    if (currentRem1 && combineRem1) combineRem1.value = currentRem1;
    if (currentRem2 && combineRem2) combineRem2.value = currentRem2;
    if (currentRem3 && combineRem3) combineRem3.value = currentRem3;
}

async function updateFilterValues() {
    const col = document.getElementById('filter-column').value;
    const valSel = document.getElementById('filter-value');
    if (!valSel) return;
    
    valSel.innerHTML = '<option value="">Loading...</option>';
    
    if (!col) {
        valSel.innerHTML = '<option value="">Select Value...</option>';
        return;
    }
    
    try {
        const res = await fetch('/api/get_unique_values', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ column: col })
        });
        const data = await res.json();
        
        if (data.success) {
            valSel.innerHTML = '<option value="">Select Value...</option>';
            data.values.sort().forEach(v => {
                const opt = document.createElement('option');
                opt.value = v;
                opt.text = v;
                valSel.appendChild(opt);
            });
        } else {
            valSel.innerHTML = '<option value="">Error loading</option>';
        }
    } catch (e) {
        console.error(e);
        valSel.innerHTML = '<option value="">Error</option>';
    }
}

async function applyRawFilter() {
    const col = document.getElementById('filter-column').value;
    const val = document.getElementById('filter-value').value;
    
    if (!col || !val) {
        alert("Please select both a column and a value to filter.");
        return;
    }
    
    if (!confirm(`Are you sure? This will PERMANENTLY REMOVE all rows where "${col}" is NOT "${val}".`)) {
        return;
    }
    
    updateStatus(`Filtering data by ${col}=${val}...`);
    try {
        const res = await fetch('/api/filter_raw_data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ column: col, value: val })
        });
        const data = await res.json();
        
        if (data.success) {
            updateStatus("Data filtered. Reloading View...");
            await reloadRawData();
            // Reset filter selection since unique values might have changed
            document.getElementById('filter-value').innerHTML = '<option value="">Select Value...</option>';
        } else {
            alert("Error: " + data.error);
            updateStatus("Filtering Failed.");
        }
    } catch (e) {
        console.error(e);
        updateStatus("Filtering Error");
    }
}

async function combineRawRemarks() {
    const invCol = document.getElementById('combine-inv-col').value;
    const rem1Col = document.getElementById('combine-rem1-col').value;
    const rem2Col = document.getElementById('combine-rem2-col').value;
    const rem3Col = document.getElementById('combine-rem3-col').value;
    
    if (!invCol) {
        alert("Please select an Invoice column.");
        return;
    }
    
    updateStatus("Combining remarks for duplicate invoices...");
    try {
        const res = await fetch('/api/combine_remarks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                invoice_col: invCol, 
                remark1_col: rem1Col,
                remark2_col: rem2Col,
                remark3_col: rem3Col
            })
        });
        const data = await res.json();
        
        if (data.preview) {
            updateStatus("Remarks combined. Reloading preview...");
            await reloadRawData();
            alert("Remarks combined successfully.");
        } else {
            alert("Error: " + (data.error || "Unknown error"));
            updateStatus("Combination failed.");
        }
    } catch (e) {
        console.error(e);
        updateStatus("Combination Error");
    }
}

function renderTable(tableId, headers, rows, editable = false, sourceOptions = []) {
    const table = document.getElementById(tableId);
    if (!table) return;
    table.innerHTML = '';

    // Determine Logic
    // Raw Table: Selectable (needs _id first col)
    // Formatted Table: Editable (needs _id first col)

    const isRaw = (tableId === 'raw-preview-table');
    let displayHeaders = headers;
    let startColIndex = 0;

    // Always check for _id
    if (headers[0] === "_id") {
        displayHeaders = headers.slice(1);
        startColIndex = 1;
    }

    // Header
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');

    if (isRaw) {
        const th = document.createElement('th');
        th.style.width = "40px";
        th.innerHTML = '<input type="checkbox" id="raw-select-all">';
        headerRow.appendChild(th);

        // Bind Select All
        // Use timeout to ensure DOM update or just bind to the innerHTML element? 
        // Better to find it after adding to table, or creating element directly.
        const input = th.querySelector('input');
        input.onchange = (e) => {
            const checked = e.target.checked;
            document.querySelectorAll('#raw-preview-table .row-checkbox').forEach(cb => cb.checked = checked);
        };
    }

    displayHeaders.forEach(h => {
        const th = document.createElement('th');
        th.innerText = h;
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Body
    const tbody = document.createElement('tbody');
    let totalBal = 0;
    let totalAdj = 0;

    // Indices for Totals
    let balIdx = -1;
    let adjIdx = -1;
    if (isRaw) {
        balIdx = displayHeaders.findIndex(h => h.toLowerCase().includes('balance') || h.toLowerCase().includes('invoice bal'));
        adjIdx = displayHeaders.findIndex(h => h.toLowerCase().includes('adjust') || h.toLowerCase().includes('pay') || h.toLowerCase().includes('paid'));
        // Correct index relative to ROW data (which might contain _id)
        // If row has _id at 0, and displayHeaders starts at 1, then:
        // displayHeaders[0] is row[1]. 
        // So raw index = foundIndex + startColIndex.
    } else {
        balIdx = 5 - (editable ? 0 : 0); // Fixed Schema Indices are stable in formatted data (assuming strict array)
        adjIdx = 6;
        // Wait, Fixed Schema: "Sl. No", "Inv No", ..., "Balance" (5)
        // Check schema in LogicEngine: 
        // ["Sl. No", "Inv No", "Date", "Patient ID", "Patient Name", "Invoice Balance", "Amt To Adjust", "CustomerCode", "Remark"]
        // Indices: 0, 1, 2, 3, 4, 5, 6
    }

    rows.forEach(row => {
        const tr = document.createElement('tr');

        // Extract ID
        let rowId = null;
        let rowData = row;

        if (startColIndex === 1) {
            rowId = row[0];
            rowData = row.slice(1);
        }

        if (isRaw) {
            const td = document.createElement('td');
            td.innerHTML = `<input type="checkbox" class="row-checkbox" value="${rowId}">`;
            td.style.textAlign = "center";
            td.onclick = (e) => e.stopPropagation(); // prevent row click?
            tr.appendChild(td);

            // Allow row click to check box?
            tr.onclick = (e) => {
                if (e.target.type !== 'checkbox') {
                    const cb = td.querySelector('input');
                    cb.checked = !cb.checked;
                }
            };
            tr.style.cursor = "pointer";
        }

        if (editable) {
            tr.dataset.rowId = rowId;
        }

        rowData.forEach((cell, idx) => {
            const td = document.createElement('td');
            let val = cell !== null ? cell : '';

            // Format Dates
            if (tableId === 'formatted-preview-table' || tableId === 'result-preview-table') {
                if (idx === 2 && val !== "") {
                    val = excelDateToJSDate(val);
                }
            } else if (isRaw) {
                const header = displayHeaders[idx] ? displayHeaders[idx].toLowerCase() : '';
                if (header.includes('date') && val !== "") {
                    val = excelDateToJSDate(val);
                }
            }

            td.innerText = val;

            if (editable) {
                td.contentEditable = true;
                td.style.cursor = "text";
                td.onfocus = () => { td.style.outline = "2px solid #6366F1"; };
                td.onblur = () => onCellBlur(td, rowId, idx);
            }

            tr.appendChild(td);
        });

        // Totals (Use RAW DATA indices not Display)
        // If Raw: balIdx found in displayHeaders mapping.
        // rowData corresponds to displayHeaders.
        const balVal = (rowData[balIdx] || "0").toString().replace(/,/g, '');
        const adjVal = (rowData[adjIdx] || "0").toString().replace(/,/g, '');
        if (balIdx !== -1) totalBal += parseFloat(balVal) || 0;
        if (adjIdx !== -1) totalAdj += parseFloat(adjVal) || 0;

        tbody.appendChild(tr);
    });

    table.appendChild(tbody);

    // Update Global Totals
    tableTotals[tableId] = { balance: parseFloat(totalBal.toFixed(2)), adjust: parseFloat(totalAdj.toFixed(2)) };

    // Update Section Header Stats
    let sectionId = '';
    if (tableId === 'raw-preview-table') sectionId = 'raw-section';
    else if (tableId === 'formatted-preview-table') sectionId = 'formatted-section';
    else if (tableId === 'result-preview-table') sectionId = 'result-section';

    if (sectionId) {
        const h3 = document.querySelector(`#${sectionId} .collapsible-header h3`);
        if (h3) {
            // Restore original title if saved, or parse it?
            // Easiest: Hardcode titles or use dataset.
            let title = "Data";
            if (sectionId === 'raw-section') title = "Input Data";
            else if (sectionId === 'formatted-section') title = "Converted Data (Mapped)";
            else if (sectionId === 'result-section') title = "Result Data (Rules Applied)";

            h3.innerHTML = `${title} <span style="font-weight:normal; font-size:0.85em; color:#A7F3D0; margin-left:10px;">(Rows: ${rows.length}, Bal: ${totalBal.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}, Adj: ${totalAdj.toLocaleString('en-US', { style: 'currency', currency: 'USD' })})</span>`;
        }
    }
}

function checkTotalMismatch(id1, id2, stepName) {
    const t1 = tableTotals[id1];
    const t2 = tableTotals[id2];
    if (!t1 || !t2) return;

    const balMismatch = Math.abs(t1.balance - t2.balance) > 0.01;
    const adjMismatch = Math.abs(t1.adjust - t2.adjust) > 0.01;

    let msg = "";
    let isError = false;

    if (balMismatch || adjMismatch) {
        msg = `${stepName}: Total Mismatch Detected!\n`;
        if (balMismatch) msg += `Balance: ${t1.balance} vs ${t2.balance}\n`;
        if (adjMismatch) msg += `Amt to Adjust: ${t1.adjust} vs ${t2.adjust}`;
        isError = true;
    } else {
        msg = `${stepName}: Totals match successfully. (${t1.balance} / ${t1.adjust})`;
    }

    if (isError) {
        updateStatus("⚠️ " + msg.replace(/\n/g, " "));
        alert(msg);
    } else {
        updateStatus("✅ " + msg);
    }
}

// Track Edits
async function onCellBlur(td, rowId, idx) {
    td.style.outline = "none";
    const newVal = td.innerText;

    // Check key
    const uniqueKey = `${rowId}-${idx}`;

    // Add to pending (even if empty, maybe user cleared it)
    // We should compare with original? For now assume dirty.
    pendingUpdates[uniqueKey] = {
        row_id: rowId,
        col_index: idx,
        value: newVal
    };

    // Visual Style
    td.style.backgroundColor = "#FEF3C7"; // Light yellow
    td.style.color = "black";

    // Show Toolbar
    showEditToolbar();
}

function showEditToolbar() {
    let toolbar = document.getElementById('edit-toolbar');
    if (!toolbar) {
        toolbar = document.createElement('div');
        toolbar.id = 'edit-toolbar';
        toolbar.style.position = 'fixed';
        toolbar.style.bottom = '20px';
        toolbar.style.right = '20px';
        toolbar.style.backgroundColor = '#1F2937';
        toolbar.style.padding = '10px 20px';
        toolbar.style.borderRadius = '8px';
        toolbar.style.display = 'flex';
        toolbar.style.gap = '10px';
        toolbar.style.boxShadow = '0 4px 6px rgba(0,0,0,0.3)';
        toolbar.style.zIndex = '1000';
        toolbar.innerHTML = `
            <span style="color:white; align-self:center; margin-right:10px">Unsaved Changes</span>
            <button onclick="saveAllChanges()" style="background:#10B981; color:white; border:none; padding:5px 10px; border-radius:4px; cursor:pointer;">
               ✔ Save All
            </button>
            <button onclick="discardAllChanges()" style="background:#EF4444; color:white; border:none; padding:5px 10px; border-radius:4px; cursor:pointer;">
               ✖ Cancel
            </button>
        `;
        document.body.appendChild(toolbar);
    }
    toolbar.style.display = 'flex';
}

function hideEditToolbar() {
    const toolbar = document.getElementById('edit-toolbar');
    if (toolbar) toolbar.style.display = 'none';
}

async function saveAllChanges() {
    const updates = Object.values(pendingUpdates);
    if (updates.length === 0) return;

    updateStatus("Saving changes...");
    try {
        const res = await fetch('/api/update_data_batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ updates: updates })
        });
        const d = await res.json();

        if (d.success) {
            updateStatus("All changes saved.");
            pendingUpdates = {};
            hideEditToolbar();
            // Re-fetch? Or just clear styles? 
            // Clearing styles is faster.
            document.querySelectorAll('#formatted-preview-table td').forEach(td => {
                if (td.style.backgroundColor === "rgb(254, 243, 199)" || td.style.backgroundColor === "#FEF3C7") {
                    td.style.backgroundColor = "";
                    td.style.color = "";
                }
            });
            // Also update originalFormattedData to reflect local changes?
            // Actually reloading file resets it. Complexity. 
            // Better to consider current state as new base.
        } else {
            console.error("Save failed", d.error);
            updateStatus("Save Failed: " + d.error);
        }
    } catch (e) {
        console.error(e);
        updateStatus("Connection Error during Save");
    }
}

function discardAllChanges() {
    if (!originalFormattedData) return;
    updateStatus("Changes discarded.");
    pendingUpdates = {};
    renderTable('formatted-preview-table', originalFormattedData.headers, originalFormattedData.rows, true);
    hideEditToolbar();
}

// --- Prefix Rules Logic ---
function addRuleRow() {
    const container = document.getElementById('rules-container');
    const div = document.createElement('div');
    // Important: min-width: 0 prevents flex items from overflowing container
    div.style.cssText = "display:flex; gap:5px; margin-bottom:5px; align-items:center; width: 100%;";
    div.innerHTML = `
        <input type="text" placeholder="Prefix" class="rule-prefix" style="flex:1; min-width:0; background:#111827; border:1px solid #374151; color:white; padding:5px; border-radius:4px; font-size:0.8rem;">
        <input type="text" placeholder="Suffix" class="rule-suffix" style="flex:1; min-width:0; background:#111827; border:1px solid #374151; color:white; padding:5px; border-radius:4px; font-size:0.8rem;">
        <input type="text" placeholder="Code" class="rule-code" style="flex:1; min-width:0; background:#111827; border:1px solid #374151; color:white; padding:5px; border-radius:4px; font-size:0.8rem;">
        <button onclick="this.parentElement.remove()" style="background:#EF4444; color:white; border:none; padding:5px; border-radius:4px; cursor:pointer; min-width: 25px;">X</button>
    `;
    container.appendChild(div);
}

let resultData = null; // Stores data after Rules/Consolidation (Ready for Export)
let splitGroups = null; // Stores split data if active

// Duplicate applyPipeline removed.

// Bind Checkbox
// Bind Checkbox - REMOVED Auto-Run
// document.getElementById('rule-consolidate').addEventListener('change', () => applyPipeline(true));

// Consolidate Duplicates Logic
function consolidateRows(rows, keyIndices = [1]) {
    const grouped = {};
    const result = [];

    // Indices
    const balIdx = 5;
    const amtIdx = 6;
    const remarkIndices = [8, 9, 10]; // Remark 1, 2, 3

    rows.forEach(row => {
        // Create composite key from selected columns
        const compositeKey = keyIndices.map(idx => (row[idx] || "").toString().trim()).join('|');

        if (!compositeKey || compositeKey.replace(/\|/g, '') === "") {
            result.push([...row]);
            return;
        }

        if (!grouped[compositeKey]) {
            // New Group
            grouped[compositeKey] = [...row];
            // Parse Numbers - remove commas first
            const balVal = (row[balIdx] || "0").toString().replace(/,/g, '');
            const amtVal = (row[amtIdx] || "0").toString().replace(/,/g, '');
            grouped[compositeKey][balIdx] = parseFloat(balVal) || 0;
            grouped[compositeKey][amtIdx] = parseFloat(amtVal) || 0;
            // Init Remarks list
            grouped[compositeKey]._remarkPool = [];
            remarkIndices.forEach(idx => {
                const val = (row[idx] || "").toString().trim();
                if (val) grouped[compositeKey]._remarkPool.push(val);
            });
        } else {
            // Aggregate - remove commas first
            const balVal = (row[balIdx] || "0").toString().replace(/,/g, '');
            const amtVal = (row[amtIdx] || "0").toString().replace(/,/g, '');
            grouped[compositeKey][balIdx] += parseFloat(balVal) || 0;
            grouped[compositeKey][amtIdx] += parseFloat(amtVal) || 0;
            // Collect Remarks
            remarkIndices.forEach(idx => {
                const val = (row[idx] || "").toString().trim();
                if (val) grouped[compositeKey]._remarkPool.push(val);
            });
        }
    });

    // Format Result
    Object.values(grouped).forEach(row => {
        row[balIdx] = row[balIdx].toFixed(2);
        row[amtIdx] = row[amtIdx].toFixed(2);
        
        // Final Remarks: Unique values joined by comma - put in Remark 1, clear 2 & 3
        if (row._remarkPool) {
            row[8] = [...new Set(row._remarkPool)].join(', ');
            row[9] = "";
            row[10] = "";
            delete row._remarkPool;
        }
        
        // Trim to 9 columns for Result Data output (Remarks only, not 3 columns)
        result.push(row);
    });

    // Re-index Serial
    result.forEach((r, i) => r[0] = i + 1);

    return result;
}

// State for Mapping
let mappingState = {};

function applyColumnMapping(sourceColName, targetColIndex) {
    if (!sourceColName) {
        delete mappingState[targetColIndex];
    } else {
        mappingState[targetColIndex] = sourceColName;
    }
}

function confirmMapping() {
    if (!rawDataStore) {
        updateStatus("No source data to map.");
        return;
    }

    // Validate Mandatory Key (Inv No = Index 1)
    if (!mappingState || !mappingState[1]) {
        alert("Critical Error: 'Inv No' column is not mapped. You must map a source column to 'Inv No' to continue.");
        updateStatus("Mapping Failed: Missing Invoice Number.");
        return;
    }

    updateStatus("Processing Mapping & Filtering...");

    console.log("DEBUG: confirmMapping START");
    console.log("DEBUG: mappingState:", JSON.stringify(mappingState));
    console.log("DEBUG: rawDataStore rows:", rawDataStore.rows.length);

    // Process Data from Raw -> Mapped
    const newRows = [];
    let serial = 1;

    rawDataStore.rows.forEach((rawRow, rIdx) => {
        const fmtRow = Array(11).fill("");
        let hasInvoice = false;

        for (let i = 1; i < 11; i++) {
            const srcCol = mappingState[i];
            if (srcCol) {
                const rawHeaderIdx = rawDataStore.headers.indexOf(srcCol);
                if (rawHeaderIdx !== -1) {
                    const val = rawRow[rawHeaderIdx];
                    let finalVal = val !== null && val !== undefined ? val : "";

                    // Format Date if index 2
                    if (i === 2 && finalVal !== "") {
                        finalVal = excelDateToJSDate(finalVal);
                    }

                    fmtRow[i] = finalVal;

                    // Inv No is Index 1
                    if (i === 1 && fmtRow[i].toString().trim() !== "") {
                        hasInvoice = true;
                    }
                }
            }
        }

        if (hasInvoice) {
            fmtRow[0] = serial++;
            newRows.push(fmtRow);
        }
    });

    console.log(`DEBUG: Generated ${newRows.length} new rows.`);

    if (newRows.length === 0) {
        const invCol = mappingState[1] || "None";
        let validInvCount = 0;
        let sampleVal = "N/A";

        if (rawDataStore && rawDataStore.headers.indexOf(invCol) !== -1) {
            const idx = rawDataStore.headers.indexOf(invCol);
            rawDataStore.rows.forEach(r => {
                if (r[idx] && r[idx].toString().trim() !== "") validInvCount++;
            });
            if (rawDataStore.rows.length > 0) sampleVal = rawDataStore.rows[0][idx];
        }

        alert(`Warning: 0 rows generated!\n\nDiagnostics:\n- Mapped 'Inv No' to: "${invCol}"\n- Total Raw Rows: ${rawDataStore.rows.length}\n- 'Inv No' Values Found: ${validInvCount}\n- Sample Value (Row 1): "${sampleVal}"\n\nSolution: Please select a column that actually contains Invoice Numbers.`);

        updateStatus("Mapping Error: 0 rows generated.");
        return;
    }

    // Auto-populate CustomerCode logic MOVED to applyPipeline (Rules Stage)
    // per user request: "Coverted data should not take the CutomerCode after column mapping. It should load after Logic & Rules applied."

    /* 
    // DEPRECATED BLOCK
    const formatSelect = document.getElementById('format-select');
    // ...
    */
    console.log("Debug: CustomerCode population deferred to Rules Engine.");

    // Store Base Mapped Data
    mappedData = {
        headers: FIXED_SCHEMA,
        rows: newRows
    };

    // Render Mapped Data (Source)
    originalFormattedData = mappedData;
    renderTable('formatted-preview-table', FIXED_SCHEMA, newRows, true, currentHeaders);

    // Auto-Open Rules Section
    toggleSidebarSection('side-rules-section');

    // Precise Raw Calculation based on Mapping Selection
    // Only sum rows that HAVE an invoice (matching the filtering logic above)
    let rawBalSum = 0;
    let rawAdjSum = 0;
    const invMapCol = mappingState[1];
    const balMapCol = mappingState[5];
    const adjMapCol = mappingState[6];

    const rawInvIdx = invMapCol ? rawDataStore.headers.indexOf(invMapCol) : -1;
    const rawBalIdx = balMapCol ? rawDataStore.headers.indexOf(balMapCol) : -1;
    const rawAdjIdx = adjMapCol ? rawDataStore.headers.indexOf(adjMapCol) : -1;

    rawDataStore.rows.forEach(r => {
        const hasInv = rawInvIdx !== -1 && r[rawInvIdx] && r[rawInvIdx].toString().trim() !== "";
        if (hasInv) {
            if (rawBalIdx !== -1) rawBalSum += parseFloat(r[rawBalIdx]) || 0;
            if (rawAdjIdx !== -1) rawAdjSum += parseFloat(r[rawAdjIdx]) || 0;
        }
    });

    tableTotals['raw-preview-table'] = {
        balance: parseFloat(rawBalSum.toFixed(2)),
        adjust: parseFloat(rawAdjSum.toFixed(2))
    };

    // Validate Totals (Compare Raw with Mapped)
    checkTotalMismatch('raw-preview-table', 'formatted-preview-table', 'Column Mapping');

    // Save BASE state (just in case user exports without rules)
    saveFullData(newRows);

    // Auto-Expand Converted Data & Rules
    toggleSection('formatted-section', true);
    toggleSidebarSection('side-rules-section', true);
}

async function saveFullData(rows) {
    try {
        const response = await fetch('/api/save_overwrite', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rows: rows })
        });
        const res = await response.json();
        if (res.success) {
            updateStatus("Mapping Confirmed & Saved.");
            loadFormattedPreview();
        } else {
            updateStatus("Save Failed: " + res.error);
        }
    } catch (e) {
        console.error(e);
        updateStatus("Save Error.");
    }
}

async function loadFormattedPreview() {
    try {
        const res = await fetch('/api/get_preview');
        const data = await res.json();
        if (data.rows) {
            originalFormattedData = data;
            renderTable('formatted-preview-table', data.headers, data.rows, true, currentHeaders);
        }
    } catch (e) {
        console.error(e);
    }
}

function filterRows() {
    // Deprecated by Strict Filter on Confirmation
    // But useful if user manually messes up?
    // User said: "skip the blank invoice rows completely... when loading".
    // So filtering visual rows is less important if source is clean.
    // But harmless to keep.
    const table = document.getElementById('formatted-preview-table');
    if (!table) return;
    const tbody = table.querySelector('tbody');
    const rows = tbody.querySelectorAll('tr');

    // Inv No is Index 1 in ["Sl. No", "Inv No", ...]
    // If _id is hidden, Inv No is 2nd Visible Column (Index 1).
    const invColIndex = 1;

    rows.forEach(tr => {
        if (tr.children[invColIndex]) {
            const val = tr.children[invColIndex].innerText.trim();
            // LogicEngine preview might return nulls or empty.
            if (!val) {
                tr.style.display = 'none';
            } else {
                tr.style.display = '';
            }
        }
    });
}


function toggleSection(sectionId, forceOpen = null) {
    const section = document.getElementById(sectionId);
    if (!section) return;

    const sections = ['raw-section', 'formatted-section', 'result-section'];

    if (forceOpen === true) {
        // Enforce Exclusive Open
        sections.forEach(id => {
            const s = document.getElementById(id);
            if (s) s.classList.remove('open');
        });
        section.classList.add('open');
    } else if (forceOpen === false) {
        section.classList.remove('open');
    } else {
        const isOpen = section.classList.contains('open');
        if (!isOpen) {
            // Exclusive Open
            sections.forEach(id => {
                const s = document.getElementById(id);
                if (s) s.classList.remove('open');
            });
            section.classList.add('open');
        } else {
            section.classList.remove('open');
        }
    }
}

// Sidebar Accordion Behavior
function toggleSidebarSection(sectionId, forceOpen = null) {
    const section = document.getElementById(sectionId);
    if (!section) return;

    const sections = ['side-mapping-section', 'side-rules-section', 'side-split-section', 'side-export-section'];

    if (forceOpen === true) {
        sections.forEach(id => {
            const s = document.getElementById(id);
            if (s) s.classList.remove('open');
        });
        section.classList.add('open');
    } else if (forceOpen === false) {
        section.classList.remove('open');
    } else {
        const isOpen = section.classList.contains('open');
        sections.forEach(id => {
            const s = document.getElementById(id);
            if (s) s.classList.remove('open');
        });
        if (!isOpen) section.classList.add('open');
    }
}

function toggleLeftColumn() {
    const container = document.getElementById('preview-container');
    container.classList.toggle('left-collapsed');
}

function renderMappingUI() {
    const container = document.getElementById('mapping-sidebar');
    if (!container || !rawDataStore) return;

    container.innerHTML = '';
    mappingState = {}; // Reset state

    // Fixed Schema Targets
    const targets = FIXED_SCHEMA;

    // Create rows for each expected target (skiping Sl. No)
    targets.forEach((defaultTarget, defaultIndex) => {
        // Remove only Sl. No from items to map
        if (defaultTarget === "Sl. No") return;

        const fieldDiv = document.createElement('div');
        fieldDiv.className = 'mapping-field';

        // LEFT: Target Label (Fixed)
        const targetLabel = document.createElement('div');
        targetLabel.className = 'target-label';
        targetLabel.innerText = defaultTarget;

        // Store index for logic
        fieldDiv.dataset.targetIndex = defaultIndex;

        // RIGHT: Source Dropdown
        const sourceSelect = document.createElement('select');
        sourceSelect.className = 'mapping-select';

        const defOpt = document.createElement('option');
        defOpt.value = "";
        defOpt.text = "-- Source --";
        sourceSelect.appendChild(defOpt);

        rawDataStore.headers.forEach(h => {
            if (h === "_id") return;

            const opt = document.createElement('option');
            opt.value = h;
            opt.text = h;

            // Smart Auto-Match
            const cleanTarget = defaultTarget.toLowerCase().replace(/[^a-z0-9]/g, '');
            const cleanSource = h.toLowerCase().replace(/[^a-z0-9]/g, '');
            if (cleanSource === cleanTarget || (cleanTarget.length > 3 && cleanSource.includes(cleanTarget))) {
                opt.selected = true;
                mappingState[defaultIndex] = h;
            }

            sourceSelect.appendChild(opt);
        });

        // Event Listeners
        const updateMapping = () => {
            rebuildMappingState();
        };

        sourceSelect.onchange = updateMapping;

        fieldDiv.appendChild(targetLabel);
        fieldDiv.appendChild(sourceSelect);
        container.appendChild(fieldDiv);
    });
}

function rebuildMappingState() {
    mappingState = {};
    const container = document.getElementById('mapping-sidebar');
    if (!container) return;

    const rows = container.querySelectorAll('.mapping-field');
    rows.forEach(row => {
        const tIdx = parseInt(row.dataset.targetIndex);
        const sourceSel = row.querySelector('.mapping-select');
        if (!isNaN(tIdx) && sourceSel) {
            const sVal = sourceSel.value;
            if (sVal) {
                mappingState[tIdx] = sVal;
            }
        }
    });
}

// Helper for above (needs to be outside renderMappingUI or hoisted)
// I will insert it inside renderMappingUI or append it?
// multi_replace can handle replacing the function body.
// I will replace the whole function renderMappingUI and add rebuildMappingState helper.


function updateStatus(msg) {
    document.getElementById('app-status').innerText = msg;
}

async function runProcess() {
    updateStatus("Processing...");
    const consoleLog = document.getElementById('console-log');
    consoleLog.innerHTML += `<p>> Starting Process...</p>`;

    try {
        const res = await fetch('/api/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ profile: document.getElementById('format-select').value })
        });
        const data = await res.json();
        consoleLog.innerHTML += `<p>> ${data.message}</p>`;

        if (data.files) {
            data.files.forEach(f => {
                consoleLog.innerHTML += `<p style='color:cyan'>> Generated: <a href="/download_file/${f}" target="_blank" style="color: #6366F1; text-decoration: underline;">${f}</a></p>`;
            });
        }

    } catch (e) {
        consoleLog.innerHTML += `<p style='color:red'>> Error: ${e}</p>`;
    }
}

let preparedFiles = []; // Stores {name, label} for multi-file

async function prepareFile() {
    if (!resultData && !mappedData && !originalFormattedData) {
        updateStatus("No data to export. Apply rules/split first.");
        return;
    }

    const btnPrepare = document.getElementById('btn-prepare');
    btnPrepare.disabled = true;

    try {
        updateStatus("Preparing File(s) for download...");
        const formatSelect = document.getElementById('export-format');
        const fileFormat = formatSelect ? formatSelect.value : 'xlsx';
        const profile = document.getElementById('format-select').value;
        const customNameInput = document.getElementById('download-filename');
        let customName = customNameInput ? customNameInput.value.trim() : null;

        const container = document.getElementById('download-list-container');
        container.innerHTML = ''; // Clear previous
        preparedFiles = [];
        preparedFilename = null;

        // Determine Data to work with
        let dataToSave = resultData ? resultData.rows : (mappedData ? mappedData.rows : (originalFormattedData ? originalFormattedData.rows : null));

        if (splitGroups && Object.keys(splitGroups).length > 0) {
            // MULTI FILE EXPORT
            const keys = Object.keys(splitGroups);
            const total = keys.length;
            updateStatus(`Starting generation of ${total} files...`);

            for (let i = 0; i < total; i++) {
                const key = keys[i];
                const rows = splitGroups[key];
                
                updateStatus(`Processing ${i + 1}/${total}: ${key}...`);

                // Determine Filename (Custom Requirement: MathingOfARReceipts-xls_[Code]_[Suffix].xlsx)
                let suffix = '';
                if (key.endsWith('100')) suffix = '_A';
                else if (key.endsWith('101')) suffix = '_B';
                else if (key.endsWith('102')) suffix = '_C';

                const splitFilename = `MathingOfARReceipts-xls_${key}${suffix}`;

                try {
                    // Filter out rows with empty invoice number before saving
                    const validRows = rows.filter(r => r[1] && r[1].toString().trim());
                    
                    // 1. Save this specific group to DB
                    const saveRes = await fetch('/api/save_overwrite', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ rows: validRows })
                    });
                    
                    if (!saveRes.ok) throw new Error(`Save failed for ${key}`);

                    // 2. Export
                    const exportRes = await fetch('/api/export_custom', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            profile: profile,
                            format: fileFormat,
                            filename: splitFilename
                        })
                    });
                    
                    if (!exportRes.ok) {
                        const errData = await exportRes.json();
                        throw new Error(`Export failed for ${key}: ${errData.error || 'Unknown error'}`);
                    }

                    const data = await exportRes.json();
                    if (data.file) {
                        preparedFiles.push({ name: data.file, label: `Download: ${key}` });
                    }
                } catch (err) {
                    console.error(`Error generating ${key}:`, err);
                    updateStatus(`Warning: Failed to generate ${key}. Continuing...`);
                    // Small delay to let the system breathe
                    await new Promise(r => setTimeout(r, 500));
                }
            }

            // Render Download Buttons
            if (preparedFiles.length > 0) {
                preparedFiles.forEach(pf => {
                    const btn = document.createElement('button');
                    btn.innerText = pf.label;
                    btn.className = "download-link-btn";
                    btn.onclick = () => window.location.href = `/download_file/${pf.name}`;
                    Object.assign(btn.style, {
                        width: "100%", padding: "8px", background: "#10B981",
                        color: "white", border: "none", borderRadius: "4px",
                        fontWeight: "bold", cursor: "pointer", marginBottom: "4px"
                    });
                    container.appendChild(btn);
                });
                updateStatus(`Generated ${preparedFiles.length} files successfully.`);
            } else {
                updateStatus("No files were generated.");
            }

        } else if (dataToSave) {
            // SINGLE FILE EXPORT
            updateStatus("Saving data to server...");
            const saved = await saveFullData(dataToSave);
            if (!saved) throw new Error("Could not save data to server.");

            updateStatus("Generating file...");
            const res = await fetch('/api/export_custom', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    profile: profile,
                    filename: customName,
                    format: fileFormat
                })
            });
            
            if (!res.ok) throw new Error("Server error during export.");
            
            const data = await res.json();

            if (data.file) {
                preparedFilename = data.file;

                const btn = document.createElement('button');
                btn.id = "btn-download";
                btn.innerText = "Download Ready: " + (data.file.length > 20 ? data.file.substring(0, 17) + "..." : data.file);
                btn.onclick = executeDownload;
                Object.assign(btn.style, {
                    width: "100%", padding: "10px", background: "#10B981",
                    color: "white", border: "none", borderRadius: "4px",
                    fontWeight: "bold", cursor: "pointer"
                });
                container.appendChild(btn);
                updateStatus("File prepared successfully.");
            } else {
                throw new Error(data.error || "Unknown export error");
            }
        }
    } catch (e) {
        console.error(e);
        updateStatus("Preparation Error: " + e.message);
    } finally {
        const btnPrepare = document.getElementById('btn-prepare');
        if (btnPrepare) btnPrepare.disabled = false;
    }
}

function executeDownload() {
    if (preparedFilename) {
        window.location.href = `/download_file/${preparedFilename}`;
        updateStatus("Download Started.");
    }
}

// Global Exports for Debugging
window.uploadFile = uploadFile;
window.checkSheets = checkSheets;
window.updateStatus = updateStatus;
window.saveFullData = saveFullData;
window.applyPipeline = applyPipeline;


function addRuleRowWithValues(prefix, suffix, code) {
    const container = document.getElementById('rules-container');
    const div = document.createElement('div');
    div.style.cssText = "display:flex; gap:5px; margin-bottom:5px; align-items:center; width: 100%;";
    div.innerHTML = `
        <input type="text" placeholder="Prefix" class="rule-prefix" value="${prefix}" style="flex:1; min-width:0; background:#111827; border:1px solid #374151; color:white; padding:5px; border-radius:4px; font-size:0.8rem;">
        <input type="text" placeholder="Suffix" class="rule-suffix" value="${suffix}" style="flex:1; min-width:0; background:#111827; border:1px solid #374151; color:white; padding:5px; border-radius:4px; font-size:0.8rem;">
        <input type="text" placeholder="Code" class="rule-code" value="${code}" style="flex:1; min-width:0; background:#111827; border:1px solid #374151; color:white; padding:5px; border-radius:4px; font-size:0.8rem;">
        <button onclick="this.parentElement.remove()" style="background:#EF4444; color:white; border:none; padding:5px; border-radius:4px; cursor:pointer; min-width: 25px;">X</button>
    `;
    container.appendChild(div);
}


// --- Template Management System ---

async function fetchTemplates() {
    // Populate Dropdowns
    ['mapping', 'rules'].forEach(async (type) => {
        const select = document.getElementById(`${type}-template-select`);
        if (!select) return;

        // Clear except first
        select.innerHTML = '<option value="">-- Load Template --</option>';

        try {
            const res = await fetch('/api/get_settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ profile: '_TEMPLATES_', section: type })
            });
            const data = await res.json();
            if (data.success && data.settings) {
                Object.keys(data.settings).forEach(name => {
                    const opt = document.createElement('option');
                    opt.value = name;
                    opt.text = name;
                    select.appendChild(opt);
                });
            }
        } catch (e) {
            console.error(`Error fetching ${type} templates`, e);
        }
    });
}

async function saveTemplate(type) {
    const nameInput = document.getElementById(`${type}-template-name`);
    const name = nameInput.value.trim();
    if (!name) {
        alert("Please enter a template name.");
        return;
    }

    // 1. Gather Data
    let config = {};
    if (type === 'mapping') {
        config = JSON.parse(JSON.stringify(mappingState)); // Deep copy
    } else if (type === 'rules') {
        config = [];
        document.querySelectorAll('#rules-container > div').forEach(div => {
            const p = div.querySelector('.rule-prefix').value.trim();
            const s = div.querySelector('.rule-suffix').value.trim();
            const c = div.querySelector('.rule-code').value.trim();
            if (p || s || c) config.push({ p, s, c });
        });
    }

    updateStatus(`Saving ${type} template...`);

    try {
        // Fetch current templates first
        const getRes = await fetch('/api/get_settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ profile: '_TEMPLATES_', section: type })
        });
        const getData = await getRes.json();
        let currentTemplates = getData.settings || {};

        // Add new
        currentTemplates[name] = config;

        // Save back
        const saveRes = await fetch('/api/save_settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                profile: '_TEMPLATES_',
                section: type,
                config: currentTemplates
            })
        });

        const saveData = await saveRes.json();
        if (saveData.success) {
            updateStatus("Template Saved.");
            nameInput.value = ''; // Clear input
            fetchTemplates(); // Refresh list
        } else {
            alert("Save Failed: " + saveData.error);
        }
    } catch (e) {
        console.error(e);
        updateStatus("Template Save Error.");
    }
}

async function loadTemplate(type, name) {
    if (!name) {
        const select = document.getElementById(`${type}-template-select`);
        if (select) {
            name = select.value;
        }
    }

    if (!name) {
        alert("Please select a template first.");
        return;
    }

    updateStatus(`Loading ${type} template...`);

    try {
        const res = await fetch('/api/get_settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ profile: '_TEMPLATES_', section: type })
        });
        const data = await res.json();
        const templates = data.settings || {};
        const config = templates[name];

        if (!config) {
            updateStatus("Template not found.");
            return;
        }

        if (type === 'mapping') {
            applyMappingTemplate(config);
        } else if (type === 'rules') {
            applyRulesTemplate(config);
        }
        updateStatus(`Template '${name}' Loaded.`);

    } catch (e) {
        console.error(e);
        updateStatus("Error loading template.");
    }
}

async function deleteSelectedTemplate(type) {
    const select = document.getElementById(`${type}-template-select`);
    const name = select?.value;
    
    if (!name) {
        alert("Please select a template to delete.");
        return;
    }
    
    if (!confirm(`Are you sure you want to delete template "${name}"? This action cannot be undone.`)) {
        return;
    }
    
    updateStatus(`Deleting ${type} template...`);
    
    try {
        const res = await fetch('/api/delete_template', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                profile: '_TEMPLATES_',
                section: type,
                name: name
            })
        });
        
        const data = await res.json();
        if (data.success) {
            updateStatus(`Template '${name}' deleted.`);
            fetchTemplates(); // Refresh List
        } else {
            alert("Delete Failed: " + (data.error || "Unknown error"));
        }
    } catch (e) {
        console.error(e);
        alert("Error deleting template: " + e.message);
    }
}


async function deleteTemplate(type, name) {
    if (!confirm(`Are you sure you want to delete template "${name}"?`)) return;

    updateStatus(`Deleting ${type} template...`);

    try {
        const res = await fetch('/api/delete_template', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                profile: '_TEMPLATES_',
                section: type,
                name: name
            })
        });

        const data = await res.json();
        if (data.success) {
            updateStatus(`Template '${name}' deleted.`);
            fetchTemplates(); // Refresh List
        } else {
            alert("Delete Failed: " + data.error);
        }
    } catch (e) {
        console.error(e);
        updateStatus("Delete Error.");
    }
}



function applyMappingTemplate(savedMapping) {
    if (!rawDataStore || !rawDataStore.headers) {
        alert("Please load a file first.");
        return;
    }

    const container = document.getElementById('mapping-sidebar');
    if (!container) return;

    let matchCount = 0;

    // Iterate ALL rows in UI to find matching target
    const rows = container.querySelectorAll('.mapping-field');
    rows.forEach(fieldDiv => {
        const tIdx = parseInt(fieldDiv.dataset.targetIndex);
        const sourceSel = fieldDiv.querySelector('.mapping-select');

        if (!isNaN(tIdx) && sourceSel) {
            // Do we have a saved mapping for this target?
            if (savedMapping.hasOwnProperty(tIdx)) {
                const savedSource = savedMapping[tIdx];

                // Check if this source exists in current file headers
                if (rawDataStore.headers.includes(savedSource)) {
                    sourceSel.value = savedSource;
                    // Update global state
                    mappingState[tIdx] = savedSource;
                    matchCount++;
                } else {
                    // Fallback to default if column missing in this file
                    sourceSel.value = "";
                    mappingState[tIdx] = "";
                }
            }
        }
    });

    if (matchCount > 0) {
        updateStatus(`Matches found: ${matchCount}. Review and Confirm.`);
    } else {
        updateStatus("No matching columns found in this file.");
    }
}

function applyRulesTemplate(rules) {
    const container = document.getElementById('rules-container');
    container.innerHTML = '';
    rules.forEach(r => {
        addRuleRowWithValues(r.p, r.s, r.c);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    fetchTemplates();
});
