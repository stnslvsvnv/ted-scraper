/* TED Scraper Frontend JavaScript */

// Configuration
const CONFIG = {
    BACKEND_BASE_URL: 'http://localhost:8847',
    REQUEST_TIMEOUT: 30000
};

// State
let currentSearchData = null;
let currentPage = 1;
let currentSearchQuery = null;

// DOM Elements
const searchForm = document.getElementById('search-form');
const searchBtn = document.getElementById('search-btn');
const backendStatus = document.getElementById('backend-status');
const emptyState = document.getElementById('empty-state');
const resultsContainer = document.getElementById('results-container');
const loadingSpinner = document.getElementById('loading-spinner');
const errorAlert = document.getElementById('error-alert');
const searchStatus = document.getElementById('search-status');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('TED Scraper Frontend loaded');
    setupEventListeners();
    checkBackendStatus();
    setDefaultDates();
});

// Setup Event Listeners
function setupEventListeners() {
    searchBtn.addEventListener('click', performSearch);
    searchForm.addEventListener('reset', resetSearch);

    // Toggle sections
    document.querySelectorAll('.toggle-section').forEach(el => {
        el.addEventListener('click', (e) => {
            e.preventDefault();
            const section = el.dataset.section;
            const content = el.closest('.mb-4').querySelector('.section-content');
            const isCollapsed = content.style.display === 'none';
            
            content.style.display = isCollapsed ? 'block' : 'none';
            el.dataset.collapsed = isCollapsed ? 'false' : 'true';
            el.querySelector('i').style.transform = isCollapsed ? 'rotate(0deg)' : 'rotate(-90deg)';
        });
    });

    // Pagination click
    document.addEventListener('click', (e) => {
        if (e.target.closest('.page-link')) {
            e.preventDefault();
            const page = e.target.dataset.page;
            if (page && currentSearchQuery) {
                currentPage = parseInt(page);
                performSearch();
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        }
    });

    // Row click for details
    document.addEventListener('click', (e) => {
        const row = e.target.closest('tbody tr');
        if (row) {
            const publicationNumber = row.dataset.publicationNumber;
            if (publicationNumber) {
                showNoticeDetails(publicationNumber);
            }
        }
    });
}

// Set default dates
function setDefaultDates() {
    const toDate = new Date();
    const fromDate = new Date();
    fromDate.setFullYear(fromDate.getFullYear() - 1);

    document.getElementById('pub-date-to').valueAsDate = toDate;
    document.getElementById('pub-date-from').valueAsDate = fromDate;
}

// Check Backend Status
async function checkBackendStatus() {
    try {
        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/health`, {
            timeout: 5000
        });
        
        if (response.ok) {
            backendStatus.textContent = 'Online';
            backendStatus.classList.remove('bg-danger');
            backendStatus.classList.add('bg-success');
            console.log('✓ Backend is online');
        } else {
            setBackendOffline();
        }
    } catch (error) {
        console.warn('Backend check failed:', error);
        setBackendOffline();
    }

    // Check every 30 seconds
    setTimeout(checkBackendStatus, 30000);
}

function setBackendOffline() {
    backendStatus.textContent = 'Offline';
    backendStatus.classList.remove('bg-success');
    backendStatus.classList.add('bg-danger');
}

// Get form data
function getSearchFilters() {
    return {
        full_text: getInputValue('full-text') || null,
        cpv_codes: getArrayValue('cpv-codes'),
        buyer_countries: getArrayValue('buyer-countries'),
        publication_date_from: document.getElementById('pub-date-from').value || null,
        publication_date_to: document.getElementById('pub-date-to').value || null,
        min_value: getNumberValue('min-value'),
        max_value: getNumberValue('max-value'),
    };
}

function getInputValue(id) {
    const val = document.getElementById(id).value.trim();
    return val ? val : null;
}

function getNumberValue(id) {
    const val = parseFloat(document.getElementById(id).value);
    return isNaN(val) ? null : val;
}

function getArrayValue(id) {
    const val = document.getElementById(id).value.trim();
    if (!val) return null;
    return val.split(',').map(v => v.trim()).filter(v => v);
}

// Perform search
async function performSearch() {
    try {
        // Disable button and show loading
        searchBtn.disabled = true;
        loadingSpinner.style.display = 'block';
        emptyState.style.display = 'none';
        resultsContainer.style.display = 'none';
        errorAlert.style.display = 'none';
        searchStatus.style.display = 'block';
        
        // Update status
        document.getElementById('status-text').textContent = '🔍 Searching...';

        // Build request
        const filters = getSearchFilters();
        const pageSize = parseInt(document.getElementById('page-size').value);
        
        const request = {
            filters,
            page: currentPage,
            page_size: pageSize,
            scope: document.getElementById('scope').value,
            sort_column: document.getElementById('sort-column').value,
            sort_order: document.getElementById('sort-order').value
        };

        currentSearchQuery = request;

        console.log('Sending search request:', request);

        // Send request
        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(request),
            timeout: CONFIG.REQUEST_TIMEOUT
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Search failed');
        }

        const data = await response.json();
        currentSearchData = data;

        console.log('Search results:', data);

        // Display results
        displayResults(data);
        document.getElementById('status-text').textContent = 
            `✓ Found ${data.total_notices} results`;
        searchStatus.classList.remove('alert-warning');
        searchStatus.classList.add('alert-success');

    } catch (error) {
        console.error('Search error:', error);
        showError(`Search failed: ${error.message}`);
        document.getElementById('status-text').textContent = 'Search error';
    } finally {
        searchBtn.disabled = false;
        loadingSpinner.style.display = 'none';
    }
}

// Display results
function displayResults(data) {
    const tbody = document.getElementById('results-tbody');
    tbody.innerHTML = '';

    if (!data.notices || data.notices.length === 0) {
        emptyState.style.display = 'block';
        emptyState.innerHTML = `
            <i class="fas fa-inbox text-muted" style="font-size: 3rem;"></i>
            <h5 class="mt-3 text-muted">No results found</h5>
            <p class="text-muted">Try adjusting your search criteria</p>
        `;
        resultsContainer.style.display = 'none';
        return;
    }

    // Populate table
    data.notices.forEach((notice, index) => {
        const row = document.createElement('tr');
        row.dataset.publicationNumber = notice.publication_number;
        row.dataset.index = index;
        
        const estimatedValue = notice.estimated_value 
            ? `€${formatNumber(notice.estimated_value)}`
            : '-';

        const cpvCodes = notice.cpv_codes && notice.cpv_codes.length > 0
            ? notice.cpv_codes.slice(0, 1).join(', ')
            : '-';

        row.innerHTML = `
            <td title="${notice.publication_number}">
                <a href="#" onclick="return false" style="cursor: pointer;">
                    ${notice.publication_number}
                </a>
            </td>
            <td title="${notice.publication_date}">
                ${formatDate(notice.publication_date)}
            </td>
            <td title="${notice.title || 'N/A'}">
                <strong>${truncate(notice.title || 'N/A', 50)}</strong>
            </td>
            <td title="${notice.buyer_name || 'N/A'}">
                ${truncate(notice.buyer_name || 'N/A', 30)}
            </td>
            <td>${notice.country || '-'}</td>
            <td>${cpvCodes}</td>
            <td>${estimatedValue}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="return false;" title="View details">
                    <i class="fas fa-external-link-alt"></i>
                </button>
            </td>
        `;
        
        tbody.appendChild(row);
    });

    // Update pagination info
    document.getElementById('showing-count').textContent = 
        Math.min(data.page_size, data.notices.length);
    document.getElementById('total-count').textContent = data.total_notices;
    document.getElementById('current-page').textContent = data.current_page;
    document.getElementById('total-pages').textContent = data.total_pages;

    // Generate pagination
    generatePagination(data);

    // Show results
    resultsContainer.style.display = 'block';
}

// Generate pagination
function generatePagination(data) {
    const paginationContainer = document.getElementById('pagination-container');
    const pagination = document.getElementById('pagination');
    pagination.innerHTML = '';

    const totalPages = data.total_pages;
    const currentPage = data.current_page;
    const maxPagesToShow = 7;

    if (totalPages <= 1) {
        paginationContainer.style.display = 'none';
        return;
    }

    paginationContainer.style.display = 'block';

    // Previous button
    if (currentPage > 1) {
        const li = document.createElement('li');
        li.className = 'page-item';
        li.innerHTML = `<a class="page-link" href="#" data-page="${currentPage - 1}">← Previous</a>`;
        pagination.appendChild(li);
    }

    // Page numbers
    let startPage = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2));
    let endPage = Math.min(totalPages, startPage + maxPagesToShow - 1);
    
    if (endPage - startPage < maxPagesToShow - 1) {
        startPage = Math.max(1, endPage - maxPagesToShow + 1);
    }

    if (startPage > 1) {
        const li = document.createElement('li');
        li.className = 'page-item';
        li.innerHTML = `<a class="page-link" href="#" data-page="1">1</a>`;
        pagination.appendChild(li);

        if (startPage > 2) {
            const li = document.createElement('li');
            li.className = 'page-item disabled';
            li.innerHTML = `<span class="page-link">...</span>`;
            pagination.appendChild(li);
        }
    }

    for (let page = startPage; page <= endPage; page++) {
        const li = document.createElement('li');
        li.className = page === currentPage ? 'page-item active' : 'page-item';
        li.innerHTML = `<a class="page-link" href="#" data-page="${page}">${page}</a>`;
        pagination.appendChild(li);
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            const li = document.createElement('li');
            li.className = 'page-item disabled';
            li.innerHTML = `<span class="page-link">...</span>`;
            pagination.appendChild(li);
        }

        const li = document.createElement('li');
        li.className = 'page-item';
        li.innerHTML = `<a class="page-link" href="#" data-page="${totalPages}">${totalPages}</a>`;
        pagination.appendChild(li);
    }

    // Next button
    if (currentPage < totalPages) {
        const li = document.createElement('li');
        li.className = 'page-item';
        li.innerHTML = `<a class="page-link" href="#" data-page="${currentPage + 1}">Next →</a>`;
        pagination.appendChild(li);
    }
}

// Show notice details
async function showNoticeDetails(publicationNumber) {
    try {
        const modal = new bootstrap.Modal(document.getElementById('notice-modal'));
        const modalBody = document.getElementById('modal-body');
        
        document.getElementById('modal-title').textContent = `Loading ${publicationNumber}...`;
        modalBody.innerHTML = '<div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div>';
        modal.show();

        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/notice/${publicationNumber}`);
        
        if (!response.ok) {
            throw new Error('Failed to fetch notice details');
        }

        const notice = await response.json();

        // Format content
        const html = `
            <div class="notice-details">
                <div class="notice-details-row">
                    <div class="notice-details-label">Publication Number</div>
                    <div class="notice-details-value">${notice.publication_number}</div>
                </div>
                <div class="notice-details-row">
                    <div class="notice-details-label">Date</div>
                    <div class="notice-details-value">${formatDate(notice.publication_date)}</div>
                </div>
                <div class="notice-details-row">
                    <div class="notice-details-label">Title</div>
                    <div class="notice-details-value"><strong>${notice.title || 'N/A'}</strong></div>
                </div>
                <div class="notice-details-row">
                    <div class="notice-details-label">Buyer</div>
                    <div class="notice-details-value">${notice.buyer_name || 'N/A'}</div>
                </div>
                <div class="notice-details-row">
                    <div class="notice-details-label">Country</div>
                    <div class="notice-details-value">${notice.country || 'N/A'}</div>
                </div>
                <div class="notice-details-row">
                    <div class="notice-details-label">CPV Codes</div>
                    <div class="notice-details-value">${notice.cpv_codes && notice.cpv_codes.length > 0 ? notice.cpv_codes.join(', ') : 'N/A'}</div>
                </div>
                <div class="notice-details-row">
                    <div class="notice-details-label">Est. Value</div>
                    <div class="notice-details-value">
                        ${notice.estimated_value ? `€${formatNumber(notice.estimated_value)}` : 'N/A'}
                    </div>
                </div>
                ${notice.url ? `
                <div class="notice-details-row">
                    <div class="notice-details-label">View on TED</div>
                    <div class="notice-details-value">
                        <a href="${notice.url}" target="_blank" rel="noopener noreferrer">
                            <i class="fas fa-external-link-alt"></i> Open on TED
                        </a>
                    </div>
                </div>
                ` : ''}
                ${notice.content_html ? `
                <div class="notice-details-row" style="border: none; padding-top: 1rem; margin-top: 1rem; border-top: 2px solid #dee2e6;">
                    <div class="notice-details-label">Full Content</div>
                </div>
                <div style="font-size: 0.85rem; color: #666; max-height: 300px; overflow-y: auto; padding: 1rem; background-color: #f8f9fa; border-radius: 0.25rem; margin-top: 0.5rem;">
                    ${notice.content_html}
                </div>
                ` : ''}
            </div>
        `;

        document.getElementById('modal-title').textContent = notice.publication_number;
        modalBody.innerHTML = html;

    } catch (error) {
        console.error('Error fetching notice details:', error);
        document.getElementById('modal-body').innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-circle"></i>
                Failed to load notice details: ${error.message}
            </div>
        `;
    }
}

// Reset search
function resetSearch() {
    currentSearchData = null;
    currentPage = 1;
    currentSearchQuery = null;
    emptyState.style.display = 'block';
    resultsContainer.style.display = 'none';
    errorAlert.style.display = 'none';
    searchStatus.style.display = 'none';
    setDefaultDates();
}

// Show error
function showError(message) {
    errorAlert.style.display = 'block';
    document.getElementById('error-text').textContent = message;
    console.error(message);
}

// Utility functions
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function formatNumber(num) {
    if (!num) return '0';
    return num.toLocaleString('en-US', { maximumFractionDigits: 0 });
}

function truncate(str, length) {
    if (!str) return '-';
    return str.length > length ? str.substring(0, length) + '...' : str;
}

// Fetch with timeout
async function fetchWithTimeout(url, options = {}, timeout = CONFIG.REQUEST_TIMEOUT) {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);
    
    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal
        });
        clearTimeout(id);
        return response;
    } catch (error) {
        clearTimeout(id);
        throw error;
    }
}

console.log('TED Scraper Frontend script loaded');
