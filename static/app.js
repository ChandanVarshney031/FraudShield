// GuardianAI Dashboard Application Logic

// Global Application State
let appState = {
    simulationInterval: null,
    simulatorConfig: {
        active: false,
        interval_ms: 1500,
        fraud_probability: 0.08
    },
    transactions: [],
    metrics: {},
    rules: {},
    selectedTransaction: null
};

// Chart instances
let distributionChart = null;
let importanceChart = null;

// API Base Endpoints
const IS_GITHUB_PAGES = window.location.hostname.includes('github.io');
const IS_LOCAL_FILE = window.location.protocol === 'file:';
const IS_DEV_SERVER = window.location.port && window.location.port !== '8000';

const API_BASE = IS_GITHUB_PAGES 
    ? 'https://fraudshield-dwal.onrender.com' 
    : (IS_LOCAL_FILE || IS_DEV_SERVER) 
        ? 'http://127.0.0.1:8000' 
        : '';

const API = {
    rules: API_BASE + '/api/rules',
    simulatorConfig: API_BASE + '/api/simulator/config',
    transactions: API_BASE + '/api/transactions',
    metrics: API_BASE + '/api/metrics',
    simulateNext: API_BASE + '/api/simulate/next',
    predict: API_BASE + '/api/predict',
    retrain: API_BASE + '/api/retrain',
    reset: API_BASE + '/api/metrics/reset'
};

// DOM Elements
const elements = {
    modelStatus: document.getElementById('model-status'),
    simStatusDot: document.getElementById('sim-status-dot'),
    simStatusText: document.getElementById('sim-status-text'),
    btnRetrain: document.getElementById('btn-retrain'),
    
    // Metrics
    valProcessedVolume: document.getElementById('val-processed-volume'),
    valProcessedCount: document.getElementById('val-processed-count'),
    valSavings: document.getElementById('val-savings'),
    valBlockedCount: document.getElementById('val-blocked-count'),
    valAccuracy: document.getElementById('val-accuracy'),
    valF1: document.getElementById('val-f1'),
    valAlertRate: document.getElementById('val-alert-rate'),
    valPrecision: document.getElementById('val-precision'),
    valRecall: document.getElementById('val-recall'),
    
    // Simulator Controls
    toggleAutoSim: document.getElementById('toggle-auto-sim'),
    inputSpeed: document.getElementById('input-speed'),
    labelSpeed: document.getElementById('label-speed'),
    inputFraudRate: document.getElementById('input-fraud-rate'),
    labelFraudRate: document.getElementById('label-fraud-rate'),
    btnTriggerNormal: document.getElementById('btn-trigger-normal'),
    btnTriggerFraud: document.getElementById('btn-trigger-fraud'),
    
    // Checkout Form
    checkoutForm: document.getElementById('checkout-form'),
    formName: document.getElementById('form-name'),
    formCardNetwork: document.getElementById('form-card-network'),
    formAge: document.getElementById('form-age'),
    formAmount: document.getElementById('form-amount'),
    formCategory: document.getElementById('form-category'),
    formCardCountry: document.getElementById('form-card-country'),
    formIpCountry: document.getElementById('form-ip-country'),
    formVelocity: document.getElementById('form-velocity'),
    formDevice: document.getElementById('form-device'),
    
    // Stream
    streamContainer: document.getElementById('stream-container'),
    btnClearFeed: document.getElementById('btn-clear-feed'),
    
    // Rules
    ruleAmountActive: document.getElementById('rule-amount-active'),
    ruleAmountVal: document.getElementById('rule-amount-val'),
    ruleMismatchActive: document.getElementById('rule-mismatch-active'),
    ruleVelocityActive: document.getElementById('rule-velocity-active'),
    ruleVelocityVal: document.getElementById('rule-velocity-val'),
    ruleDeviceActive: document.getElementById('rule-device-active'),
    ruleMlVal: document.getElementById('rule-ml-val'),
    
    // Chart labels
    statCountApproved: document.getElementById('stat-count-approved'),
    statCountReview: document.getElementById('stat-count-review'),
    statCountBlocked: document.getElementById('stat-count-blocked'),
    
    // Drawer
    drawerOverlay: document.getElementById('drawer-overlay'),
    detailDrawer: document.getElementById('detail-drawer'),
    btnCloseDrawer: document.getElementById('btn-close-drawer'),
    
    // Drawer Contents
    auditDetailBadge: document.getElementById('audit-detail-badge'),
    auditDetailScore: document.getElementById('audit-detail-score'),
    auditDetailDecision: document.getElementById('audit-detail-decision'),
    auditDetailExplanations: document.getElementById('audit-detail-explanations'),
    profileName: document.getElementById('profile-name'),
    profileCard: document.getElementById('profile-card'),
    profileNetwork: document.getElementById('profile-network'),
    profileCardCountry: document.getElementById('profile-card-country'),
    profileIpCountry: document.getElementById('profile-ip-country'),
    profileCategory: document.getElementById('profile-category'),
    profileDevice: document.getElementById('profile-device'),
    profileVelocity: document.getElementById('profile-velocity'),
    profileHistorical: document.getElementById('profile-historical')
};

