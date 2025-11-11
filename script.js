/* TED Scraper Frontend - FINAL WORKING VERSION */

// Configuration
const CONFIG = {
    BACKEND_BASE_URL: window.location.origin,
    REQUEST_TIMEOUT: 30000
};

console.log('Backend URL:', CONFIG.BACKEND_BASE_URL);

// State
let currentSearchData = null;
let currentPage = 1;

// DOM Elements
const searchBtn = document.getElementById('search-btn');
const backendStatus = document.getElementById('backend-status');
const resultsContainer = document.getElementById('results-container');
const emptyState = document.getElementById('empty-state');
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
    if (searchBtn) {
        searchBtn.addEventListener('click', performSearch);
    }

    // Document clicks
    document.addEventListener('click', (e) => {
        if (e.target.closest('.page-link')) {
            e.preventDefault();
            const page = e.target.dataset.page;
            if (page) {
                currentPage = parseInt(page);
                performSearch();
            }
        }

        if (e.target.closest('tbody tr')) {
            const row = e.target.closest('tbody tr');
            if (row) {
                const pubNum = row.dataset.publicationNumber;
                if (pubNum) {
                    showNoticeDetails(pubNum);
                }
            }
        }
    });
}

// Set default dates
function setDefaultDates() {
    const toDate = new Date().toISOString().split('T')[0];
    const fromDate = new Date();
    fromDate.setFullYear(fromDate.getFullYear() - 1);
    const fromDateStr = fromDate.toISOString().split('T')[0];

    const pubDateFrom = document.getElementById('pub-date-from');
    const pubDateTo = document.getElementById('pub-date-to');
    
    if (pubDateFrom) pubDateFrom.value = fromDateStr;
    if (pubDateTo) pubDateTo.value = toDate;
}

