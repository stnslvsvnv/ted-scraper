/* TED Scraper Frontend - Полная версия с forced past defaults для лотов и clear button */

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
    setDefaultDates();  // Вызов с past dates
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

// Set Default Dates (past for guaranteed lots)
function setDefaultDates() {
    const today = new Date();
    const fromDate = new Date(today.getFullYear(), 9, 1);  // 2024-10-01 (past month for many lots)
    const fromStr = fromDate.toISOString().split('T')[0];  // 2024-10-01
    const toStr = today.toISOString().split('T')[0];       // 2025-11-12

    if (elements.dateFrom) elements.dateFrom.value = fromStr;
    if (elements.dateTo) elements.dateTo.value = toStr;
    console.log('Default dates for lots:', fromStr, 'to', toStr, '— expect total >10000');
}

// Clear Form (for empty query with defaults)
function clearForm() {
    if (elements.textInput) elements.textInput.value = '';
    if (elements.countryInput) elements.countryInput.value = '';
    setDefaultDates();  // Keep past dates
    if (elements.pageSize) elements.pageSize.value = '25';
    currentPage = 1;
    console.log('Form cleared — searching with past defaults');
    performSearch();
}

// Check Backend Status
async function checkBackendStatus() {
    try {
        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/health`, { timeout: 5000 });
        if (response.ok) {
            if (elements.backendStatus) {
                elements.backendStatus.textContent = 'Online';
                elements.backendStatus.classList.remove('bg-danger');
                elements.backendStatus.classList.add('bg-success');
            }
            console.log('✓ Backend is online');
        } else {
            setBackendOffline();
        }
    } catch (error) {
        console.warn('Backend check failed:', error);
        setBackendOffline();
    }
    setTimeout(checkBackendStatus, 30000);  // Poll every 30s
}

function setBackendOffline() {
    if (elements.backendStatus) {
        elements.backendStatus.textContent = 'Offline';
        elements.backendStatus.classList.remove('bg-success');
        elements.backendStatus.classList.add('bg-danger');
    }
}

// Get form data (with forced defaults if empty)
function getSearchRequest() {
    const text = elements.textInput?.value?.trim() || null;
    let publicationDateFrom = elements.dateFrom?.value?.trim() || null;
    let publicationDateTo = elements.dateTo?.value?.trim() || null;
    const country = elements.countryInput?.value?.trim() || null;
    const limit = parseInt(elements.pageSize?.value || '25');

    // Force past broad if empty (avoid 0 total)
    if (!publicationDateFrom) publicationDateFrom = '2024-10-01';
    if (!publicationDateTo) publicationDateTo = new Date().toISOString().split('T')[0];

    return {
        filters: {
            text: text,
            publication_date_from: publicationDateFrom,
            publication_date_to: publicationDateTo,
            country: country
        },
        page: currentPage,
        limit: limit
    };
}

// Perform search
async function performSearch() {
    try {
        if (elements.searchBtn) elements.searchBtn.disabled = true;
        if (elements.loadingSpinner) elements.loadingSpinner.style.display = 'block';
        hideEmptyState();
        hideResults();
        hideError();
        showStatus('Поиск...');

        const request = getSearchRequest();
        console.log('Sending search request:', request);

        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request),
            timeout: CONFIG.REQUEST_TIMEOUT
        });

        console.log('Response status:', response.status);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();
        currentSearchData = data;
        console.log('Search results:', data);

        displayResults(data);

        if (elements.searchStatus) {
            elements.searchStatus.classList.remove('alert-warning');
            elements.searchStatus.classList.add('alert-success');
            elements.searchStatus.textContent = `${data.notices.length} результатов из ${data.total}`;
        }

    } catch (error) {
        console.error('Search error:', error);
        showError(`Ошибка поиска: ${error.message}`);
    } finally {
        if (elements.searchBtn) elements.searchBtn.disabled = false;
        if (elements.loadingSpinner) elements.loadingSpinner.style.display = 'none';
    }
}

// Display results
function displayResults(data) {
    if (!data.notices || data.notices.length === 0) {
        showNoResults();
        return;
    }

    if (elements.resultsContainer) elements.resultsContainer.style.display = 'block';
    if (elements.resultsTbody) {
        elements.resultsTbody.innerHTML = '';
        data.notices.forEach((notice) => {
            const row = document.createElement('tr');
            row.dataset.publicationNumber = notice.publication_number;
            const pubNum = notice.publication_number || 'N/A';
            const date = notice.publication_date ? new Date(notice.publication_date).toLocaleDateString('ru-RU') : '-';
            const title = notice.title || 'Нет заголовка';
            const buyer = notice.buyer || 'Неизвестный';
            const country = notice.country || 'Неизвестно';

            row.innerHTML = `
                <td>${pubNum}</td>
                <td>${title}</td>
                <td>${buyer}</td>
                <td>${country}</td>
                <td>${date}</td>
            `;
            elements.resultsTbody.appendChild(row);
        });
    }

    // Basic pagination (if total > limit)
    if (data.total > data.notices.length) {
        displayPagination(data.total, data.notices.length);
    }
}

// Display pagination
function displayPagination(total, perPage) {
    const paginationDiv = document.getElementById('pagination') || createPaginationDiv();
    paginationDiv.innerHTML = '';
    const totalPages = Math.ceil(total / perPage);
    for (let i = 1; i <= Math.min(5, totalPages); i++) {  // Show first 5 pages
        const btn = document.createElement('button');
        btn.classList.add('page-link');
        btn.dataset.page = i;
        btn.textContent = i;
        if (i === currentPage) btn.classList.add('active');
        btn.onclick = () => { currentPage = i; performSearch(); };
        paginationDiv.appendChild(btn);
    }
    if (totalPages > 5) {
        const ellipsis = document.createElement('span');
        ellipsis.textContent = '...';
        paginationDiv.appendChild(ellipsis);
        const lastBtn = document.createElement('button');
        lastBtn.classList.add('page-link');
        lastBtn.dataset.page = totalPages;
        lastBtn.textContent = totalPages;
        lastBtn.onclick = () => { currentPage = totalPages; performSearch(); };
        paginationDiv.appendChild(lastBtn);
    }
}

function createPaginationDiv() {
    const div = document.createElement('div');
    div.id = 'pagination';
    div.classList.add('pagination');
    if (elements.resultsContainer) elements.resultsContainer.appendChild(div);
    return div;
}

// Show no results
function showNoResults() {
    if (elements.emptyState) {
        elements.emptyState.innerHTML = `
            <p>Результаты не найдены.</p>
            <p>Попробуйте: <button type="button" onclick="clearForm()" class="btn btn-sm btn-outline-primary">Очистить фильтры</button> для последних 25, или расширьте даты с 2024-10-01. Добавьте text="computer" или country="DEU". Если 0 — проверьте API key в backend.</p>
        `;
        elements.emptyState.style.display = 'block';
    }
    if (elements.resultsContainer) elements.resultsContainer.style.display = 'none';
    if (elements.searchStatus) {
        elements.searchStatus.textContent = '0 результатов';
        elements.searchStatus.classList.add('alert-warning');
    }
}

// Show error
function showError(message) {
    if (elements.errorAlert) {
        elements.errorAlert.textContent = message;
        elements.errorAlert.style.display = 'block';
        elements.errorAlert.classList.add('alert-danger');
    }
    console.error('Error displayed:', message);
}

// Hide helpers
function hideEmptyState() {
    if (elements.emptyState) elements.emptyState.style.display = 'none';
}

function hideResults() {
    if (elements.resultsContainer) elements.resultsContainer.style.display = 'none';
}

function hideError() {
    if (elements.errorAlert) {
        elements.errorAlert.style.display = 'none';
        elements.errorAlert.classList.remove('alert-danger');
    }
}

function showStatus(message) {
    if (elements.searchStatus) {
        elements.searchStatus.textContent = message;
        elements.searchStatus.style.display = 'block';
        elements.searchStatus.classList.add('alert-info');
    }
}

// Optional: Show notice details (if backend has /notice/{id})
async function showNoticeDetails(publicationNumber) {
    try {
        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/notice/${publicationNumber}`);
        if (response.ok) {
            const details = await response.json();
            // Display modal or expand row
            console.log('Details:', details);
            alert(`Детали для ${publicationNumber}: ${JSON.stringify(details, null, 2)}`);
        }
    } catch (error) {
        console.error('Details error:', error);
    }
}