// Initial setup on window load
window.addEventListener('DOMContentLoaded', async () => {
    // 1. Initialize empty charts
    initCharts();
    
    // 2. Fetch configurations and initial state
    await fetchRules();
    await fetchSimulatorConfig();
    await loadInitialData();
    
    // 3. Setup event listeners
    setupEventListeners();
});

// Init Charts using Chart.js
function initCharts() {
    // Distribution Chart
    const ctxDist = document.getElementById('distributionChart').getContext('2d');
    distributionChart = new Chart(ctxDist, {
        type: 'doughnut',
        data: {
            labels: ['Approved', 'Review', 'Blocked'],
            datasets: [{
                data: [0, 0, 0],
                backgroundColor: [
                    'rgba(16, 185, 129, 0.75)',  // Emerald Green
                    'rgba(245, 158, 11, 0.75)',  // Amber Orange
                    'rgba(239, 68, 68, 0.75)'    // Rose Red
                ],
                borderColor: [
                    '#10b981',
                    '#f59e0b',
                    '#ef4444'
                ],
                borderWidth: 1.5,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            cutout: '70%'
        }
    });

    // Importance Chart (XAI drivers) inside drawer
    const ctxImp = document.getElementById('importanceChart').getContext('2d');
    importanceChart = new Chart(ctxImp, {
        type: 'bar',
        data: {
            labels: [
                'Amount', 'Odd Hour', 'Age Profile', 'Velocity', 
                'Loc Mismatch', 'Device Risk', 'Category Risk', 'Card Risk'
            ],
            datasets: [{
                label: 'Relative Driver Weight',
                data: [0, 0, 0, 0, 0, 0, 0, 0],
                backgroundColor: 'rgba(99, 102, 241, 0.6)',
                borderColor: '#6366f1',
                borderWidth: 1.5,
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#9ca3af', font: { size: 10 } },
                    min: 0,
                    max: 1
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#f3f4f6', font: { size: 11 } }
                }
            }
        }
    });
}

// Fetch Configurations & Initial Database
async function fetchRules() {
    try {
        const response = await fetch(API.rules);
        const rules = await response.json();
        appState.rules = rules;
        syncRulesToUI(rules);
    } catch (err) {
        console.error("Error fetching rules:", err);
    }
}

async function fetchSimulatorConfig() {
    try {
        const response = await fetch(API.simulatorConfig);
        const config = await response.json();
        appState.simulatorConfig = config;
        syncSimulatorConfigToUI(config);
    } catch (err) {
        console.error("Error fetching simulator config:", err);
    }
}

async function loadInitialData() {
    try {
        // Fetch historical transactions
        const txResponse = await fetch(API.transactions);
        appState.transactions = await txResponse.json();
        renderTransactionsFeed();
        
        // Fetch initial metrics
        await refreshMetrics();
    } catch (err) {
        console.error("Error loading initial data:", err);
    }
}

// UI Sync Methods
function syncRulesToUI(rules) {
    elements.ruleAmountActive.checked = rules.block_high_amount;
    elements.ruleAmountVal.value = rules.block_high_amount_threshold;
    elements.ruleMismatchActive.checked = rules.block_location_mismatch;
    elements.ruleVelocityActive.checked = rules.block_high_velocity;
    elements.ruleVelocityVal.value = rules.block_high_velocity_threshold;
    elements.ruleDeviceActive.checked = rules.block_high_risk_device;
    elements.ruleMlVal.value = rules.min_ml_threshold;
}

function syncSimulatorConfigToUI(config) {
    elements.toggleAutoSim.checked = config.active;
    elements.inputSpeed.value = config.interval_ms;
    elements.labelSpeed.innerText = (config.interval_ms / 1000).toFixed(1) + 's';
    elements.inputFraudRate.value = Math.round(config.fraud_probability * 100);
    elements.labelFraudRate.innerText = Math.round(config.fraud_probability * 100) + '%';
    
    // Status visual
    if (config.active) {
        elements.simStatusDot.className = 'status-dot orange';
        elements.simStatusText.innerText = 'Active (' + (config.interval_ms / 1000).toFixed(1) + 's interval)';
        startSimulatorLoop();
    } else {
        elements.simStatusDot.className = 'status-dot';
        elements.simStatusText.innerText = 'Inactive';
        stopSimulatorLoop();
    }
}

// Sync Form country mismatches easily for demoing
document.querySelectorAll('.country-sync').forEach(select => {
    select.addEventListener('change', () => {
        // Just logs or visually indicators if mismatch
        const billing = elements.formCardCountry.value;
        const ip = elements.formIpCountry.value;
        if (billing !== ip) {
            elements.formIpCountry.style.borderColor = 'var(--color-orange)';
        } else {
            elements.formIpCountry.style.borderColor = '';
        }
    });
});

// Event Listeners
function setupEventListeners() {
    // Simulator controls
    elements.toggleAutoSim.addEventListener('change', (e) => {
        updateSimulatorBackend({ active: e.target.checked });
    });
    
    elements.inputSpeed.addEventListener('input', (e) => {
        const val = parseInt(e.target.value);
        elements.labelSpeed.innerText = (val / 1000).toFixed(1) + 's';
    });
    elements.inputSpeed.addEventListener('change', (e) => {
        updateSimulatorBackend({ interval_ms: parseInt(e.target.value) });
    });

    elements.inputFraudRate.addEventListener('input', (e) => {
        const val = parseInt(e.target.value);
        elements.labelFraudRate.innerText = val + '%';
    });
    elements.inputFraudRate.addEventListener('change', (e) => {
        updateSimulatorBackend({ fraud_probability: parseInt(e.target.value) / 100 });
    });
    
    elements.btnTriggerNormal.addEventListener('click', () => triggerSingleSim(false));
    elements.btnTriggerFraud.addEventListener('click', () => triggerSingleSim(true));
    
    // Rule edits (dynamic updates on blur/change)
    const ruleElements = [
        elements.ruleAmountActive, elements.ruleAmountVal,
        elements.ruleMismatchActive, elements.ruleVelocityActive,
        elements.ruleVelocityVal, elements.ruleDeviceActive, elements.ruleMlVal
    ];
    
    ruleElements.forEach(el => {
        el.addEventListener('change', saveRulesFromUI);
    });
    
    // Form submission
    elements.checkoutForm.addEventListener('submit', handleManualCheckout);
    
    // Model Retraining
    elements.btnRetrain.addEventListener('click', handleRetrainModel);
    
    // Feed Reset
    elements.btnClearFeed.addEventListener('click', handleResetMetrics);
    
    // Drawer close
    elements.btnCloseDrawer.addEventListener('click', closeDrawer);
    elements.drawerOverlay.addEventListener('click', closeDrawer);
}

// Update Simulator Configuration on Backend
async function updateSimulatorBackend(diff) {
    try {
        const response = await fetch(API.simulatorConfig, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(diff)
        });
        const data = await response.json();
        appState.simulatorConfig = data.config;
        syncSimulatorConfigToUI(data.config);
    } catch (err) {
        console.error("Error updating simulator config:", err);
    }
}

// Update Rules on Backend
async function saveRulesFromUI() {
    const rules = {
        block_high_amount: elements.ruleAmountActive.checked,
        block_high_amount_threshold: parseFloat(elements.ruleAmountVal.value) || 5000,
        block_location_mismatch: elements.ruleMismatchActive.checked,
        block_high_velocity: elements.ruleVelocityActive.checked,
        block_high_velocity_threshold: parseInt(elements.ruleVelocityVal.value) || 4,
        block_high_risk_device: elements.ruleDeviceActive.checked,
        min_ml_threshold: parseFloat(elements.ruleMlVal.value) || 75
    };
    
    try {
        const response = await fetch(API.rules, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(rules)
        });
        const data = await response.json();
        appState.rules = data.rules;
    } catch (err) {
        console.error("Error saving rules:", err);
    }
}

