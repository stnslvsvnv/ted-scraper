const API_BASE = "http://localhost:8000";

let currentPage = 1;
let currentFilters = {};
let totalResults = 0;

// Инициализация
document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("searchBtn").addEventListener("click", performSearch);
    document.getElementById("prevPage").addEventListener("click", () => changePage(-1));
    document.getElementById("nextPage").addEventListener("click", () => changePage(1));

    // Enter для поиска
    ["searchText", "countryFilter", "dateFrom", "dateTo"].forEach(id => {
        document.getElementById(id)?.addEventListener("keypress", (e) => {
            if (e.key === "Enter") performSearch();
        });
    });

    // Первоначальный поиск
    performSearch();
});

async function performSearch() {
    currentPage = 1;
    currentFilters = {
        text: document.getElementById("searchText").value.trim() || null,
        country: document.getElementById("countryFilter").value.trim() || null,
        publication_date_from: document.getElementById("dateFrom").value || null,
        publication_date_to: document.getElementById("dateTo").value || null,
    };

    await fetchResults();
}

async function changePage(delta) {
    const newPage = currentPage + delta;
    if (newPage < 1) return;

    const totalPages = Math.ceil(totalResults / 25);
    if (newPage > totalPages) return;

    currentPage = newPage;
    await fetchResults();
}

async function fetchResults() {
    const resultsDiv = document.getElementById("results");
    const tbody = document.querySelector("#resultsTable tbody");
    const statusDiv = document.getElementById("status");
    const pagination = document.getElementById("pagination");

    resultsDiv.style.display = "none";
    statusDiv.textContent = "Searching...";
    statusDiv.className = "status info";

    try {
        const response = await fetch(`${API_BASE}/search`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                filters: currentFilters,
                page: currentPage,
                limit: 25,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Search failed");
        }

        const data = await response.json();
        totalResults = data.total;

        tbody.innerHTML = "";

        if (data.notices.length === 0) {
            statusDiv.textContent = "No results found";
            statusDiv.className = "status warning";
            return;
        }

        data.notices.forEach((notice) => {
            const row = createNoticeRow(notice);
            tbody.appendChild(row);
        });

        updatePaginationInfo();
        resultsDiv.style.display = "block";
        statusDiv.textContent = "";
        pagination.style.display = "flex";

    } catch (error) {
        console.error("Search error:", error);
        statusDiv.textContent = `Error: ${error.message}`;
        statusDiv.className = "status error";
    }
}

function createNoticeRow(notice) {
    const row = document.createElement("tr");
    row.className = "notice-row";
    row.dataset.publicationNumber = notice.publication_number;

    row.innerHTML = `
        <td>${notice.publication_number || "—"}</td>
        <td>${notice.publication_date || "—"}</td>
        <td>${notice.deadline_date || "—"}</td>
        <td>${notice.title || "—"}</td>
        <td>${notice.country || "—"}</td>
        <td>${notice.city || "—"}</td>
        <td>${notice.performance_city || "—"}</td>
    `;

    row.addEventListener("click", () => toggleAccordion(row));
    return row;
}

async function toggleAccordion(row) {
    const publicationNumber = row.dataset.publicationNumber;
    const existingDetail = row.nextElementSibling;

    // Если уже открыто — закрыть
    if (existingDetail && existingDetail.classList.contains("detail-row")) {
        existingDetail.remove();
        row.classList.remove("expanded");
        return;
    }

    // Закрыть все другие открытые
    document.querySelectorAll(".detail-row").forEach(el => el.remove());
    document.querySelectorAll(".notice-row").forEach(r => r.classList.remove("expanded"));

    row.classList.add("expanded");

    // Показать загрузку
    const loadingRow = document.createElement("tr");
    loadingRow.className = "detail-row";
    loadingRow.innerHTML = `<td colspan="7" class="detail-content"><div class="loading">Loading details...</div></td>`;
    row.after(loadingRow);

    try {
        const response = await fetch(`${API_BASE}/notice/${publicationNumber}`);
        if (!response.ok) {
            throw new Error("Failed to load details");
        }

        const detail = await response.json();
        loadingRow.querySelector("td").innerHTML = renderDetail(detail);

        // Добавить обработчик для вложенного accordion (Notice)
        const noticeToggle = loadingRow.querySelector(".notice-toggle");
        if (noticeToggle) {
            noticeToggle.addEventListener("click", (e) => {
                e.stopPropagation();
                const noticeContent = loadingRow.querySelector(".notice-content");
                noticeContent.classList.toggle("open");
                noticeToggle.textContent = noticeContent.classList.contains("open") 
                    ? "▼ Hide Full Notice" 
                    : "► Show Full Notice";
            });
        }

    } catch (error) {
        console.error("Error loading detail:", error);
        loadingRow.querySelector("td").innerHTML = `<div class="error">Failed to load details: ${error.message}</div>`;
    }
}

