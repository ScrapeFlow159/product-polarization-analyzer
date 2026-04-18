// scripts.js - Updated for CSV Data Integration
// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// DOM Elements
const elements = {
    categorySelect: document.getElementById('categorySelect'),
    subcategorySelect: document.getElementById('subcategorySelect'),
    runAnalysisBtn: document.getElementById('runAnalysis'),
    loadingSpinner: document.getElementById('loadingSpinner'),
    resultsSection: document.getElementById('resultsSection'),
    resultsContent: document.getElementById('resultsContent'),
    productsTables: document.getElementById('productsTables'),
    etsyProductsBody: document.getElementById('etsyProductsBody'),
    darazProductsBody: document.getElementById('darazProductsBody')
};

// State
let currentState = {
    category: '',
    subcategory: ''
};

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 App initialized - CSV Data Version');
    setupEventListeners();
    checkBackendStatus();
});

// Enhanced backend status check
async function checkBackendStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/`);
        const data = await response.json();
        console.log('✅ Backend connected:', data);
        
        // Display data status in console
        if (data.data_status) {
            console.log(`📊 Data Status:`);
            console.log(`   Daraz: ${data.data_status.daraz_count} products (${data.data_status.daraz_loaded ? '✅ Loaded' : '❌ Not Loaded'})`);
            console.log(`   Etsy: ${data.data_status.etsy_count} products (${data.data_status.etsy_loaded ? '✅ Loaded' : '❌ Not Loaded'})`);
            console.log(`   CSV Data Used: ${data.data_status.csv_data_used ? '✅' : '❌'}`);
            
            // Show notification about data source
            if (data.data_status.csv_data_used) {
                showNotification('✅ Backend connected - Using real CSV data', 'success');
            } else {
                showNotification('⚠️ Backend connected but using sample data (CSV files not found)', 'warning');
            }
        }
    } catch (error) {
        console.error('❌ Backend connection failed:', error);
        showNotification('❌ Cannot connect to backend server. Please ensure the backend is running on port 8000.', 'error');
    }
}

// Setup event listeners
function setupEventListeners() {
    // Category selection
    elements.categorySelect.addEventListener('change', function(e) {
        currentState.category = e.target.value;
        
        if (currentState.category) {
            elements.subcategorySelect.disabled = false;
            populateSubcategories();
        } else {
            elements.subcategorySelect.disabled = true;
            currentState.subcategory = '';
            updateAnalysisButtonState();
        }
    });
    
    // Subcategory selection
    elements.subcategorySelect.addEventListener('change', function(e) {
        currentState.subcategory = e.target.value;
        updateAnalysisButtonState();
    });
    
    // Run analysis button
    elements.runAnalysisBtn.addEventListener('click', runAnalysis);
}

// Populate subcategories
function populateSubcategories() {
    const subcategories = {
        electronics: ["Earbuds", "Headphones", "Mobile Accessories"]
    };
    
    elements.subcategorySelect.innerHTML = '<option value="">-- Select Subcategory --</option>';
    
    if (currentState.category in subcategories) {
        subcategories[currentState.category].forEach(sub => {
            const option = document.createElement('option');
            option.value = sub.toLowerCase().replace(/[^a-z0-9]/g, '-');
            option.textContent = sub;
            elements.subcategorySelect.appendChild(option);
        });
    }
}

// Update analysis button state
function updateAnalysisButtonState() {
    const isValid = currentState.category && currentState.subcategory;
    elements.runAnalysisBtn.disabled = !isValid;
    
    if (isValid) {
        elements.runAnalysisBtn.innerHTML = '<i class="fas fa-chart-line"></i> Run CSV Data Analysis';
    } else {
        elements.runAnalysisBtn.innerHTML = 'Run Polarization Analysis';
    }
}

// Show loading
function showLoading() {
    elements.loadingSpinner.style.display = 'flex';
    elements.runAnalysisBtn.disabled = true;
    elements.runAnalysisBtn.innerHTML = '<div class="spinner"></div> Analyzing CSV Data...';
}

// Hide loading
function hideLoading() {
    elements.loadingSpinner.style.display = 'none';
    updateAnalysisButtonState();
}

// Enhanced notification system
function showNotification(message, type = 'info') {
    // Remove any existing notifications first
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(notification => notification.remove());
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <span>${message}</span>
        <button class="notification-close">×</button>
    `;
    
    // Add styles if not already added
    if (!document.getElementById('notification-styles')) {
        const style = document.createElement('style');
        style.id = 'notification-styles';
        style.textContent = `
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 20px;
                border-radius: 8px;
                color: white;
                z-index: 10000;
                display: flex;
                justify-content: space-between;
                align-items: center;
                min-width: 320px;
                max-width: 400px;
                box-shadow: 0 6px 16px rgba(0,0,0,0.2);
                animation: slideIn 0.3s ease-out;
                font-family: Arial, sans-serif;
                font-size: 14px;
            }
            .notification.info { 
                background: linear-gradient(135deg, #2563eb, #1d4ed8);
                border-left: 4px solid #3b82f6;
            }
            .notification.success { 
                background: linear-gradient(135deg, #10b981, #0da271);
                border-left: 4px solid #34d399;
            }
            .notification.warning { 
                background: linear-gradient(135deg, #f59e0b, #d97706);
                border-left: 4px solid #fbbf24;
            }
            .notification.error { 
                background: linear-gradient(135deg, #ef4444, #dc2626);
                border-left: 4px solid #f87171;
            }
            .notification-close {
                background: none;
                border: none;
                color: white;
                font-size: 24px;
                cursor: pointer;
                margin-left: 15px;
                padding: 0;
                line-height: 1;
                opacity: 0.8;
                transition: opacity 0.2s;
            }
            .notification-close:hover {
                opacity: 1;
            }
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOut {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(notification);
    
    // Add close functionality
    notification.querySelector('.notification-close').addEventListener('click', () => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    });
    
    // Auto-remove after 6 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }
    }, 6000);
}

// Main analysis function - Enhanced for CSV data
async function runAnalysis() {
    if (!currentState.category || !currentState.subcategory) {
        showNotification('Please select both category and subcategory', 'warning');
        return;
    }
    
    try {
        showLoading();
        hideResults();
        
        console.log(`📡 Sending analysis request for: ${currentState.category} - ${currentState.subcategory}`);
        
        // Call the updated API endpoint
        const response = await fetch(`${API_BASE_URL}/api/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                category: currentState.category,
                subcategory: currentState.subcategory,
                time_range: "latest"
            })
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status} - ${await response.text()}`);
        }
        
        const data = await response.json();
        console.log('📊 Analysis response received:', data);
        
        // Enhanced data validation
        if (!data.etsy || !data.daraz) {
            throw new Error('Invalid response format from server');
        }
        
        // Display results
        displayProductTables(data);
        displayResults(data);
        
        hideLoading();
        showNotification(`✅ Analysis complete! Processed ${data.data_analysis?.total_products_analyzed || 0} products`, 'success');
        
    } catch (error) {
        console.error('❌ Analysis error:', error);
        showNotification(`Analysis failed: ${error.message}`, 'error');
        hideLoading();
        
        // Fallback to sample data
        const sampleData = generateSampleData();
        displayProductTables(sampleData);
        displayResults(sampleData);
        showNotification('Using sample data for demonstration', 'warning');
    }
}

// Hide results
function hideResults() {
    elements.resultsSection.style.display = 'none';
    elements.productsTables.style.display = 'none';
}

// Enhanced product table display
function displayProductTables(data) {
    // Clear existing rows
    elements.etsyProductsBody.innerHTML = '';
    elements.darazProductsBody.innerHTML = '';
    
    // Calculate averages with safety checks
    const etsyScores = data.etsy.products?.map(p => p.final_score) || [];
    const darazScores = data.daraz.products?.map(p => p.final_score) || [];
    
    const etsyAvg = etsyScores.length > 0 ? 
        (etsyScores.reduce((a, b) => a + b, 0) / etsyScores.length).toFixed(3) : '0.000';
    const darazAvg = darazScores.length > 0 ? 
        (darazScores.reduce((a, b) => a + b, 0) / darazScores.length).toFixed(3) : '0.000';
    
    // Display Etsy products
    if (data.etsy.products && data.etsy.products.length > 0) {
        data.etsy.products.forEach((product, index) => {
            const row = createProductRow(product, index + 1, 'etsy');
            elements.etsyProductsBody.appendChild(row);
        });
        
        // Add average row for Etsy
        const etsyAvgRow = document.createElement('tr');
        etsyAvgRow.className = 'summary-row';
        etsyAvgRow.innerHTML = `
            <td colspan="6" style="text-align: right; padding-right: 15px;"><strong>Average Score:</strong></td>
            <td><span class="score-cell score-high">${etsyAvg}</span></td>
        `;
        elements.etsyProductsBody.appendChild(etsyAvgRow);
    } else {
        elements.etsyProductsBody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 20px; color: #666;">No Etsy products found</td></tr>`;
    }
    
    // Display Daraz products
    if (data.daraz.products && data.daraz.products.length > 0) {
        data.daraz.products.forEach((product, index) => {
            const row = createProductRow(product, index + 1, 'daraz');
            elements.darazProductsBody.appendChild(row);
        });
        
        // Add average row for Daraz
        const darazAvgRow = document.createElement('tr');
        darazAvgRow.className = 'summary-row';
        darazAvgRow.innerHTML = `
            <td colspan="6" style="text-align: right; padding-right: 15px;"><strong>Average Score:</strong></td>
            <td><span class="score-cell score-high">${darazAvg}</span></td>
        `;
        elements.darazProductsBody.appendChild(darazAvgRow);
    } else {
        elements.darazProductsBody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 20px; color: #666;">No Daraz products found</td></tr>`;
    }
    
    // Show tables section
    elements.productsTables.style.display = 'block';
    
    // Scroll to tables smoothly
    setTimeout(() => {
        elements.productsTables.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });
    }, 100);
}

