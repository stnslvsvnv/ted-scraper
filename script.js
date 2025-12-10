/* TED Scraper Frontend + Slim Select */

const CONFIG = {
    BACKEND_BASE_URL: window.location.origin,
    REQUEST_TIMEOUT: 30000,
    COUNTRIES: [
        {code: 'ALB', name: 'Albania'},
        {code: 'AND', name: 'Andorra'},
        {code: 'AUT', name: 'Austria'},
        {code: 'BEL', name: 'Belgium'},
        {code: 'BGR', name: 'Bulgaria'},
        {code: 'CHE', name: 'Switzerland'},
        {code: 'CYP', name: 'Cyprus'},
        {code: 'CZE', name: 'Czechia'},
        {code: 'DEU', name: 'Germany'},
        {code: 'DNK', name: 'Denmark'},
        {code: 'ESP', name: 'Spain'},
        {code: 'EST', name: 'Estonia'},
        {code: 'FIN', name: 'Finland'},
        {code: 'FRA', name: 'France'},
        {code: 'GBR', name: 'United Kingdom'},
        {code: 'GRC', name: 'Greece'},
        {code: 'HRV', name: 'Croatia'},
        {code: 'HUN', name: 'Hungary'},
        {code: 'IRL', name: 'Ireland'},
        {code: 'ISL', name: 'Iceland'},
        {code: 'ITA', name: 'Italy'},
        {code: 'LIE', name: 'Liechtenstein'},
        {code: 'LTU', name: 'Lithuania'},
        {code: 'LUX', name: 'Luxembourg'},
        {code: 'LVA', name: 'Latvia'},
        {code: 'MLT', name: 'Malta'},
        {code: 'MNE', name: 'Montenegro'},
        {code: 'NLD', name: 'Netherlands'},
        {code: 'NOR', name: 'Norway'},
        {code: 'POL', name: 'Poland'},
        {code: 'PRT', name: 'Portugal'},
        {code: 'ROU', name: 'Romania'},
        {code: 'SRB', name: 'Serbia'},
        {code: 'SVK', name: 'Slovakia'},
        {code: 'SVN', name: 'Slovenia'},
        {code: 'SWE', name: 'Sweden'},
        {code: 'UKR', name: 'Ukraine'},
        {code: 'XKX', name: 'Kosovo'}
    ]
};

let currentSearchData = null;
let currentPage = 1;
let countrySlim = null;

const elements = {
    searchForm: document.getElementById('search-form'),
    textInput: document.getElementById('text'),
    dateFrom: document.getElementById('publication-date-from'),
    dateTo: document.getElementById('publication-date-to'),
    countrySelect: document.getElementById('country-select'),
    pageSize: document.getElementById('page-size'),
    searchBtn: document.getElementById('search-btn'),
    clearBtn: document.getElementById('clear-btn'),
    backendStatus: document.getElementById('backend-status'),
    resultsContainer: document.getElementById('results-container'),
    resultsTbody: document.getElementById('results-tbody'),
    emptyState: document.getElementById('empty-state'),
    loadingSpinner: document.getElementById('loading-spinner'),
    errorAlert: document.getElementById('error-alert'),
    searchStatus: document.getElementById('search-status')
};

document.addEventListener('DOMContentLoaded', () => {
    setupCountries();
    setupSlimSelect();
    setupEventListeners();
    checkBackendStatus();
    setDefaultDates();
});

// инициализация списка стран (опции <option>)
function setupCountries() {
    if (!elements.countrySelect) return;
    elements.countrySelect.innerHTML = CONFIG.COUNTRIES
        .map(c => `<option value="${c.code}">${c.code} — ${c.name}</option>`)
        .join('');
}

// инициализация Slim Select
function setupSlimSelect() {
    if (!elements.countrySelect) return;
    countrySlim = new SlimSelect({
        select: '#country-select',
        settings: {
            placeholderText: 'Выберите страны',
            searchPlaceholder: 'Поиск...',
            searchText: 'Ничего не найдено',
            closeOnSelect: false,
            hideSelected: true,
            allowDeselect: true
        }
    });

    // по умолчанию несколько популярных стран
    countrySlim.setSelected(['DEU', 'FRA', 'ITA', 'ESP', 'NLD']);
}

