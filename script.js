/* TED Scraper Frontend - FIXED VERSION */

const CONFIG = {
    BACKEND_BASE_URL: window.location.origin,
    REQUEST_TIMEOUT: 30000,
};

console.log("Backend URL:", CONFIG.BACKEND_BASE_URL);

// Глобальное состояние
let currentPage = 1;
let totalResults = 0;
let totalPages = 1;
let selectedCountries = new Set();
let countriesList = [];

// DOM элементы
const elements = {
    // Form elements
    searchForm: document.getElementById("search-form"),
    textInput: document.getElementById("text"),
    dateFrom: document.getElementById("publication-date-from"),
    dateTo: document.getElementById("publication-date-to"),
    countryInput: document.getElementById("country-select"),
    countryDropdown: document.getElementById("country-dropdown"),
    selectedCountriesContainer: document.getElementById("selected-countries"),
    cpvCode: document.getElementById("cpv-code"),
    activeOnly: document.getElementById("active-only"),
    pageSize: document.getElementById("page-size"),
    searchBtn: document.getElementById("search-btn"),
    clearBtn: document.getElementById("clear-btn"),

    // Status elements
    backendStatus: document.getElementById("backend-status"),
    resultsContainer: document.getElementById("results-container"),
    resultsTbody: document.getElementById("results-tbody"),
    emptyState: document.getElementById("empty-state"),
    loadingSpinner: document.getElementById("loading-spinner"),
    errorAlert: document.getElementById("error-alert"),
    infoAlert: document.getElementById("info-alert"),
    resultsSummary: document.getElementById("results-summary"),

    // Pagination
    prevPage: document.getElementById("prev-page"),
    nextPage: document.getElementById("next-page"),
    pageInfo: document.getElementById("page-info"),
};

// Инициализация
document.addEventListener("DOMContentLoaded", async () => {
    console.log("TED Scraper Frontend initialized");
    setDefaultDates();
    await loadCountries();
    setupEventListeners();
    checkBackendStatus();
});

// Установка дат по умолчанию
function setDefaultDates() {
    const today = new Date();
    const monthAgo = new Date();
    monthAgo.setDate(today.getDate() - 30);

    if (elements.dateFrom) {
        elements.dateFrom.valueAsDate = monthAgo;
        elements.dateFrom.max = today.toISOString().split("T")[0];
    }
    if (elements.dateTo) {
        elements.dateTo.valueAsDate = today;
        elements.dateTo.max = today.toISOString().split("T")[0];
    }
}

