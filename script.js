/* TED Scraper Frontend – мультивыбор стран без библиотек */

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

let currentPage = 1;
let currentSearchData = null;
let selectedCountries = new Set();

const el = {
    searchForm: document.getElementById('search-form'),
    textInput: document.getElementById('text'),
    dateFrom: document.getElementById('publication-date-from'),
    dateTo: document.getElementById('publication-date-to'),
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
    searchStatus: document.getElementById('search-status'),
    countrySearch: document.getElementById('country-search'),
    countryDropdownList: document.getElementById('country-dropdown-list'),
    countryTags: document.getElementById('country-selected-tags')
};

document.addEventListener('DOMContentLoaded', () => {
    initCountryDropdown();
    setupEvents();
    checkBackendStatus();
    setDefaultDates();
    performSearch();
});

function setupEvents() {
    if (el.searchForm) {
        el.searchForm.addEventListener('submit', e => {
            e.preventDefault();
            currentPage = 1;
            performSearch();
        });
    }
    if (el.clearBtn) {
        el.clearBtn.addEventListener('click', () => {
            el.textInput.value = '';
            selectedCountries.clear();
            refreshCountryUI();
            setDefaultDates();
            el.pageSize.value = '25';
        });
    }
    if (el.countrySearch) {
        el.countrySearch.addEventListener('input', () => {
            filterCountryDropdown(el.countrySearch.value.trim().toLowerCase());
        });
    }
}

function setDefaultDates() {
    const today = new Date();
    const fromDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
    el.dateFrom.value = fromDate.toISOString().split('T')[0];
    el.dateTo.value = today.toISOString().split('T')[0];
}

/* ---------- мультиселект стран ---------- */

function initCountryDropdown() {
    el.countryDropdownList.innerHTML = '';
    CONFIG.COUNTRIES.forEach(c => {
        const item = document.createElement('label');
        item.className = 'country-item';
        item.innerHTML = `
            <input type="checkbox" value="${c.code}">
            <span class="country-code">${c.code}</span>
            <span class="country-name">${c.name}</span>
        `;
        const checkbox = item.querySelector('input');
        checkbox.addEventListener('change', () => {
            if (checkbox.checked) selectedCountries.add(c.code);
            else selectedCountries.delete(c.code);
            refreshCountryUI();
        });
        el.countryDropdownList.appendChild(item);
    });

    // по умолчанию DEU, FRA
    selectedCountries.add('DEU');
    selectedCountries.add('FRA');
    refreshCountryUI();
}

function filterCountryDropdown(term) {
    const items = el.countryDropdownList.querySelectorAll('.country-item');
    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(term) ? '' : 'none';
    });
}

function refreshCountryUI() {
    // Чекбоксы
    el.countryDropdownList.querySelectorAll('input[type="checkbox"]').forEach(ch => {
        ch.checked = selectedCountries.has(ch.value);
    });

    // Теги выбранных
    el.countryTags.innerHTML = '';
    if (selectedCountries.size === 0) {
        el.countryTags.innerHTML = '<span class="country-tag country-tag--empty">Страны не выбраны</span>';
        return;
    }
    CONFIG.COUNTRIES.forEach(c => {
        if (selectedCountries.has(c.code)) {
            const tag = document.createElement('span');
            tag.className = 'country-tag';
            tag.textContent = `${c.code} — ${c.name}`;
            tag.addEventListener('click', () => {
                selectedCountries.delete(c.code);
                refreshCountryUI();
            });
            el.countryTags.appendChild(tag);
        }
    });
}

/* ---------- backend статус ---------- */

async function checkBackendStatus() {
    try {
        const r = await fetch(`${CONFIG.BACKEND_BASE_URL}/health`);
        if (r.ok) {
            el.backendStatus.textContent = 'Online';
            el.backendStatus.classList.remove('bg-danger');
            el.backendStatus.classList.add('bg-success');
        } else setBackendOffline();
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

/* ---------- поиск ---------- */

function getSearchRequest() {
    const text = el.textInput.value.trim() || null;
    const publicationDateFrom = el.dateFrom.value.trim() || null;
    const publicationDateTo = el.dateTo.value.trim() || null;
    const country = selectedCountries.size ? Array.from(selectedCountries).join(',') : null;
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

        const request = getSearchRequest();
        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/search`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(request)
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();
        currentSearchData = data;
        renderResults(data);

        el.searchStatus.className = 'alert alert-success';
        el.searchStatus.textContent = `Найдено: ${data.total}`;
        el.searchStatus.style.display = 'block';

    } catch (e) {
        showError(`Ошибка поиска: ${e.message}`);
    } finally {
        el.searchBtn.disabled = false;
        el.loadingSpinner.style.display = 'none';
    }
}

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
        const dateStr = n.publication_date ? new Date(n.publication_date).toLocaleDateString('ru-RU') : '-';
        tr.innerHTML = `
            <td>${n.publication_number || 'N/A'}</td>
            <td>${dateStr}</td>
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
    for (let i = 1; i <= Math.min(totalPages, 5); i++) {
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

/* ---------- вспомогательные ---------- */

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
