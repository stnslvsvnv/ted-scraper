/* TED Scraper Frontend с accordion и проверками на null */

const CONFIG = {
    BACKEND_BASE_URL: window.location.origin,
    REQUEST_TIMEOUT: 30000,
};

console.log("Backend URL:", CONFIG.BACKEND_BASE_URL);

// Глобальное состояние
let currentPage = 1;
let totalResults = 0;

// Селектор DOM‑элементов
const elements = {
    searchForm: document.getElementById("search-form"),
    textInput: document.getElementById("text"),
    dateFrom: document.getElementById("publication-date-from"),
    dateTo: document.getElementById("publication-date-to"),
    countryInput: document.getElementById("country"),
    pageSize: document.getElementById("page-size"),
    searchBtn: document.getElementById("search-btn"),

    backendStatus: document.getElementById("backend-status"),
    resultsContainer: document.getElementById("results-container"),
    resultsTbody: document.getElementById("results-tbody"),
    emptyState: document.getElementById("empty-state"),
    loadingSpinner: document.getElementById("loading-spinner"),
    errorAlert: document.getElementById("error-alert"),
    searchStatus: document.getElementById("search-status"),
};

document.addEventListener("DOMContentLoaded", () => {
    console.log("TED Scraper Frontend loaded");
    setupEventListeners();
    setDefaultDates();
    checkBackendStatus();
    performSearch();
});

// Навешиваем обработчики только если элементы есть
function setupEventListeners() {
    if (elements.searchForm) {
        elements.searchForm.addEventListener("submit", (e) => {
            e.preventDefault();
            currentPage = 1;
            performSearch();
        });
    }

    if (elements.searchBtn) {
        elements.searchBtn.addEventListener("click", (e) => {
            e.preventDefault();
            currentPage = 1;
            performSearch();
        });
    }

    // Кнопка очистки фильтров
    if (elements.searchForm) {
        const clearBtn = document.createElement("button");
        clearBtn.type = "button";
        clearBtn.textContent = "Очистить фильтры";
        clearBtn.classList.add("btn", "btn-secondary", "ms-2");
        clearBtn.onclick = () => clearForm();
        elements.searchForm.appendChild(clearBtn);
    }

    // Клик по строке таблицы — открыть / закрыть accordion
    document.addEventListener("click", (e) => {
        const row = e.target.closest("tbody tr.notice-row");
        if (row) {
            const pubNum = row.dataset.publicationNumber;
            if (pubNum) {
                toggleAccordion(row, pubNum);
            }
        }
    });
}

// Даты по умолчанию
function setDefaultDates() {
    const today = new Date();
    const fromDate = new Date(today.getFullYear(), 9, 1); // 1 октября текущего года
    const fromStr = fromDate.toISOString().split("T")[0];
    const toStr = today.toISOString().split("T")[0];

    if (elements.dateFrom) elements.dateFrom.value = fromStr;
    if (elements.dateTo) elements.dateTo.value = toStr;
}

// Очистка формы
function clearForm() {
    if (elements.textInput) elements.textInput.value = "";
    if (elements.countryInput) elements.countryInput.value = "";
    if (elements.pageSize) elements.pageSize.value = "25";
    setDefaultDates();
    currentPage = 1;
    performSearch();
}