// Enhanced results display with data source information
function displayResults(data) {
    elements.resultsSection.style.display = 'block';
    
    // Calculate CPI status
    const etsyStatus = getCPIStatus(data.etsy.cpi);
    const darazStatus = getCPIStatus(data.daraz.cpi);
    
    // Determine stable platform
    const stablePlatform = data.etsy.cpi < data.daraz.cpi ? 'Etsy' : 'Daraz';
    const unstablePlatform = stablePlatform === 'Etsy' ? 'Daraz' : 'Etsy';
    
    // Determine data source
    const usingCSVData = data.etsy.data_source === 'CSV' && data.daraz.data_source === 'CSV';
    const dataSourceText = usingCSVData ? 
        '✅ Using Real CSV Data' : 
        '⚠️ Using Sample Data (CSV files not found or failed to load)';
    
    const dataSourceColor = usingCSVData ? '#10b981' : '#f59e0b';
    
    // Get stability reason
    const stabilityReason = data.etsy.cpi < data.daraz.cpi 
        ? `Etsy has lower CPI (${data.etsy.cpi.toFixed(3)}) indicating more consistent product distribution` 
        : `Daraz has lower CPI (${data.daraz.cpi.toFixed(3)}) indicating more consistent product distribution`;
    
    // Calculate percentage difference
    const cpiDiff = Math.abs(data.etsy.cpi - data.daraz.cpi);
    const percentMoreStable = ((cpiDiff / Math.max(data.etsy.cpi, data.daraz.cpi)) * 100).toFixed(1);
    
    const html = `
        <div class="results-container">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="margin: 0;">📈 Polarization Analysis: ${currentState.category} - ${currentState.subcategory}</h3>
                <span style="background: ${dataSourceColor}20; color: ${dataSourceColor}; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid ${dataSourceColor}40;">
                    ${dataSourceText}
                </span>
            </div>
            
            <div class="platforms-summary">
                <div class="platform-card etsy">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                        <h4 style="margin: 0;">🛍️ Etsy Marketplace</h4>
                        <span class="cpi-indicator ${etsyStatus.class}">${etsyStatus.label}</span>
                    </div>
                    <p><strong>Products Analyzed:</strong> ${data.etsy.products?.length || 0}</p>
                    <p><strong>Average Product Score:</strong> ${(data.etsy.products?.reduce((sum, p) => sum + p.final_score, 0) / (data.etsy.products?.length || 1)).toFixed(3)}</p>
                    <p><strong>CPI Score:</strong> <span style="font-weight: bold; font-family: monospace;">${data.etsy.cpi.toFixed(3)}</span></p>
                    <p><strong>Data Source:</strong> ${data.etsy.data_source || 'Unknown'}</p>
                    <p><strong>Market Status:</strong> ${stablePlatform === 'Etsy' ? '<span style="color: #10b981; font-weight: bold;">STABLE MARKET</span>' : '<span style="color: #ef4444; font-weight: bold;">LESS STABLE</span>'}</p>
                </div>
                
                <div class="platform-card daraz">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                        <h4 style="margin: 0;">📦 Daraz Marketplace</h4>
                        <span class="cpi-indicator ${darazStatus.class}">${darazStatus.label}</span>
                    </div>
                    <p><strong>Products Analyzed:</strong> ${data.daraz.products?.length || 0}</p>
                    <p><strong>Average Product Score:</strong> ${(data.daraz.products?.reduce((sum, p) => sum + p.final_score, 0) / (data.daraz.products?.length || 1)).toFixed(3)}</p>
                    <p><strong>CPI Score:</strong> <span style="font-weight: bold; font-family: monospace;">${data.daraz.cpi.toFixed(3)}</span></p>
                    <p><strong>Data Source:</strong> ${data.daraz.data_source || 'Unknown'}</p>
                    <p><strong>Market Status:</strong> ${stablePlatform === 'Daraz' ? '<span style="color: #10b981; font-weight: bold;">STABLE MARKET</span>' : '<span style="color: #ef4444; font-weight: bold;">LESS STABLE</span>'}</p>
                </div>
            </div>
            
            <div class="stability-comparison">
                <h4 style="color: #0369a1; margin-bottom: 15px;">📊 Market Stability Assessment</h4>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                    <div style="background: #d1fae5; padding: 15px; border-radius: 8px;">
                        <strong style="color: #065f46;">Most Stable Platform</strong>
                        <p style="font-size: 24px; font-weight: bold; color: #065f46; margin: 10px 0;">${stablePlatform}</p>
                        <p style="font-size: 12px; color: #065f46;">CPI: ${stablePlatform === 'Etsy' ? data.etsy.cpi.toFixed(3) : data.daraz.cpi.toFixed(3)}</p>
                    </div>
                    
                    <div style="background: #fee2e2; padding: 15px; border-radius: 8px;">
                        <strong style="color: #991b1b;">Less Stable Platform</strong>
                        <p style="font-size: 24px; font-weight: bold; color: #991b1b; margin: 10px 0;">${unstablePlatform}</p>
                        <p style="font-size: 12px; color: #991b1b;">CPI: ${unstablePlatform === 'Etsy' ? data.etsy.cpi.toFixed(3) : data.daraz.cpi.toFixed(3)}</p>
                    </div>
                </div>
                
                <div style="background: #f8fafc; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                    <p><strong>📈 Key Metrics:</strong></p>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li><strong>CPI Difference:</strong> ${cpiDiff.toFixed(3)}</li>
                        <li><strong>Stability Advantage:</strong> ${stablePlatform} is ${percentMoreStable}% more stable</li>
                        <li><strong>Total Products Analyzed:</strong> ${data.data_analysis?.total_products_analyzed || (data.etsy.products?.length || 0) + (data.daraz.products?.length || 0)}</li>
                        <li><strong>Analysis Time:</strong> ${data.data_analysis?.analysis_timestamp ? new Date(data.data_analysis.analysis_timestamp).toLocaleString() : new Date().toLocaleString()}</li>
                    </ul>
                </div>
                
                <p><strong>🔍 Analysis:</strong> ${getStabilityAnalysis(data.etsy.cpi, data.daraz.cpi)}</p>
                
                <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #e5e7eb;">
                    <p style="font-size: 12px; color: #6b7280;">
                        <strong>Note:</strong> ${data.data_analysis?.note || 'Analysis based on product ratings, reviews, popularity, and price factors.'}
                    </p>
                </div>
            </div>
            
            <button id="exportBtn" class="export-button" onclick="exportAnalysis()" style="margin-top: 20px;">
                📥 Export Analysis Results
            </button>
        </div>
    `;
    
    elements.resultsContent.innerHTML = html;
    
    // Add export button styling
    if (!document.getElementById('export-button-styles')) {
        const style = document.createElement('style');
        style.id = 'export-button-styles';
        style.textContent = `
            .export-button {
                background: linear-gradient(135deg, #7c3aed, #2563eb);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                cursor: pointer;
                font-weight: bold;
                font-size: 14px;
                display: block;
                width: 100%;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .export-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
            }
        `;
        document.head.appendChild(style);
    }
}