function setupEventListeners() {
    if (elements.searchForm) {
        elements.searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            currentPage = 1;
            performSearch();
        });
    }
    if (elements.clearBtn) {
        elements.clearBtn.addEventListener('click', clearForm);
    }
}

function setDefaultDates() {
    const today = new Date();
    const fromDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
    const fromStr = fromDate.toISOString().split('T')[0];
    const toStr = today.toISOString().split('T')[0];
    if (elements.dateFrom) elements.dateFrom.value = fromStr;
    if (elements.dateTo) elements.dateTo.value = toStr;
}

function clearForm() {
    if (elements.textInput) elements.textInput.value = '';
    if (countrySlim) countrySlim.setSelected([]);
    if (elements.pageSize) elements.pageSize.value = '25';
    setDefaultDates();
    currentPage = 1;
}

async function checkBackendStatus() {
    try {
        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/health`);
        if (response.ok) {
            elements.backendStatus.textContent = 'Online';
            elements.backendStatus.classList.remove('bg-danger', 'bg-secondary');
            elements.backendStatus.classList.add('bg-success');
        } else setBackendOffline();
    } catch {
        setBackendOffline();
    }
    setTimeout(checkBackendStatus, 30000);
}

function setBackendOffline() {
    elements.backendStatus.textContent = 'Offline';
    elements.backendStatus.classList.remove('bg-success', 'bg-secondary');
    elements.backendStatus.classList.add('bg-danger');
}

// формирование тела запроса
function getSearchRequest() {
    const selectedCountries = countrySlim ? countrySlim.getSelected() : [];
    return {
        filters: {
            text: elements.textInput?.value?.trim() || null,
            publication_date_from: elements.dateFrom?.value?.trim() || null,
            publication_date_to: elements.dateTo?.value?.trim() || null,
            country: selectedCountries.length ? selectedCountries.join(',') : null
        },
        page: currentPage,
        limit: parseInt(elements.pageSize?.value || '25')
    };
}

async function performSearch() {
    try {
        elements.searchBtn.disabled = true;
        elements.loadingSpinner.style.display = 'block';
        hideEmptyState(); hideResults(); hideError();
        showStatus('Поиск...');

        const request = getSearchRequest();
        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/search`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(request)
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();
        currentSearchData = data;
        displayResults(data);

        elements.searchStatus.classList.remove('alert-warning', 'alert-info');
        elements.searchStatus.classList.add('alert-success');
        elements.searchStatus.innerHTML = `Найдено: <strong>${data.total}</strong> результатов`;
        elements.searchStatus.style.display = 'block';

    } catch (e) {
        showError(`Ошибка поиска: ${e.message}`);
    } finally {
        elements.searchBtn.disabled = false;
        elements.loadingSpinner.style.display = 'none';
    }
}

function displayResults(data) {
    if (!data.notices || data.notices.length === 0) {
        showNoResults();
        return;
    }

    elements.resultsContainer.style.display = 'block';
    elements.resultsTbody.innerHTML = '';

    data.notices.forEach(n => {
        const row = document.createElement('tr');
        const pubNum = n.publication_number || 'N/A';
        const date = n.publication_date ? new Date(n.publication_date).toLocaleDateString('ru-RU') : '-';
        const title = n.title || 'Нет заголовка';
        const buyer = n.buyer || 'Неизвестный';
        const country = n.country || '-';
        row.innerHTML = `
            <td>${pubNum}</td>
            <td>${date}</td>
            <td>${title}</td>
            <td>${buyer}</td>
            <td>${country}</td>
        `;
        elements.resultsTbody.appendChild(row);
    });
}

function showNoResults() {
    elements.emptyState.style.display = 'block';
    elements.resultsContainer.style.display = 'none';
}

function showError(msg) {
    elements.errorAlert.textContent = msg;
    elements.errorAlert.style.display = 'block';
    elements.errorAlert.classList.add('alert-danger');
}

function hideEmptyState() { elements.emptyState.style.display = 'none'; }
function hideResults() { elements.resultsContainer.style.display = 'none'; }
function hideError() {
    elements.errorAlert.style.display = 'none';
    elements.errorAlert.classList.remove('alert-danger');
}
function showStatus(msg) {
    elements.searchStatus.textContent = msg;
    elements.searchStatus.style.display = 'block';
    elements.searchStatus.classList.remove('alert-success', 'alert-warning');
    elements.searchStatus.classList.add('alert-info');
}