// Проверка backend /health
async function checkBackendStatus() {
    try {
        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/health`);
        if (response.ok) {
            if (elements.backendStatus) {
                elements.backendStatus.textContent = "Online";
                elements.backendStatus.classList.remove("bg-danger");
                elements.backendStatus.classList.add("bg-success");
            }
        } else {
            setBackendOffline();
        }
    } catch (e) {
        console.warn("Backend check failed:", e);
        setBackendOffline();
    }
    setTimeout(checkBackendStatus, 30000);
}

function setBackendOffline() {
    if (elements.backendStatus) {
        elements.backendStatus.textContent = "Offline";
        elements.backendStatus.classList.remove("bg-success");
        elements.backendStatus.classList.add("bg-danger");
    }
}

// Формирование запроса
function getSearchRequest() {
    const text = elements.textInput?.value?.trim() || null;
    let publicationDateFrom = elements.dateFrom?.value?.trim() || null;
    let publicationDateTo = elements.dateTo?.value?.trim() || null;

    // если даты не заданы — подставляем разумный диапазон
    if (!publicationDateFrom) publicationDateFrom = "2024-10-01";
    if (!publicationDateTo) publicationDateTo = new Date().toISOString().split("T")[0];

    let country = null;
    if (elements.countryInput) {
        const selected = Array.from(elements.countryInput.selectedOptions)
            .map((o) => o.value)
            .filter((v) => v);
        country = selected.length ? selected.join(",") : null;
    }

    const limit = parseInt(elements.pageSize?.value || "25", 10) || 25;

    return {
        filters: {
            text,
            publication_date_from: publicationDateFrom,
            publication_date_to: publicationDateTo,
            country,
        },
        page: currentPage,
        limit,
    };
}

// Поиск
async function performSearch() {
    try {
        if (elements.searchBtn) elements.searchBtn.disabled = true;
        if (elements.loadingSpinner) elements.loadingSpinner.style.display = "block";
        hideError();
        hideEmptyState();
        hideResults();
        showStatus("Поиск...");

        const request = getSearchRequest();
        console.log("Sending search request:", request);

        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/search`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(request),
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();
        totalResults = data.total || 0;
        displayResults(data);

        if (elements.searchStatus) {
            elements.searchStatus.className = "alert alert-success";
            elements.searchStatus.style.display = "block";
            elements.searchStatus.textContent = `${data.notices.length} результатов из ${data.total}`;
        }
    } catch (e) {
        console.error("Search error:", e);
        showError(`Ошибка поиска: ${e.message}`);
    } finally {
        if (elements.searchBtn) elements.searchBtn.disabled = false;
        if (elements.loadingSpinner) elements.loadingSpinner.style.display = "none";
    }
}

// Отображение результатов
function displayResults(data) {
    if (!data.notices || !data.notices.length) {
        showNoResults();
        return;
    }

    if (elements.resultsContainer) elements.resultsContainer.style.display = "block";
    if (!elements.resultsTbody) return;

    elements.resultsTbody.innerHTML = "";

    data.notices.forEach((n) => {
        const row = document.createElement("tr");
        row.className = "notice-row";
        row.dataset.publicationNumber = n.publication_number;

        row.innerHTML = `
            <td>${n.publication_number || "—"}</td>
            <td>${n.publication_date || "—"}</td>
            <td>${n.deadline_date || "—"}</td>
            <td>${n.title || "—"}</td>
            <td>${n.country || "—"}</td>
            <td>${n.city || "—"}</td>
            <td>${n.performance_city || "—"}</td>
        `;

        elements.resultsTbody.appendChild(row);
    });
}

// Accordion: раскрытие строки
async function toggleAccordion(row, publicationNumber) {
    const existingDetail = row.nextElementSibling;
    if (existingDetail && existingDetail.classList.contains("detail-row")) {
        existingDetail.remove();
        row.classList.remove("expanded");
        return;
    }

    // закрываем другие
    document.querySelectorAll(".detail-row").forEach((tr) => tr.remove());
    document.querySelectorAll(".notice-row").forEach((r) => r.classList.remove("expanded"));

    row.classList.add("expanded");

    const detailRow = document.createElement("tr");
    detailRow.className = "detail-row";
    detailRow.innerHTML =
        '<td colspan="7" class="detail-content"><div class="loading">Loading details...</div></td>';
    row.after(detailRow);

    try {
        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/notice/${publicationNumber}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const detail = await response.json();
        detailRow.querySelector("td").innerHTML = renderDetail(detail);

        const toggleBtn = detailRow.querySelector(".notice-toggle");
        const noticeContent = detailRow.querySelector(".notice-content");
        if (toggleBtn && noticeContent) {
            toggleBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                noticeContent.classList.toggle("open");
                toggleBtn.textContent = noticeContent.classList.contains("open")
                    ? "▼ Hide Full Notice"
                    : "► Show Full Notice";
            });
        }
    } catch (e) {
        console.error("Detail error:", e);
        detailRow.querySelector("td").innerHTML =
            `<div class="error">Не удалось загрузить детали: ${e.message}</div>`;
    }
}