// Enhanced product row creation
function createProductRow(product, rank, platform) {
    const row = document.createElement('tr');
    
    // Format data based on platform
    const price = platform === 'etsy' 
        ? `$${typeof product.price === 'number' ? product.price.toFixed(2) : '0.00'}`
        : `Rs ${typeof product.price === 'number' ? Math.round(product.price) : '0'}`;
    
    // Determine score color
    let scoreClass = 'score-medium';
    const score = product.final_score || 0;
    if (score >= 0.7) scoreClass = 'score-high';
    if (score < 0.5) scoreClass = 'score-low';
    
    // Truncate long product names with tooltip
    const productName = product.name ? product.name : `Product ${rank}`;
    const displayName = productName.length > 30 
        ? productName.substring(0, 27) + '...' 
        : productName;
    
    row.innerHTML = `
        <td style="text-align: center; font-weight: bold;">${rank}</td>
        <td title="${productName}" style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${displayName}</td>
        <td style="text-align: right; font-family: monospace;">${price}</td>
        <td style="text-align: center;"><span class="score-indicator">${(product.rating_norm || 0).toFixed(2)}</span></td>
        <td style="text-align: center;">${(product.review_norm || 0).toFixed(2)}</td>
        <td style="text-align: center;"><span class="score-indicator">${(product.popularity_norm || 0).toFixed(2)}</span></td>
        <td style="text-align: center;"><span class="score-cell ${scoreClass}">${score.toFixed(3)}</span></td>
    `;
    
    return row;
}