// Simulator Loop Management
function startSimulatorLoop() {
    stopSimulatorLoop(); // Clear active first
    const interval = appState.simulatorConfig.interval_ms;
    appState.simulationInterval = setInterval(async () => {
        try {
            const response = await fetch(API.simulateNext);
            const transaction = await response.json();
            
            // Push to local array
            appState.transactions.unshift(transaction);
            if (appState.transactions.length > 200) appState.transactions.pop();
            
            renderTransactionsFeed();
            await refreshMetrics();
        } catch (err) {
            console.error("Error fetching simulated transaction:", err);
        }
    }, interval);
}

function stopSimulatorLoop() {
    if (appState.simulationInterval) {
        clearInterval(appState.simulationInterval);
        appState.simulationInterval = null;
    }
}

// Trigger single simulated transaction
async function triggerSingleSim(forceFraud) {
    try {
        const response = await fetch(`${API.simulateNext}?force_fraud=${forceFraud}`);
        const transaction = await response.json();
        
        appState.transactions.unshift(transaction);
        if (appState.transactions.length > 200) appState.transactions.pop();
        
        renderTransactionsFeed();
        await refreshMetrics();
    } catch (err) {
        console.error("Error triggering manual sim:", err);
    }
}

// Submit payment through Checkout form
async function handleManualCheckout(e) {
    e.preventDefault();
    
    // Set button loading state to guide user during cold starts
    const submitBtn = elements.checkoutForm.querySelector('button[type="submit"]');
    const originalBtnHTML = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<i class="lucide-loader animate-spin"></i> Processing...`;
    if (window.lucide) {
        window.lucide.createIcons();
    }
    
    const billing = elements.formCardCountry.value;
    const ip = elements.formIpCountry.value;
    const amount = parseFloat(elements.formAmount.value);
    
    // Map human selections to model values
    // Device risk: Desktop (0.1), Mobile (0.3), Safari (0.35), Tablet (0.2), Tor (0.9)
    let deviceRisk = 0.1;
    const devName = elements.formDevice.value;
    if (devName.includes("iOS")) deviceRisk = 0.2;
    else if (devName.includes("Safari")) deviceRisk = 0.35;
    else if (devName.includes("Tablet")) deviceRisk = 0.2;
    else if (devName.includes("Tor")) deviceRisk = 0.9;
    
    // Category risk: Grocery (0.15), Dining (0.2), Gas (0.35), Apparel (0.40), Electronics (0.75), Travel (0.8), Wallet (0.95)
    let categoryRisk = 0.15;
    const catName = elements.formCategory.value;
    if (catName.includes("Dining")) categoryRisk = 0.20;
    else if (catName.includes("Gas")) categoryRisk = 0.35;
    else if (catName.includes("Apparel")) categoryRisk = 0.40;
    else if (catName.includes("Electronics")) categoryRisk = 0.75;
    else if (catName.includes("Travel")) categoryRisk = 0.80;
    else if (catName.includes("Digital Wallet")) categoryRisk = 0.95;

    const txPayload = {
        amount: amount,
        time_of_day: parseFloat((new Date().getHours() + new Date().getMinutes()/60).toFixed(2)),
        card_holder_age: parseInt(elements.formAge.value),
        transaction_velocity: parseInt(elements.formVelocity.value),
        location_mismatch: billing !== ip ? 1 : 0,
        device_risk: deviceRisk,
        category_risk: categoryRisk,
        historical_fraud_rate: 0.015,  // default clean rate
        
        cardholder_name: elements.formName.value,
        card_number_masked: "4" + Math.floor(1000 + Math.random()*9000) + " **** **** " + Math.floor(1000 + Math.random()*9000),
        card_network: elements.formCardNetwork.value,
        card_country: billing,
        ip_country: ip,
        category: catName,
        device: devName,
        simulated_fraud: 0
    };
    
    try {
        const response = await fetch(API.predict, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(txPayload)
        });
        
        if (!response.ok) {
            throw new Error(`Server returned status ${response.status}`);
        }
        
        const data = await response.json();
        
        appState.transactions.unshift(data);
        if (appState.transactions.length > 200) appState.transactions.pop();
        
        renderTransactionsFeed();
        await refreshMetrics();
        
        // Open drawer on checkout submit to show results immediately!
        openTransactionDeepDive(data);
    } catch (err) {
        console.error("Error submitting manual prediction:", err);
        alert("Failed to process payment. The server might be booting up or encountering CORS issues. Please try again in a few seconds.");
    } finally {
        // Restore button state
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnHTML;
        if (window.lucide) {
            window.lucide.createIcons();
        }
    }
}

// Retrain model
async function handleRetrainModel() {
    elements.btnRetrain.disabled = true;
    elements.modelStatus.innerText = "Retraining in progress...";
    elements.modelStatus.parentElement.querySelector('.status-dot').className = "status-dot orange";
    
    try {
        const response = await fetch(API.retrain, { method: 'POST' });
        const data = await response.json();
        
        if (data.status === "success") {
            elements.modelStatus.innerText = "Active (RandomForest - Retrained)";
            elements.modelStatus.parentElement.querySelector('.status-dot').className = "status-dot green";
            alert("Model retrained successfully on new transaction distributions!");
        }
    } catch (err) {
        console.error("Failed retraining model:", err);
        elements.modelStatus.innerText = "Error active (RandomForest)";
        elements.modelStatus.parentElement.querySelector('.status-dot').className = "status-dot red";
    } finally {
        elements.btnRetrain.disabled = false;
    }
}

// Reset Session Metrics and Logs
async function handleResetMetrics() {
    if (!confirm("Are you sure you want to clear the transaction history and reset performance metrics?")) return;
    
    try {
        await fetch(API.reset, { method: 'POST' });
        appState.transactions = [];
        renderTransactionsFeed();
        await refreshMetrics();
        closeDrawer();
    } catch (err) {
        console.error("Failed resetting system metrics:", err);
    }
}

// Refresh metrics values on widgets
async function refreshMetrics() {
    try {
        const response = await fetch(API.metrics);
        const data = await response.json();
        appState.metrics = data;
        
        // Populate DOM elements
        elements.valProcessedVolume.innerText = '$' + data.total_processed_amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        elements.valProcessedCount.innerText = (data.true_positives + data.false_positives + data.true_negatives + data.false_negatives) + ' txs';
        
        elements.valSavings.innerText = '$' + data.fraud_savings_usd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        elements.valBlockedCount.innerText = (data.true_positives + data.false_positives) + ' blocked';
        
        elements.valAccuracy.innerText = data.accuracy.toFixed(1) + '%';
        elements.valF1.innerText = data.f1_score.toFixed(1) + '%';
        elements.valAlertRate.innerText = data.alert_rate.toFixed(1) + '% alert rate';
        
        elements.valPrecision.innerText = data.precision.toFixed(1) + '%';
        elements.valRecall.innerText = data.recall.toFixed(1) + '%';
        
        // Distribution stats
        elements.statCountApproved.innerText = data.true_negatives + data.false_negatives - data.suspicious_reviews;
        elements.statCountReview.innerText = data.suspicious_reviews;
        elements.statCountBlocked.innerText = data.true_positives + data.false_positives;
        
        // Update Chart distribution data
        distributionChart.data.datasets[0].data = [
            data.true_negatives + data.false_negatives - data.suspicious_reviews,
            data.suspicious_reviews,
            data.true_positives + data.false_positives
        ];
        distributionChart.update();
        
    } catch (err) {
        console.error("Error refreshing dashboard metrics:", err);
    }
}

// Render Auditor transaction feed
function renderTransactionsFeed() {
    if (appState.transactions.length === 0) {
        elements.streamContainer.innerHTML = `
            <div class="stream-placeholder">
                <i class="lucide-activity animate-pulse"></i>
                <p>Simulating audit logs... Toggle the simulator or execute manual checkouts to generate logs.</p>
            </div>
        `;
        return;
    }
    
    // Clear feed container
    elements.streamContainer.innerHTML = '';
    
    // Render list
    appState.transactions.forEach(item => {
        const tx = item.tx;
        const ev = item.evaluation;
        
        const itemDiv = document.createElement('div');
        const statusClass = ev.status.toLowerCase(); // approved, review, blocked
        itemDiv.className = `tx-item ${statusClass}`;
        
        itemDiv.innerHTML = `
            <div class="tx-item-left">
                <span class="tx-card-holder">${tx.cardholder_name}</span>
                <span class="tx-meta">
                    <span>${tx.card_number_masked}</span>
                    <span>•</span>
                    <span>${tx.category}</span>
                </span>
            </div>
            <div class="tx-item-right">
                <span class="tx-amount">$${tx.amount.toFixed(2)}</span>
                <span class="tx-badge ${statusClass}">${ev.status}</span>
            </div>
        `;
        
        // Handle click event to audit
        itemDiv.addEventListener('click', () => {
            openTransactionDeepDive(item);
        });
        
        elements.streamContainer.appendChild(itemDiv);
    });
}

// Drawer deep dive presentation
function openTransactionDeepDive(item) {
    appState.selectedTransaction = item;
    
    const tx = item.tx;
    const ev = item.evaluation;
    
    // Status and Score styling
    elements.auditDetailBadge.innerText = ev.status;
    elements.auditDetailBadge.className = `audit-status-badge ${ev.status.toLowerCase()}`;
    
    elements.auditDetailScore.innerText = ev.ml_score.toFixed(1) + '%';
    
    // Explain text
    elements.auditDetailDecision.innerText = ev.decision_reason;
    
    // Explanations bullets
    elements.auditDetailExplanations.innerHTML = '';
    if (ev.status === "APPROVED") {
        elements.auditDetailExplanations.className = "bullet-explanations no-alerts";
    } else {
        elements.auditDetailExplanations.className = "bullet-explanations";
    }
    
    ev.explanations.forEach(exp => {
        const li = document.createElement('li');
        li.innerText = exp;
        elements.auditDetailExplanations.appendChild(li);
    });
    
    // Cardholder diagnostics mapping
    elements.profileName.innerText = tx.cardholder_name;
    elements.profileCard.innerText = tx.card_number_masked;
    elements.profileNetwork.innerText = tx.card_network;
    elements.profileCardCountry.innerText = tx.card_country;
    elements.profileIpCountry.innerText = tx.ip_country;
    elements.profileCategory.innerText = tx.category;
    elements.profileDevice.innerText = tx.device;
    elements.profileVelocity.innerText = `${tx.transaction_velocity} txs / 15m`;
    elements.profileHistorical.innerText = `${(tx.historical_fraud_rate * 100).toFixed(1)}% alert rate`;
    
    // Render drivers chart inside drawer
    // Drivers mapping: amount, time_of_day, card_holder_age, transaction_velocity, location_mismatch, device_risk, category_risk, historical_fraud_rate
    const drivers = ev.risk_drivers;
    importanceChart.data.datasets[0].data = [
        drivers.amount || 0,
        drivers.time_of_day || 0,
        drivers.card_holder_age || 0,
        drivers.transaction_velocity || 0,
        drivers.location_mismatch || 0,
        drivers.device_risk || 0,
        drivers.category_risk || 0,
        drivers.historical_fraud_rate || 0
    ];
    importanceChart.update();
    
    // Open drawer classes
    elements.drawerOverlay.classList.add('active');
    elements.detailDrawer.classList.add('active');
}

function closeDrawer() {
    elements.drawerOverlay.classList.remove('active');
    elements.detailDrawer.classList.remove('active');
    appState.selectedTransaction = null;
}