// Разметка для detail
function renderDetail(detail) {
    const s = detail.summary || {};
    const lot = s.lot || {};
    const buyer = s.buyer || {};

    return `
        <div class="detail-container">
            <div class="detail-section">
                <h3>Direct URL</h3>
                <p><a href="${detail.direct_url}" target="_blank">${detail.direct_url}</a></p>
            </div>

            <div class="detail-section">
                <h3>Summary</h3>
                <div class="summary-grid">
                    <div class="summary-item"><strong>Type:</strong> ${s.type || "N/A"}</div>
                    <div class="summary-item"><strong>Country:</strong> ${s.country || "N/A"}</div>
                    <div class="summary-item"><strong>Procedure:</strong> ${s.procedure_type || "N/A"}</div>
                </div>

                <h4>Buyer</h4>
                <div class="summary-grid">
                    <div class="summary-item"><strong>Name:</strong> ${buyer.name || "N/A"}</div>
                    <div class="summary-item"><strong>Email:</strong> ${
                        buyer.email ? `<a href="mailto:${buyer.email}">${buyer.email}</a>` : "N/A"
                    }</div>
                    <div class="summary-item"><strong>Location:</strong> ${
                        (buyer.city || "") + (buyer.country ? ", " + buyer.country : "")
                    }</div>
                </div>

                <h4>${lot.title || "LOT"}</h4>
                <div class="summary-grid">
                    <div class="summary-item"><strong>Description:</strong> ${lot.description || "N/A"}</div>
                    <div class="summary-item"><strong>Contract Nature:</strong> ${lot.contract_nature || "N/A"}</div>
                    <div class="summary-item"><strong>Classification:</strong> ${lot.classification || "N/A"}</div>
                    <div class="summary-item"><strong>Place:</strong> ${
                        (lot.place_of_performance?.city || "N/A") +
                        ", " +
                        (lot.place_of_performance?.country || "N/A")
                    }</div>
                    <div class="summary-item"><strong>Start Date:</strong> ${lot.start_date || "N/A"}</div>
                    <div class="summary-item"><strong>End Date:</strong> ${lot.end_date || "N/A"}</div>
                    <div class="summary-item deadline-highlight">
                        <strong>Deadline:</strong> ${(lot.deadline?.date || "N/A") + " " + (lot.deadline?.time || "")}
                    </div>
                </div>
            </div>

            <div class="detail-section">
                <button class="notice-toggle">► Show Full Notice</button>
                <div class="notice-content">
                    <h3>Full Notice Details</h3>
                    <div class="notice-fields">
                        ${renderFullNotice(detail.full_notice || {})}
                    </div>
                </div>
            </div>
        </div>
    `;
}

function renderFullNotice(full) {
    return Object.entries(full)
        .map(
            ([k, v]) =>
                `<div class="notice-field"><strong>${k}:</strong> <span>${String(v)}</span></div>`
        )
        .join("");
}

// Вспомогательные функции отображения
function showNoResults() {
    if (elements.emptyState) elements.emptyState.style.display = "block";
    if (elements.resultsContainer) elements.resultsContainer.style.display = "none";
    if (elements.searchStatus) {
        elements.searchStatus.style.display = "block";
        elements.searchStatus.className = "alert alert-warning";
        elements.searchStatus.textContent = "0 результатов";
    }
}

function showError(msg) {
    if (elements.errorAlert) {
        elements.errorAlert.style.display = "block";
        elements.errorAlert.textContent = msg;
        elements.errorAlert.className = "alert alert-danger";
    }
}

function hideError() {
    if (elements.errorAlert) {
        elements.errorAlert.style.display = "none";
    }
}

function hideEmptyState() {
    if (elements.emptyState) elements.emptyState.style.display = "none";
}

function hideResults() {
    if (elements.resultsContainer) elements.resultsContainer.style.display = "none";
}

function showStatus(msg) {
    if (elements.searchStatus) {
        elements.searchStatus.style.display = "block";
        elements.searchStatus.className = "alert alert-info";
        elements.searchStatus.textContent = msg;
    }
}