// Get CPI status label and class
function getCPIStatus(cpi) {
    if (cpi < 0.3) return { label: 'Very Stable', class: 'cpi-stable' };
    if (cpi < 0.5) return { label: 'Stable', class: 'cpi-stable' };
    if (cpi < 0.7) return { label: 'Polarized', class: 'cpi-polarized' };
    return { label: 'Highly Polarized', class: 'cpi-unstable' };
}

// Enhanced stability analysis text
function getStabilityAnalysis(etsyCPI, darazCPI) {
    const diff = Math.abs(etsyCPI - darazCPI);
    
    if (diff < 0.1) {
        return "Both markets show similar polarization levels with minimal stability difference. This suggests comparable market conditions and consumer behavior patterns across platforms.";
    } else if (diff < 0.2) {
        return "Moderate stability difference detected. One platform shows more consistent product distribution, suggesting different market dynamics or consumer expectations.";
    } else if (diff < 0.3) {
        return "Significant stability gap observed. The markets operate under fundamentally different structures, potentially indicating varied competitive landscapes or platform policies.";
    } else {
        return "Pronounced market divergence detected. The platforms serve distinct market segments with different product expectations, pricing strategies, and consumer bases.";
    }
}

// Enhanced sample data generation
function generateSampleData() {
    console.log('🔄 Generating sample data for demonstration');
    
    return {
        etsy: {
            platform: "Etsy",
            products: Array.from({length: 10}, (_, i) => ({
                name: `Sample Etsy Product ${i + 1}`,
                price: 30 + i * 15 + Math.random() * 10,
                rating_norm: 0.65 + Math.random() * 0.25,
                review_norm: 0.6 + Math.random() * 0.3,
                popularity_norm: 0.55 + Math.random() * 0.35,
                final_score: 0.55 + Math.random() * 0.35
            })),
            mean_features: {
                rating_norm: 0.75,
                review_norm: 0.65,
                price_norm: 0.4,
                popularity_norm: 0.7
            },
            cpi: 0.35 + Math.random() * 0.1,
            data_source: "Sample"
        },
        daraz: {
            platform: "Daraz",
            products: Array.from({length: 10}, (_, i) => ({
                name: `Sample Daraz Product ${i + 1}`,
                price: 800 + i * 350 + Math.random() * 200,
                rating_norm: 0.45 + Math.random() * 0.35,
                review_norm: 0.4 + Math.random() * 0.4,
                popularity_norm: 0.5 + Math.random() * 0.4,
                final_score: 0.4 + Math.random() * 0.4
            })),
            mean_features: {
                rating_norm: 0.6,
                review_norm: 0.5,
                price_norm: 0.3,
                popularity_norm: 0.6
            },
            cpi: 0.55 + Math.random() * 0.15,
            data_source: "Sample"
        },
        feature_contributions: {
            rating: 35.2,
            review: 28.5,
            price: 18.7,
            popularity: 17.6
        },
        overall_cpi: 0.45,
        stable_market: Math.random() > 0.5 ? "Etsy" : "Daraz",
        data_analysis: {
            total_products_analyzed: 20,
            csv_data_used: false,
            etsy_from_csv: false,
            daraz_from_csv: false,
            analysis_timestamp: new Date().toISOString(),
            note: "Using sample data - CSV files not found or backend unavailable"
        }
    };
}