// Загрузка списка стран
async function loadCountries() {
    try {
        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/countries`);
        if (response.ok) {
            countriesList = await response.json();
            populateCountryDropdown();
        }
    } catch (error) {
        console.warn("Failed to load countries:", error);
        countriesList = [
            { code: "DEU", name: "Germany (Deutschland)" },
            { code: "FRA", name: "France" },
            { code: "ITA", name: "Italy (Italia)" },
            { code: "ESP", name: "Spain (España)" },
            { code: "GBR", name: "United Kingdom" },
            { code: "NLD", name: "Netherlands (Nederland)" },
            { code: "BEL", name: "Belgium (België/Belgique)" },
            { code: "POL", name: "Poland (Polska)" },
        ];
        populateCountryDropdown();
    }
}

// Заполнение выпадающего списка стран
function populateCountryDropdown() {
    if (!elements.countryDropdown || !countriesList.length) return;
    elements.countryDropdown.innerHTML = "";

    countriesList.forEach((country) => {
        const option = document.createElement("div");
        option.className = "multi-select-option";
        option.innerHTML = `
            <input type="checkbox" id="country-${country.code}">
            <label for="country-${country.code}">${country.name}</label>
        `;
        option.querySelector("input").addEventListener("change", (e) => {
            if (e.target.checked) {
                selectedCountries.add(country.code);
            } else {
                selectedCountries.delete(country.code);
            }
            updateSelectedCountriesDisplay();
        });
        elements.countryDropdown.appendChild(option);
    });
}

// Обновление отображения выбранных стран
function updateSelectedCountriesDisplay() {
    if (!elements.selectedCountriesContainer) return;
    elements.selectedCountriesContainer.innerHTML = "";

    if (elements.countryInput) {
        elements.countryInput.value = selectedCountries.size
            ? `Выбрано стран: ${selectedCountries.size}`
            : "Выберите страны...";
    }

    selectedCountries.forEach((countryCode) => {
        const country = countriesList.find((c) => c.code === countryCode);
        if (country) {
            const tag = document.createElement("div");
            tag.className = "country-tag";
            tag.innerHTML = `
                ${country.code}
                <span class="remove" onclick="removeCountry('${countryCode}')">&times;</span>
            `;
            elements.selectedCountriesContainer.appendChild(tag);
        }
    });
}

// Удаление страны
function removeCountry(countryCode) {
    selectedCountries.delete(countryCode);
    const checkbox = document.getElementById(`country-${countryCode}`);
    if (checkbox) checkbox.checked = false;
    updateSelectedCountriesDisplay();
}

// Переключение выпадающего списка стран
function toggleCountryDropdown() {
    if (elements.countryDropdown) {
        elements.countryDropdown.classList.toggle("show");
    }
}

// Закрытие выпадающего списка при клике вне его
document.addEventListener("click", (e) => {
    if (
        !elements.countryInput?.contains(e.target) &&
        !elements.countryDropdown?.contains(e.target)
    ) {
        elements.countryDropdown?.classList.remove("show");
    }
});

// Настройка обработчиков событий
function setupEventListeners() {
    if (elements.searchForm) {
        elements.searchForm.addEventListener("submit", (e) => {
            e.preventDefault();
            currentPage = 1;
            performSearch();
        });
    }

    if (elements.clearBtn) {
        elements.clearBtn.addEventListener("click", clearForm);
    }

    if (elements.prevPage) {
        elements.prevPage.addEventListener("click", () => {
            if (currentPage > 1) {
                currentPage--;
                performSearch();
            }
        });
    }

    if (elements.nextPage) {
        elements.nextPage.addEventListener("click", () => {
            if (currentPage < totalPages) {
                currentPage++;
                performSearch();
            }
        });
    }

    document.querySelectorAll(".theme-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            const theme = e.target.dataset.theme;
            document.documentElement.setAttribute("data-theme", theme);
            document
                .querySelectorAll(".theme-btn")
                .forEach((b) => b.classList.remove("active"));
            e.target.classList.add("active");
        });
    });
}


// Очистка формы
function clearForm() {
    if (elements.textInput) elements.textInput.value = "";
    if (elements.cpvCode) elements.cpvCode.value = "";
    if (elements.activeOnly) elements.activeOnly.checked = false;
    if (elements.pageSize) elements.pageSize.value = "25";
    
    // Очистка выбранных стран
    selectedCountries.clear();
    updateSelectedCountriesDisplay();
    
    // Снятие галочек в выпадающем списке
    document.querySelectorAll('#country-dropdown input[type="checkbox"]').forEach(checkbox => {
        checkbox.checked = false;
    });
    
    setDefaultDates();
    currentPage = 1;
    
    // Скрываем результаты
    hideResults();
    showInfo("Форма очищена. Введите новые критерии поиска.");
}

// Проверка статуса бэкенда
async function checkBackendStatus() {
    console.log("🔍 CHECKING BACKEND...", CONFIG.BACKEND_BASE_URL + "/health");
    try {
        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/health`, { 
            timeout: 5000,
            cache: 'no-cache'
        });
        console.log("✅ HEALTH RESPONSE:", response.status);
        if (response.ok) {
            setBackendStatus(true);
        } else {
            setBackendStatus(false);
        }
    } catch (error) {
        console.error("❌ HEALTH ERROR:", error);
        setBackendStatus(false);
    }
    setTimeout(checkBackendStatus, 20000);
}

function setBackendStatus(isOnline) {
    if (elements.backendStatus) {
        if (isOnline) {
            elements.backendStatus.textContent = "Online";
            elements.backendStatus.className = "status-badge online";
        } else {
            elements.backendStatus.textContent = "Offline";
            elements.backendStatus.className = "status-badge offline";
        }
    }
}

// Формирование запроса
function getSearchRequest() {
    const text = elements.textInput?.value?.trim() || null;
    const publicationDateFrom = elements.dateFrom?.value || null;
    const publicationDateTo = elements.dateTo?.value || null;
    const cpvCode = elements.cpvCode?.value?.trim() || null;
    const activeOnly = elements.activeOnly?.checked || false;
    const limit = parseInt(elements.pageSize?.value || "25", 10);
    
    // Преобразуем Set стран в строку
    const country = selectedCountries.size > 0 ? Array.from(selectedCountries).join(",") : null;
    
    return {
        filters: {
            text,
            publication_date_from: publicationDateFrom,
            publication_date_to: publicationDateTo,
            country,
            cpv_code: cpvCode,
            active_only: activeOnly
        },
        page: currentPage,
        limit: limit
    };
}

