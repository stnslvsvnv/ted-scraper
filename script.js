/* TED Scraper Frontend - Исправленная версия с POST */

const CONFIG = {
    BACKEND_BASE_URL: 'http://65.21.253.7:8846',  // Если порт другой, укажите вручную, напр. 'http://your-server:8846'
    REQUEST_TIMEOUT: 60000  // Увеличено для TED API
};

console.log('Backend URL:', CONFIG.BACKEND_BASE_URL);

// State
let currentSearchData = null;
let currentPage = 1;
let totalPages = 1;

// DOM Elements
const searchForm = document.getElementById('search-form');
const searchBtn = document.getElementById('search-btn');
const backendStatus = document.getElementById('backend-status');
const resultsContainer = document.getElementById('results-container');
const emptyState = document.getElementById('empty-state');
const loadingSpinner = document.getElementById('loading-spinner');
const errorAlert = document.getElementById('error-alert');
const searchStatus = document.getElementById('search-status');
const resultsList = document.getElementById('results-list');
const pagination = document.getElementById('pagination');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('TED Scraper Frontend loaded');
    setupEventListeners();
    checkBackendStatus();
    setDefaultDates();
});

// Setup Event Listeners
function setupEventListeners() {
    if (searchForm) {
        searchForm.addEventListener('submit', handleSearch);
    }
}

// Check Backend Status (простая проверка /)
async function checkBackendStatus() {
    try {
        const response = await fetch(CONFIG.BACKEND_BASE_URL + '/', { timeout: 5000 });
        if (response.ok) {
            backendStatus.textContent = 'Backend готов';
            backendStatus.className = 'status success';
        } else {
            backendStatus.textContent = 'Backend недоступен';
            backendStatus.className = 'status error';
        }
    } catch (error) {
        backendStatus.textContent = 'Backend недоступен: ' + error.message;
        backendStatus.className = 'status error';
    }
}

// Set Default Dates (last 30 days)
function setDefaultDates() {
    const today = new Date();
    const fromDate = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
    
    const fromStr = fromDate.toISOString().split('T')[0];
    const toStr = today.toISOString().split('T')[0];
    
    const fromInput = document.getElementById('publication-date-from');
    const toInput = document.getElementById('publication-date-to');
    if (fromInput) fromInput.value = fromStr;
    if (toInput) toInput.value = toStr;
}

// Handle Search
async function handleSearch(e) {
    e.preventDefault();
    currentPage = 1;
    await performSearch();
}

// Perform Search
async function performSearch() {
    const filters = getFiltersFromForm();
    const request = {
        filters: filters,
        page: currentPage,
        limit: 25
    };

    showLoading(true);
    hideError();
    resultsList.innerHTML = '';
    pagination.innerHTML = '';
    searchStatus.textContent = '';
    searchStatus.className = '';

    try {
        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/search`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(request),
            signal: AbortSignal.timeout(CONFIG.REQUEST_TIMEOUT)
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const data = await response.json();
        currentSearchData = data;

        displayResults(data);
        updatePagination(data.total, 25);
        searchStatus.textContent = `Показаны ${ (currentPage - 1) * 25 + data.notices.length } из ${data.total} результатов`;
        searchStatus.className = 'status info';

    } catch (error) {
        console.error('Search error:', error);
        showError('Ошибка поиска: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// Get Filters From Form
function getFiltersFromForm() {
    const text = document.getElementById('text');
    const fromDate = document.getElementById('publication-date-from');
    const toDate = document.getElementById('publication-date-to');
    const country = document.getElementById('country');
    
    return {
        text: text ? text.value.trim() || null : null,
        publication_date_from: fromDate ? fromDate.value || null : null,
        publication_date_to: toDate ? toDate.value || null : null,
        country: country ? country.value.trim().toUpperCase() || null : null
    };
}

// Display Results
function displayResults(data) {
    if (!data.notices || data.notices.length === 0) {
        emptyState.style.display = 'block';
        resultsContainer.style.display = 'none';
        return;
    }

    emptyState.style.display = 'none';
    resultsContainer.style.display = 'block';

    resultsList.innerHTML = data.notices.map(notice => `
        <div class="result-item">
            <h3>${notice.title || 'Без названия'}</h3>
            <p><strong>Номер публикации:</strong> ${notice.publication_number}</p>
            <p><strong>Дата публикации:</strong> ${notice.publication_date || 'Не указана'}</p>
            <p><strong>Покупатель:</strong> ${notice.buyer || 'Не указан'}</p>
            <p><strong>Страна:</strong> ${notice.country || 'Не указана'}</p>
        </div>
    `).join('');
}

// Update Pagination
function updatePagination(total, limit) {
    totalPages = Math.ceil(total / limit);
    if (totalPages <= 1) {
        pagination.style.display = 'none';
        return;
    }

    pagination.style.display = 'block';
    let paginationHtml = `
        <button onclick="changePage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>Предыдущая</button>
        <span>Страница ${currentPage} из ${totalPages}</span>
        <button onclick="changePage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>Следующая</button>
    `;
    pagination.innerHTML = paginationHtml;
}

// Change Page (глобальная для onclick)
window.changePage = function(page) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    performSearch();
};

// Utility Functions
function showLoading(show) {
    if (loadingSpinner) loadingSpinner.style.display = show ? 'block' : 'none';
    if (searchBtn) searchBtn.disabled = show;
}

function showError(message) {
    if (errorAlert) {
        errorAlert.textContent = message;
        errorAlert.style.display = 'block';
    }
}

function hideError() {
    if (errorAlert) errorAlert.style.display = 'none';
}

// Add Clear button in setupEventListeners
function setupEventListeners(elements) {
    elements.searchForm.addEventListener('submit', (e) => handleSearch(e, elements));
    // Clear button
    const clearBtn = document.createElement('button');
    clearBtn.type = 'button';
    clearBtn.textContent = 'Очистить фильтры';
    clearBtn.onclick = () => clearForm(elements);
    elements.searchForm.appendChild(clearBtn);
}

// Clear Form (for * query)
function clearForm(elements) {
    elements.searchForm.reset();
    setDefaultDates();  // Keep broader defaults
    currentPage = 1;
    performSearch(elements);  // Search with *
}

// Set Default Dates (2024-01-01 to today for results)
function setDefaultDates() {
    const today = new Date();
    const fromDate = new Date('2024-01-01');
    const toStr = today.toISOString().split('T')[0];
    const fromStr = '2024-01-01';
    
    document.getElementById('publication-date-from').value = fromStr;
    document.getElementById('publication-date-to').value = toStr;
    console.log('Defaults: 2024-01-01 to', toStr, '— expect total >1000');
}

// In showNoResults
function showNoResults(elements) {
    elements.emptyState.innerHTML = '<p>Нет результатов. <button onclick="clearForm(initElements())">Очистить фильтры</button> для последних 25, или расширьте даты/scope ALL.</p>';
    elements.emptyState.style.display = 'block';
    elements.resultsContainer.style.display = 'none';
}