// Check Backend Status
async function checkBackendStatus() {
    try {
        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/health`, {
            timeout: 5000
        });
        
        if (response.ok) {
            if (backendStatus) {
                backendStatus.textContent = 'Online';
                backendStatus.classList.remove('bg-danger');
                backendStatus.classList.add('bg-success');
            }
            console.log('✓ Backend is online');
        } else {
            setBackendOffline();
        }
    } catch (error) {
        console.warn('Backend check failed:', error);
        setBackendOffline();
    }

    setTimeout(checkBackendStatus, 30000);
}

function setBackendOffline() {
    if (backendStatus) {
        backendStatus.textContent = 'Offline';
        backendStatus.classList.remove('bg-success');
        backendStatus.classList.add('bg-danger');
    }
}

// Get form data
function getSearchRequest() {
    const fullText = document.getElementById('full-text')?.value?.trim() || null;
    const pubDateFrom = document.getElementById('pub-date-from')?.value || null;
    const pubDateTo = document.getElementById('pub-date-to')?.value || null;
    const pageSize = parseInt(document.getElementById('page-size')?.value || 10);

    return {
        filters: {
            full_text: fullText,
            cpv_codes: null,
            buyer_countries: null,
            publication_date_from: pubDateFrom,
            publication_date_to: pubDateTo
        },
        page: currentPage,
        page_size: pageSize
    };
}

// Perform search
async function performSearch() {
    try {
        if (searchBtn) searchBtn.disabled = true;
        if (loadingSpinner) loadingSpinner.style.display = 'block';
        if (emptyState) emptyState.style.display = 'none';
        if (resultsContainer) resultsContainer.style.display = 'none';
        if (errorAlert) errorAlert.style.display = 'none';
        if (searchStatus) searchStatus.style.display = 'block';

        const request = getSearchRequest();
        
        console.log('Sending search request:', request);

        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(request)
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
        
        if (searchStatus) {
            searchStatus.classList.remove('alert-warning');
            searchStatus.classList.add('alert-success');
        }

    } catch (error) {
        console.error('Search error:', error);
        showError(`Search failed: ${error.message}`);
    } finally {
        if (searchBtn) searchBtn.disabled = false;
        if (loadingSpinner) loadingSpinner.style.display = 'none';
    }
}

// Display results
function displayResults(data) {
    const tbody = document.getElementById('results-tbody');
    if (!tbody) return;

    tbody.innerHTML = '';

    if (!data.notices || data.notices.length === 0) {
        if (emptyState) {
            emptyState.style.display = 'block';
            emptyState.innerHTML = `
                <i class="fas fa-inbox text-muted" style="font-size: 3rem;"></i>
                <h5 class="mt-3 text-muted">No results found</h5>
                <p class="text-muted">Try adjusting your search criteria</p>
            `;
        }
        if (resultsContainer) resultsContainer.style.display = 'none';
        return;
    }

    // Populate table
    data.notices.forEach((notice) => {
        const row = document.createElement('tr');
        row.dataset.publicationNumber = notice.publication_number;
        
        const pubNum = notice.publication_number || 'N/A';
        const date = notice.publication_date ? new Date(notice.publication_date).toLocaleDateString() : '-';
        const title = notice.title || 'N/A';
        const buyer = notice.buyer_name || '-';
        const country = notice.country || '-';
        const cpv = notice.cpv_codes ? (Array.isArray(notice.cpv_codes) ? notice.cpv_codes[0] : notice.cpv_codes) : '-';

        row.innerHTML = `
            <td>${pubNum}</td>
            <td>${date}</td>
            <td><strong>${truncate(title, 50)}</strong></td>
            <td>${truncate(buyer, 30)}</td>
            <td>${country}</td>
            <td>${cpv}</td>
            <td><button class="btn btn-sm btn-outline-primary"><i class="fas fa-external-link-alt"></i></button></td>
        `;
        
        tbody.appendChild(row);
    });

    // Update info
    const showingEl = document.getElementById('showing-count');
    const totalEl = document.getElementById('total-count');
    const pageEl = document.getElementById('current-page');
    const pagesEl = document.getElementById('total-pages');
    
    if (showingEl) showingEl.textContent = data.notices.length;
    if (totalEl) totalEl.textContent = data.total_notices;
    if (pageEl) pageEl.textContent = data.current_page;
    if (pagesEl) pagesEl.textContent = data.total_pages;

    // Pagination
    generatePagination(data);

    // Show results
    if (resultsContainer) resultsContainer.style.display = 'block';
}

// Generate pagination
function generatePagination(data) {
    const pagination = document.getElementById('pagination');
    if (!pagination) return;

    pagination.innerHTML = '';

    const totalPages = data.total_pages || 1;
    const currentPage_ = data.current_page || 1;

    if (totalPages <= 1) return;

    // Previous
    if (currentPage_ > 1) {
        const li = document.createElement('li');
        li.className = 'page-item';
        li.innerHTML = `<a class="page-link" href="#" data-page="${currentPage_ - 1}">← Previous</a>`;
        pagination.appendChild(li);
    }

    // Numbers
    for (let i = 1; i <= totalPages; i++) {
        if (i < 1 || i > totalPages) continue;
        if (i > currentPage_ + 2 && i < totalPages - 2) {
            if (i === currentPage_ + 3) {
                const li = document.createElement('li');
                li.className = 'page-item disabled';
                li.innerHTML = '<span class="page-link">...</span>';
                pagination.appendChild(li);
            }
            continue;
        }

        const li = document.createElement('li');
        li.className = i === currentPage_ ? 'page-item active' : 'page-item';
        li.innerHTML = `<a class="page-link" href="#" data-page="${i}">${i}</a>`;
        pagination.appendChild(li);
    }

    // Next
    if (currentPage_ < totalPages) {
        const li = document.createElement('li');
        li.className = 'page-item';
        li.innerHTML = `<a class="page-link" href="#" data-page="${currentPage_ + 1}">Next →</a>`;
        pagination.appendChild(li);
    }
}

// Show notice details
async function showNoticeDetails(pubNum) {
    try {
        const modal = new bootstrap.Modal(document.getElementById('notice-modal') || new HTMLElement());
        const modalBody = document.getElementById('modal-body');
        
        if (!modalBody) return;
        
        const modalTitle = document.getElementById('modal-title');
        if (modalTitle) modalTitle.textContent = `Loading ${pubNum}...`;
        
        modalBody.innerHTML = '<div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div>';
        modal.show();

        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/notice/${pubNum}`);
        
        if (!response.ok) {
            throw new Error('Failed to fetch notice details');
        }

        const notice = await response.json();

        const html = `
            <div class="notice-details">
                <div class="mb-3">
                    <strong>Publication Number:</strong> ${notice.publication_number}
                </div>
                <div class="mb-3">
                    <strong>Date:</strong> ${notice.publication_date || 'N/A'}
                </div>
                <div class="mb-3">
                    <strong>Title:</strong> ${notice.title || 'N/A'}
                </div>
                <div class="mb-3">
                    <strong>Buyer:</strong> ${notice.buyer_name || 'N/A'}
                </div>
                <div class="mb-3">
                    <strong>Country:</strong> ${notice.country || 'N/A'}
                </div>
                <div class="mb-3">
                    <strong>Type:</strong> ${notice.notice_type || 'N/A'}
                </div>
                <div class="mb-3">
                    <strong>CPV:</strong> ${notice.cpv_codes ? (Array.isArray(notice.cpv_codes) ? notice.cpv_codes.join(', ') : notice.cpv_codes) : 'N/A'}
                </div>
                ${notice.url ? `<a href="${notice.url}" target="_blank" class="btn btn-primary">View on TED</a>` : ''}
            </div>
        `;

        if (modalTitle) modalTitle.textContent = notice.publication_number;
        modalBody.innerHTML = html;

    } catch (error) {
        console.error('Error:', error);
        const modalBody = document.getElementById('modal-body');
        if (modalBody) {
            modalBody.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
        }
    }
}

// Show error
function showError(message) {
    if (errorAlert) {
        errorAlert.style.display = 'block';
        const errorText = document.getElementById('error-text');
        if (errorText) errorText.textContent = message;
    }
    console.error(message);
}

// Utility
function truncate(str, length) {
    if (!str) return '-';
    return str.length > length ? str.substring(0, length) + '...' : str;
}

console.log('TED Scraper Frontend script loaded');
