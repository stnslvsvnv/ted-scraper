/* TED Scraper Frontend – простая стабильная версия */

const CONFIG = {
    BACKEND_BASE_URL: window.location.origin,
    REQUEST_TIMEOUT: 30000,
    COUNTRIES: [
        {code: 'ALB', name: 'Albania'},
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

const el = {
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
    resultsList: document.getElementById('results-list'),
    pagination: document.getElementById('pagination'),
    emptyState: document.getElementById('empty-state'),
    loadingSpinner: document.getElementById('loading-spinner'),
    errorAlert: document.getElementById('error-alert'),
    searchStatus: document.getElementById('search-status')
};

document.addEventListener('DOMContentLoaded', () => {
    console.log('Frontend loaded');
    initCountries();
    setupEvents();
    checkBackendStatus();
    setDefaultDates();
    performSearch();
});

/* --- UI init --- */

function initCountries() {
    if (!el.countrySelect) return;
    el.countrySelect.innerHTML = CONFIG.COUNTRIES
        .map(c => `<option value="${c.code}">${c.code} — ${c.name}</option>`)
        .join('');

    // по умолчанию выделим 2–3 популярных
    ['DEU', 'FRA', 'ITA'].forEach(code => {
        const opt = el.countrySelect.querySelector(`option[value="${code}"]`);
        if (opt) opt.selected = true;
    });
}

function setupEvents() {
    if (el.searchForm) {
        el.searchForm.addEventListener('submit', e => {
            e.preventDefault();
            currentPage = 1;
            performSearch();
        });
    }

    if (el.searchBtn) {
        el.searchBtn.addEventListener('click', e => {
            e.preventDefault();
            currentPage = 1;
            performSearch();
        });
    }

    if (el.clearBtn) {
        el.clearBtn.addEventListener('click', () => {
            el.textInput.value = '';
            el.countrySelect.selectedIndex = -1;
            setDefaultDates();
            el.pageSize.value = '25';
            el.countrySearch.value = '';
            filterCountries('');
        });
    }

    if (el.countrySearch) {
        el.countrySearch.addEventListener('input', () => {
            filterCountries(el.countrySearch.value.trim().toLowerCase());
        });
    }
}

function setDefaultDates() {
    const today = new Date();
    const fromDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
    el.dateFrom.value = fromDate.toISOString().split('T')[0];
    el.dateTo.value = today.toISOString().split('T')[0];
}

function filterCountries(term) {
    const options = el.countrySelect.options;
    for (let i = 0; i < options.length; i++) {
        const text = options[i].text.toLowerCase();
        options[i].style.display = term ? (text.includes(term) ? '' : 'none') : '';
    }
}

/* --- backend status --- */

async function checkBackendStatus() {
    try {
        const res = await fetch(`${CONFIG.BACKEND_BASE_URL}/health`);
        if (res.ok) {
            el.backendStatus.textContent = 'Online';
            el.backendStatus.classList.remove('bg-danger');
            el.backendStatus.classList.add('bg-success');
        } else {
            setBackendOffline();
        }
    } catch {
        setBackendOffline();
    }
    setTimeout(checkBackendStatus, 30000);
}

function setBackendOffline() {
    el.backendStatus.textContent = 'Offline';
    el.backendStatus.classList.remove('bg-success');
    el.backendStatus.classList.add('bg-danger');
}

/* --- search --- */

function getSearchRequest() {
    const text = el.textInput.value.trim() || null;
    const publicationDateFrom = el.dateFrom.value.trim() || null;
    const publicationDateTo = el.dateTo.value.trim() || null;

    const selected = Array.from(el.countrySelect.options)
        .filter(o => o.selected && o.style.display !== 'none')
        .map(o => o.value);
    const country = selected.length ? selected.join(',') : null;

    const limit = parseInt(el.pageSize.value || '25');

    return {
        filters: { text, publication_date_from: publicationDateFrom, publication_date_to: publicationDateTo, country },
        page: currentPage,
        limit
    };
}

async function performSearch() {
    try {
        el.searchBtn.disabled = true;
        el.loadingSpinner.style.display = 'block';
        hideError();
        hideEmptyState();
        hideResults();
        showStatus('Поиск...');

        const req = getSearchRequest();
        console.log('Request:', req);

        const res = await fetch(`${CONFIG.BACKEND_BASE_URL}/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(req)
        });

        console.log('Response status:', res.status);

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }

        const data = await res.json();
        currentSearchData = data;
        renderResults(data);

        el.searchStatus.className = 'alert alert-success';
        el.searchStatus.textContent = `Найдено: ${data.total}`;
        el.searchStatus.style.display = 'block';

    } catch (e) {
        console.error('Search error:', e);
        showError(`Ошибка поиска: ${e.message}`);
    } finally {
        el.searchBtn.disabled = false;
        el.loadingSpinner.style.display = 'none';
    }
}

/* --- render --- */

function renderResults(data) {
    if (!data.notices || data.notices.length === 0) {
        showNoResults();
        return;
    }

    el.resultsContainer.style.display = 'block';
    el.resultsList.innerHTML = '';

    const table = document.createElement('table');
    table.className = 'table';
    table.innerHTML = `
        <thead>
            <tr>
                <th>Номер публикации</th>
                <th>Дата</th>
                <th>Заголовок</th>
                <th>Покупатель</th>
                <th>Страна</th>
            </tr>
        </thead>
        <tbody></tbody>
    `;

    const tbody = table.querySelector('tbody');

    data.notices.forEach(n => {
        const tr = document.createElement('tr');
        const date = n.publication_date ? new Date(n.publication_date).toLocaleDateString('ru-RU') : '-';
        tr.innerHTML = `
            <td>${n.publication_number || 'N/A'}</td>
            <td>${date}</td>
            <td>${n.title || 'Нет заголовка'}</td>
            <td>${n.buyer || 'Неизвестный'}</td>
            <td>${n.country || '-'}</td>
        `;
        tbody.appendChild(tr);
    });

    el.resultsList.appendChild(table);
    renderPagination(data.total, data.notices.length);
}

function renderPagination(total, perPage) {
    el.pagination.innerHTML = '';
    if (!total || total <= perPage) return;
    const totalPages = Math.ceil(total / perPage);
    const maxPages = Math.min(totalPages, 5);

    for (let i = 1; i <= maxPages; i++) {
        const btn = document.createElement('button');
        btn.className = 'page-link';
        btn.textContent = i;
        if (i === currentPage) btn.classList.add('active');
        btn.addEventListener('click', () => {
            currentPage = i;
            performSearch();
        });
        el.pagination.appendChild(btn);
    }
}

/* --- helpers --- */

function showNoResults() {
    el.emptyState.style.display = 'block';
    el.resultsContainer.style.display = 'none';
}

function showError(msg) {
    el.errorAlert.textContent = msg;
    el.errorAlert.className = 'alert alert-danger';
    el.errorAlert.style.display = 'block';
}

function hideError() { el.errorAlert.style.display = 'none'; }
function hideEmptyState() { el.emptyState.style.display = 'none'; }
function hideResults() { el.resultsContainer.style.display = 'none'; }

function showStatus(msg) {
    el.searchStatus.textContent = msg;
    el.searchStatus.className = 'alert alert-info';
    el.searchStatus.style.display = 'block';
}
