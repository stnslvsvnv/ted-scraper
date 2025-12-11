/* TED Scraper Frontend – версия с правильными полями */

const CONFIG = {
    BACKEND_BASE_URL: window.location.origin,
    REQUEST_TIMEOUT: 30000
};

console.log('Backend URL:', CONFIG.BACKEND_BASE_URL);

let currentSearchData = null;
let currentPage = 1;

const elements = {
    searchForm: document.getElementById('search-form'),
    textInput: document.getElementById('text'),
    dateFrom: document.getElementById('publication-date-from'),
    dateTo: document.getElementById('publication-date-to'),
    countryInput: document.getElementById('country'),
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

document.addEventListener('DOMContentLoaded', () => {
    console.log('TED Scraper Frontend loaded');
    setupEventListeners();
    checkBackendStatus();
    setDefaultDates();
    performSearch();
});

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
}

function setDefaultDates() {
    const today = new Date();
    const fromDate = new Date(today.getFullYear(), 9, 1);
    const fromStr = fromDate.toISOString().split('T')[0];
    const toStr = today.toISOString().split('T')[0];
    if (elements.dateFrom) elements.dateFrom.value = fromStr;
    if (elements.dateTo) elements.dateTo.value = toStr;
}

async function checkBackendStatus() {
    try {
        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/health`, { timeout: 5000 });
        if (response.ok) {
            if (elements.backendStatus) {
                elements.backendStatus.textContent = 'Online';
                elements.backendStatus.classList.remove('bg-danger');
                elements.backendStatus.classList.add('bg-success');
            }
        } else {
            setBackendOffline();
        }
    } catch (error) {
        setBackendOffline();
    }
    setTimeout(checkBackendStatus, 30000);
}

function setBackendOffline() {
    if (elements.backendStatus) {
        elements.backendStatus.textContent = 'Offline';
        elements.backendStatus.classList.remove('bg-success');
        elements.backendStatus.classList.add('bg-danger');
    }
}

function getSearchRequest() {
    const text = elements.textInput?.value?.trim() || null;
    let publicationDateFrom = elements.dateFrom?.value?.trim() || null;
    let publicationDateTo = elements.dateTo?.value?.trim() || null;

    let country = null;
    if (elements.countryInput && elements.countryInput.options) {
        const selected = Array.from(elements.countryInput.options)
            .filter(o => o.selected && o.value)
            .map(o => o.value);
        if (selected.length) {
            country = selected.join(',');
        }
    }

    const limit = parseInt(elements.pageSize?.value || '25');

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

function displayResults(data) {
    if (!data.notices || data.notices.length === 0) {
        showNoResults();
        return;
    }
    if (elements.resultsContainer) elements.resultsContainer.style.display = 'block';
    if (!elements.resultsTbody) return;

    elements.resultsTbody.innerHTML = '';

    data.notices.forEach((notice) => {
        const row = document.createElement('tr');
        row.dataset.publicationNumber = notice.publication_number;

        const pubNum = notice.publication_number || 'N/A';
        const pubDate = notice.publication_date || '-';
        const deadline = notice.deadline_date || '-';
        const title = notice.title || 'Нет заголовка';

        let locationParts = [];
        if (notice.country) locationParts.push(notice.country);
        if (notice.city) locationParts.push(notice.city);
        if (notice.performance_city && notice.performance_city !== notice.city) {
            locationParts.push(`(${notice.performance_city})`);
        }
        const location = locationParts.join(' / ') || '-';

        row.innerHTML = `
            <td class="col-pubnum">${pubNum}</td>
            <td>${pubDate}</td>
            <td>${deadline}</td>
            <td class="col-title">${title}</td>
            <td>${location}</td>
        `;
        elements.resultsTbody.appendChild(row);
    });
}

function showNoResults() {
    if (elements.emptyState) elements.emptyState.style.display = 'block';
    if (elements.resultsContainer) elements.resultsContainer.style.display = 'none';
    if (elements.searchStatus) {
        elements.searchStatus.textContent = '0 результатов';
        elements.searchStatus.classList.add('alert-warning');
    }
}

function showError(message) {
    if (elements.errorAlert) {
        elements.errorAlert.textContent = message;
        elements.errorAlert.style.display = 'block';
        elements.errorAlert.classList.add('alert-danger');
    }
}

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
