/* TED Scraper Frontend - Исправленная версия */

const CONFIG = {
    BACKEND_BASE_URL: window.location.origin,
    REQUEST_TIMEOUT: 30000
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

// Check Backend Status
async function checkBackendStatus() {
    try {
        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/search?page=1&limit=1`);
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
    
    document.getElementById('publication-date-from').value = fromDate.toISOString().split('T')[0];
    document.getElementById('publication-date-to').value = today.toISOString().split('T')[0];
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

    try {
        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/search`, {
            method: 'GET',  // FastAPI поддерживает GET с query params для Pydantic
            headers: { 'Content-Type': 'application/json' },
            timeout: CONFIG.REQUEST_TIMEOUT
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        currentSearchData = data;

        displayResults(data);
        updatePagination(data.total, 25);
        searchStatus.textContent = `Показаны ${data.notices.length} из ${data.total} результатов`;
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
    return {
        text: document.getElementById('text').value.trim() || null,
        publication_date_from: document.getElementById('publication-date-from').value || null,
        publication_date_to: document.getElementById('publication-date-to').value || null,
        country: document.getElementById('country').value.trim().toUpperCase() || null
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

// Change Page
window.changePage = function(page) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    performSearch();
};

// Utility Functions
function showLoading(show) {
    loadingSpinner.style.display = show ? 'block' : 'none';
    searchBtn.disabled = show;
}

function showError(message) {
    errorAlert.textContent = message;
    errorAlert.style.display = 'block';
}

function hideError() {
    errorAlert.style.display = 'none';
}