// Enhanced export functionality
function exportAnalysis() {
    try {
        // Get the current analysis data (you might want to store this globally)
        const analysisData = {
            timestamp: new Date().toISOString(),
            category: currentState.category,
            subcategory: currentState.subcategory,
            platform_comparison: {
                etsy_cpi: document.querySelector('.platform-card.etsy')?.querySelector('span[style*="font-family: monospace"]')?.textContent || 'N/A',
                daraz_cpi: document.querySelector('.platform-card.daraz')?.querySelector('span[style*="font-family: monospace"]')?.textContent || 'N/A',
                stable_platform: document.querySelector('[style*="color: #065f46"]')?.textContent || 'N/A'
            },
            data_source: document.querySelector('[style*="border: 1px solid"]')?.textContent || 'Unknown'
        };
        
        const dataStr = JSON.stringify(analysisData, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
        
        const exportFileDefaultName = `polarization-analysis-${currentState.category || 'all'}-${new Date().toISOString().split('T')[0]}.json`;
        
        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', exportFileDefaultName);
        document.body.appendChild(linkElement);
        linkElement.click();
        document.body.removeChild(linkElement);
        
        showNotification('✅ Analysis exported successfully!', 'success');
    } catch (error) {
        console.error('Export error:', error);
        showNotification('Failed to export analysis', 'error');
    }
}

// Add some additional CSS for better display
document.addEventListener('DOMContentLoaded', function() {
    if (!document.getElementById('enhanced-styles')) {
        const style = document.createElement('style');
        style.id = 'enhanced-styles';
        style.textContent = `
            .score-indicator {
                display: inline-block;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: bold;
                background: #e5e7eb;
                color: #374151;
                min-width: 40px;
            }
            
            .score-cell {
                display: inline-block;
                padding: 6px 10px;
                border-radius: 6px;
                font-weight: bold;
                font-family: monospace;
                min-width: 60px;
            }
            
            .score-high {
                background: #d1fae5;
                color: #065f46;
                border: 1px solid #a7f3d0;
            }
            
            .score-medium {
                background: #fef3c7;
                color: #92400e;
                border: 1px solid #fde68a;
            }
            
            .score-low {
                background: #fee2e2;
                color: #991b1b;
                border: 1px solid #fecaca;
            }
            
            .cpi-indicator {
                display: inline-block;
                padding: 4px 10px;
                border-radius: 20px;
                font-size: 11px;
                font-weight: bold;
                text-transform: uppercase;
            }
            
            .cpi-stable {
                background: #d1fae5;
                color: #065f46;
            }
            
            .cpi-polarized {
                background: #fef3c7;
                color: #92400e;
            }
            
            .cpi-unstable {
                background: #fee2e2;
                color: #991b1b;
            }
        `;
        document.head.appendChild(style);
    }
});