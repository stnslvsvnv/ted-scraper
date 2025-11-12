/* TED Scraper Frontend - Полная версия с past defaults для лотов и clear button */

const CONFIG = {
    BACKEND_BASE_URL: window.location.origin,
    REQUEST_TIMEOUT: 30000
};

console.log('Backend URL:', CONFIG.BACKEND_BASE_URL);

// State
let currentSearchData = null;
let currentPage = 1;

// DOM Elements (предполагаемые ID из index.html; скорректируйте если нужно)
const elements = {
    searchForm: document.getElementById('search-form'),
    textInput: document.getElementById('text'),  // ID для text search
    dateFrom: document.getElementById('publication-date-from'),
    dateTo: document.getElementById('publication-date-to'),
    countryInput: document.getElementById('country'),  // ID для country
    pageSize: document.getElementById('page-size') || { value: '25' },
    searchBtn: document.getElementById('search-btn'),
    backendStatus: document.getElementById('backend-status'),
    resultsContainer: document.getElementById('results-container'),
    resultsTbody: document.getElementById('results-tbody'),
    emptyState: document.getElementById('empty-state'),
    loadingSpinner: document.getElementById('loading-spinner'),
    errorAlert: document.getElementById('error-alert'),
    searchStatus: document.getElementById('search-status')
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('TED Scraper Frontend loaded');
    setupEventListeners();
    checkBackendStatus();
    setDefaultDates();  // Вызов обновлённой функции здесь
    // Initial search with defaults
    performSearch();
});

// Setup Event Listeners
function setupEventListeners() {
    if (elements.searchForm) {
        elements.searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            currentPage = 1;
            performSearch();
        });
    }
    if (elements.searchBtn) {
        elements.searchBtn.addEventListener('click', (e) => {
            e.preventDefault();
            currentPage = 1;
            performSearch();
        });
    }

    // Clear button
    const clearBtn = document.createElement('button');
    clearBtn.type = 'button';
    clearBtn.textContent = 'Очистить фильтры';
    clearBtn.classList.add('btn', 'btn-secondary', 'ms-2');
    clearBtn.onclick = () => clearForm();
    if (elements.searchForm) {
        elements.searchForm.appendChild(clearBtn);  // Add to form
    }

    // Pagination clicks
    document.addEventListener('click', (e) => {
        if (e.target.closest('.page-link')) {
            e.preventDefault();
            const page = parseInt(e.target.dataset.page);
            if (!isNaN(page)) {
                currentPage = page;
                performSearch();
            }
        }
    });

    // Row details click (if needed)
    document.addEventListener('click', (e) => {
        if (e.target.closest('tbody tr')) {
            const row = e.target.closest('tbody tr');
            const pubNum = row.dataset.publicationNumber;
            if (pubNum) {
                console.log('View details for:', pubNum);  // Expand if needed
                // showNoticeDetails(pubNum);  // Implement if API has /notice/{id}
            }
        }
    });
}

// Set Default Dates (past for guaranteed lots) — ОБНОВЛЁННАЯ ФУНКЦИЯ ЗДЕСЬ
function setDefaultDates() {
    const today = new Date();
    const fromDate = new Date(today.getFullYear(), 9, 1);  // 2024-10-01 (past month for many lots)
    const fromStr = fromDate.toISOString().split('T')[0];  // 2024-10-01
    const toStr = today.toISOString().split('T')[0];       // 2025-11-12

    if (elements.dateFrom) elements.dateFrom.value = fromStr;
    if (elements.dateTo) elements.dateTo.value = toStr;
    console.log('Default dates for lots:', fromStr, 'to', toStr, '— expect total >10000');
}

// Clear Form (for * query)
function clear
