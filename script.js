/* TED Scraper Frontend - Multi-country selector */

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

console.log('Backend URL:', CONFIG.BACKEND_BASE_URL);

// State
let currentSearchData = null;
let currentPage = 1;

// DOM Elements
const elements = {
    searchForm: document.getElementById('search-form'),
    textInput: document.getElementById('text'),
    dateFrom: document.getElementById('publication-date-from'),
    dateTo: document.getElementById('publication-date-to'),
    countrySelect: document.getElementById('country-select'),
    countrySearch: document.getElementById('country-search'),
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

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('TED Scraper Frontend loaded');
    setupEventListeners();
    setupCountries();
    checkBackendStatus();
    setDefaultDates();
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

    if (elements.clearBtn) {
        elements.clearBtn.addEventListener('click', clearForm);
    }

    if (elements.countrySearch) {
        elements.countrySearch.addEventListener('input', filterCountries);
    }
}

// Setup Countries Dropdown
function setupCountries() {
    if (!elements.countrySelect) return;
    
    elements.countrySelect.innerHTML = CONFIG.COUNTRIES.map(country => 
        `<option value="${country.code}">${country.code} - ${country.name}</option>`
    ).join('');
    
    // Выделяем популярные страны по умолчанию
    setTimeout(() => {
        const popular = ['DEU', 'FRA', 'ITA', 'ESP', 'NLD'];
        popular.forEach(code => {
            const option = elements.countrySelect.querySelector(`option[value="${code}"]`);
            if (option) option.selected = true;
        });
    }, 100);
}

// Filter Countries
function filterCountries() {
    const searchTerm = elements.countrySearch.value.toLowerCase();
    const options = elements.countrySelect.options;
    
    for (let i = 0; i < options.length; i++) {
        const option = options[i];
        const matches = option.text.toLowerCase().includes(searchTerm);
        option.style.display = matches ? '' : 'none';
    }
}

// Set Default Dates
function setDefaultDates() {
    const today = new Date();
    const fromDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
    const fromStr = fromDate.toISOString().split('T')[0];
    const toStr = today.toISOString().split('T')[0];
    
    if (elements.dateFrom) elements.dateFrom.value = fromStr;
    if (elements.dateTo) elements.dateTo.value = toStr;
}

// Clear Form
function clearForm() {
    if (elements.textInput) elements.textInput.value = '';
    if (elements.countrySelect) Array.from(elements.countrySelect.options).forEach(opt => opt.selected = false);
    if (elements.countrySearch) elements.countrySearch.value = '';
    if (elements.pageSize) elements.pageSize.value = '25';
    setDefaultDates();
    currentPage = 1;
    filterCountries(); // Reset filter
    console.log('Form cleared');
}

// Check Backend Status
async function checkBackendStatus() {
    try {
        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/health`);
        if (response.ok) {
            if (elements.backendStatus) {
                elements.backendStatus.textContent = 'Online';
                elements.backendStatus.classList.remove('bg-danger', 'bg-secondary');
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
        elements.backendStatus.classList.remove('bg-success', 'bg-secondary');
        elements.backendStatus.classList.add('bg-danger');
    }
}

// Get form data
function getSearchRequest() {
    const selectedCountries = Array.from(elements.countrySelect.selectedOptions).map(opt => opt.value);
    const countryList = selectedCountries.join(',');
    
    return {
        filters: {
            text: elements.textInput?.value?.trim() || null,
            publication_date_from: elements.dateFrom?.value?.trim() || null,
            publication_date_to: elements.dateTo?.value?.trim() || null,
            country: countryList || null
        },
        page: currentPage,
        limit: parseInt(elements.pageSize?.value || '25')
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
            body: JSON.stringify(request)
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();
        currentSearchData = data;
        
        console.log('Search results:', data);
        displayResults(data);
        
        if (elements.searchStatus) {
            elements.searchStatus.classList.remove('alert-warning', 'alert-info');
            elements.searchStatus.classList.add('alert-success');
            elements.searchStatus.innerHTML = `Найдено: <strong>${data.total}</strong> результатов`;
            elements.searchStatus.style.display = 'block';
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

    if (elements.resultsContainer) {
        elements.resultsContainer.style.display = 'block';
    }

    if (elements.resultsTbody) {
        elements.resultsTbody.innerHTML = '';
        
        data.notices.forEach((notice) => {
            const row = document.createElement('tr');
            
            const pubNum = notice.publication_number || 'N/A';
            const date = notice.publication_date ? 
                new Date(notice.publication_date).toLocaleDateString('ru-RU') : '-';
            const title = notice.title || 'Нет заголовка';
            const buyer = notice.buyer || 'Неизвестный';
            const country = notice.country || '-';

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
}

// Show no results
function showNoResults() {
    if (elements.emptyState) {
        elements.emptyState.style.display = 'block';
    }
    if (elements.resultsContainer) {
        elements.resultsContainer.style.display = 'none';
    }
}

// Show error
function showError(message) {
    if (elements.errorAlert) {
        elements.errorAlert.textContent = message;
        elements.errorAlert.style.display = 'block';
        elements.errorAlert.classList.add('alert-danger');
    }
}

// Hide helpers
function hideEmptyState() { if (elements.emptyState) elements.emptyState.style.display = 'none'; }
function hideResults() { if (elements.resultsContainer) elements.resultsContainer.style.display = 'none'; }
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
        elements.searchStatus.classList.remove('alert-success', 'alert-warning');
        elements.searchStatus.classList.add('alert-info');
    }
}