function renderDetail(detail) {
    const summary = detail.summary;
    const lot = summary.lot;
    const buyer = summary.buyer;

    return `
        <div class="detail-container">
            <div class="detail-section">
                <h3>Direct URL</h3>
                <p><a href="${detail.direct_url}" target="_blank">${detail.direct_url}</a></p>
            </div>

            <div class="detail-section">
                <h3>Summary</h3>
                <div class="summary-grid">
                    <div class="summary-item">
                        <strong>Type:</strong> ${summary.type}
                    </div>
                    <div class="summary-item">
                        <strong>Country:</strong> ${summary.country}
                    </div>
                    <div class="summary-item">
                        <strong>Procedure:</strong> ${summary.procedure_type}
                    </div>
                </div>

                <h4>Buyer</h4>
                <div class="summary-grid">
                    <div class="summary-item">
                        <strong>Name:</strong> ${buyer.name}
                    </div>
                    <div class="summary-item">
                        <strong>Email:</strong> <a href="mailto:${buyer.email}">${buyer.email}</a>
                    </div>
                    <div class="summary-item">
                        <strong>Location:</strong> ${buyer.city}, ${buyer.country}
                    </div>
                </div>

                <h4>${lot.title}</h4>
                <div class="summary-grid">
                    <div class="summary-item">
                        <strong>Description:</strong> ${lot.description}
                    </div>
                    <div class="summary-item">
                        <strong>Contract Nature:</strong> ${lot.contract_nature}
                    </div>
                    <div class="summary-item">
                        <strong>Classification:</strong> ${lot.classification}
                    </div>
                    <div class="summary-item">
                        <strong>Place:</strong> ${lot.place_of_performance.city}, ${lot.place_of_performance.country}
                    </div>
                    <div class="summary-item">
                        <strong>Start Date:</strong> ${lot.start_date || "N/A"}
                    </div>
                    <div class="summary-item">
                        <strong>End Date:</strong> ${lot.end_date || "N/A"}
                    </div>
                    <div class="summary-item deadline-highlight">
                        <strong>Deadline:</strong> ${lot.deadline.date || "N/A"} ${lot.deadline.time || ""}
                    </div>
                </div>
            </div>

            <div class="detail-section">
                <button class="notice-toggle">► Show Full Notice</button>
                <div class="notice-content">
                    <h3>Full Notice Details</h3>
                    <div class="notice-fields">
                        ${renderFullNotice(detail.full_notice)}
                    </div>
                </div>
            </div>
        </div>
    `;
}

function renderFullNotice(fullNotice) {
    return Object.entries(fullNotice)
        .map(([key, value]) => `
            <div class="notice-field">
                <strong>${key}:</strong> <span>${value}</span>
            </div>
        `)
        .join("");
}

function updatePaginationInfo() {
    const totalPages = Math.ceil(totalResults / 25);
    document.getElementById("pageInfo").textContent = 
        `Page ${currentPage} of ${totalPages} (Total: ${totalResults} results)`;
    document.getElementById("prevPage").disabled = currentPage === 1;
    document.getElementById("nextPage").disabled = currentPage >= totalPages;
}