// Выполнение поиска
async function performSearch() {
    console.log("🔍 START SEARCH", currentPage);
    try {
        showLoading(true);
        hideError();
        hideInfo();
        hideEmptyState();
        hideResults();
        
        const request = getSearchRequest();
        console.log("📤 SEARCH REQUEST:", request);
        
        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/search`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify(request),
            cache: 'no-cache'
        });
        
        console.log("📥 SEARCH RESPONSE:", response.status);
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            console.error("❌ SEARCH ERROR:", error);
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        
        const data = await response.json();
        console.log("✅ SEARCH DATA:", data);
        
        // Обработка полученных данных
        if (data.notices && data.notices.length > 0) {
            totalResults = data.total;
            const limit = parseInt(elements.pageSize?.value || "25", 10);
            totalPages = Math.ceil(totalResults / limit);
            
            displayResults(data.notices);
            showResults();
            updatePagination();
            updateResultsSummary(data.total);
            hideEmptyState();
        } else {
            showNoResults();
            hideResults();
        }
        
    } catch (error) {
        console.error("💥 FULL ERROR:", error);
        showError(`Ошибка поиска: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

// Отображение результатов
function displayResults(notices) {
    if (!elements.resultsTbody) return;
    
    elements.resultsTbody.innerHTML = "";
    
    notices.forEach(notice => {
        const row = document.createElement("tr");
        row.className = "notice-row";
        row.dataset.publicationNumber = notice.publication_number;
        
        // Форматирование дат
        const pubDate = notice.publication_date ? formatDate(notice.publication_date) : "—";
        const deadlineDate = notice.deadline_date ? formatDate(notice.deadline_date) : "—";
        
        row.innerHTML = `
            <td><strong>${notice.publication_number}</strong></td>
            <td>${pubDate}</td>
            <td>${deadlineDate}</td>
            <td>${notice.title || '—'}</td>
            <td>${notice.country || '—'}</td>
            <td>${notice.city || '—'}</td>
            <td>${notice.cpv_code || '—'}</td>
        `;
        
        // Click handler для expandable row
        row.addEventListener('click', async () => {
            // сначала пробуем найти уже существующую строку деталей
            let detailRow = document.querySelector(`[data-publication="${notice.publication_number}"]`);
            if (detailRow) {
                detailRow.remove();
                row.classList.remove('expanded');
                return;
            }

            row.classList.add('expanded');

            const directUrl = `https://ted.europa.eu/en/notice/${notice.publication_number}/html`;

            // создаём новую строку деталей
            detailRow = document.createElement('tr');
            detailRow.className = 'detail-row';
            detailRow.dataset.publication = notice.publication_number;
            detailRow.innerHTML = `
                <td colspan="7" class="detail-cell">
                    <div class="detail-container">
                        <div class="detail-section">
                            <h3>📄 Direct Link & Summary</h3>
                            <div class="detail-grid">
                                <div class="detail-item">
                                    <strong>Publication:</strong>
                                    <a href="${directUrl}" target="_blank" class="btn btn-primary">Open TED Notice</a>
                                </div>
                                <div class="detail-item">
                                    <strong>Title:</strong> ${notice.title || '—'}
                                </div>
                                <div class="detail-item">
                                    <strong>Buyer:</strong> ${notice.buyer || '—'}
                                </div>
                                <div class="detail-item">
                                    <strong>CPV:</strong> ${notice.cpv_code || '—'}
                                </div>
                            </div>
                        </div>
                    </div>
                </td>
            `;
            elements.resultsTbody.appendChild(detailRow);
        });
        
        elements.resultsTbody.appendChild(row);
    });
}

function formatDate(dateStr) {
    try {
        // Предполагаем, что дата может приходить в формате YYYYMMDD или YYYY-MM-DD
        let cleanDate = dateStr.replace(/-/g, '');
        
        if (cleanDate.length === 8) {
            const year = cleanDate.substring(0, 4);
            const month = cleanDate.substring(4, 6);
            const day = cleanDate.substring(6, 8);
            return `${day}.${month}.${year}`;
        }
        
        return dateStr || '—';
    } catch {
        return dateStr || '—';
    }
}

function updatePagination() {
    if (elements.pageInfo) {
        elements.pageInfo.textContent = `Страница ${currentPage} из ${totalPages}`;
    }
    if (elements.prevPage) {
        elements.prevPage.disabled = currentPage <= 1;
    }
    if (elements.nextPage) {
        elements.nextPage.disabled = currentPage >= totalPages;
    }
}

// Обновление сводки результатов
function updateResultsSummary(total) {
    if (elements.resultsSummary) {
        elements.resultsSummary.textContent = `Найдено тендеров: ${total}`;
    }
}

// UI Helpers
function showLoading(show) {
    if (elements.loadingSpinner) {
        elements.loadingSpinner.style.display = show ? 'block' : 'none';
    }
}

function hideResults() {
    if (elements.resultsContainer) {
        elements.resultsContainer.style.display = 'none';
    }
}

function showResults() {
    if (elements.resultsContainer) {
        elements.resultsContainer.style.display = 'block';
    }
}

function showNoResults() {
    if (elements.emptyState) {
        elements.emptyState.style.display = 'block';
    }
}

function hideEmptyState() {
    if (elements.emptyState) {
        elements.emptyState.style.display = 'none';
    }
}

function showError(message) {
    if (elements.errorAlert) {
        elements.errorAlert.textContent = message;
        elements.errorAlert.style.display = 'block';
    }
}

function hideError() {
    if (elements.errorAlert) {
        elements.errorAlert.style.display = 'none';
    }
}

function showInfo(message) {
    if (elements.infoAlert) {
        elements.infoAlert.textContent = message;
        elements.infoAlert.style.display = 'block';
    }
}

function hideInfo() {
    if (elements.infoAlert) {
        elements.infoAlert.style.display = 'none';
    }
}

// 🔥 ТЕСТОВАЯ КНОПКА для DevTools
window.testBackend = async () => {
    console.log("🧪 TESTING...");
    try {
        const health = await fetch('/health');
        console.log('HEALTH:', await health.json());
        
        const countries = await fetch('/countries');
        console.log('COUNTRIES:', await countries.json());
        
        console.log('✅ Backend работает!');
    } catch(e) {
        console.error('❌ Backend сломан:', e);
    }
};