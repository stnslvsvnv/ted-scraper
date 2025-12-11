/* TED Scraper Frontend - Полностью переработанная версия */

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
    pageInfo: document.getElementById("page-info")
};

// Инициализация
document.addEventListener("DOMContentLoaded", async () => {
    console.log("TED Scraper Frontend initialized");
    
    // Установка дат по умолчанию (последние 30 дней)
    setDefaultDates();
    
    // Загрузка списка стран
    await loadCountries();
    
    // Настройка обработчиков событий
    setupEventListeners();
    
    // Проверка статуса бэкенда
    checkBackendStatus();
    
    // Автоматический поиск при загрузке
    // performSearch();
});

// Установка дат по умолчанию
function setDefaultDates() {
    const today = new Date();
    const monthAgo = new Date();
    monthAgo.setDate(today.getDate() - 30);
    
    if (elements.dateFrom) {
        elements.dateFrom.valueAsDate = monthAgo;
        elements.dateFrom.max = today.toISOString().split('T')[0];
    }
    
    if (elements.dateTo) {
        elements.dateTo.valueAsDate = today;
        elements.dateTo.max = today.toISOString().split('T')[0];
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
        // Fallback к стандартному списку
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
    
    elements.countryDropdown.innerHTML = '';
    
    countriesList.forEach(country => {
        const option = document.createElement("div");
        option.className = "multi-select-option";
        option.innerHTML = `
            <input type="checkbox" id="country-${country.code}" 
                   value="${country.code}" 
                   ${selectedCountries.has(country.code) ? 'checked' : ''}>
            <label for="country-${country.code}">
                ${country.name}
            </label>
        `;
        
        option.querySelector('input').addEventListener('change', (e) => {
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
    
    elements.selectedCountriesContainer.innerHTML = '';
    
    // Обновляем поле ввода
    if (elements.countryInput) {
        elements.countryInput.value = selectedCountries.size 
            ? `Выбрано стран: ${selectedCountries.size}` 
            : "Выберите страны...";
    }
    
    // Добавляем теги выбранных стран
    selectedCountries.forEach(countryCode => {
        const country = countriesList.find(c => c.code === countryCode);
        if (country) {
            const tag = document.createElement("div");
            tag.className = "country-tag";
            tag.innerHTML = `
                ${country.code}
                <span class="remove" onclick="removeCountry('${country.code}')">
                    <i class="fas fa-times"></i>
                </span>
            `;
            elements.selectedCountriesContainer.appendChild(tag);
        }
    });
}

// Удаление страны
function removeCountry(countryCode) {
    selectedCountries.delete(countryCode);
    
    // Снимаем галочку в выпадающем списке
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
document.addEventListener('click', (e) => {
    if (!elements.countryInput?.contains(e.target) && 
        !elements.countryDropdown?.contains(e.target)) {
        elements.countryDropdown?.classList.remove("show");
    }
});

// Настройка обработчиков событий
function setupEventListeners() {
    // Поиск по форме
    if (elements.searchForm) {
        elements.searchForm.addEventListener("submit", (e) => {
            e.preventDefault();
            currentPage = 1;
            performSearch();
        });
    }
    
    // Кнопка очистки
    if (elements.clearBtn) {
        elements.clearBtn.addEventListener("click", clearForm);
    }
    
    // Пагинация
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
    
    // Переключатель темы
    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const theme = e.target.dataset.theme;
            document.documentElement.setAttribute('data-theme', theme);
            
            // Обновляем активную кнопку
            document.querySelectorAll('.theme-btn').forEach(b => 
                b.classList.remove('active'));
            e.target.classList.add('active');
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
    try {
        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/health`, {
            timeout: 5000
        });
        
        if (response.ok) {
            setBackendStatus(true);
        } else {
            setBackendStatus(false);
        }
    } catch (error) {
        console.warn("Backend check failed:", error);
        setBackendStatus(false);
    }
    
    // Повторная проверка каждые 30 секунд
    setTimeout(checkBackendStatus, 30000);
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
    const country = selectedCountries.size > 0 
        ? Array.from(selectedCountries).join(",") 
        : null;
    
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
    try {
        // Показываем лоадер
        showLoading(true);
        hideError();
        hideInfo();
        hideEmptyState();
        hideResults();
        
        const request = getSearchRequest();
        console.log("Search request:", request);
        
        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/search`, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify(request)
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        
        const data = await response.json();
        console.log("Search response:", data);
        
        totalResults = data.total || 0;
        totalPages = Math.ceil(totalResults / (request.limit || 25));
        
        // Обновляем пагинацию
        updatePagination();
        
        if (data.notices && data.notices.length > 0) {
            displayResults(data.notices);
            showResults();
        } else {
            showNoResults();
        }
        
        // Обновляем сводку
        if (elements.resultsSummary) {
            elements.resultsSummary.textContent = 
                `Найдено: ${totalResults} тендеров | Страница ${currentPage} из ${totalPages}`;
        }
        
    } catch (error) {
        console.error("Search error:", error);
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
        const pubDate = notice.publication_date ? 
            formatDate(notice.publication_date) : "—";
        const deadlineDate = notice.deadline_date ? 
            formatDate(notice.deadline_date) : "—";
        
        row.innerHTML = `
            <td>
                <strong>${notice.publication_number || "—"}</strong>
            </td>
            <td>${pubDate}</td>
            <td>${deadlineDate}</td>
            <td>
                <div style="max-width: 300px; overflow: hidden; text-overflow: ellipsis;">
                    ${notice.title || "—"}
                </div>
            </td>
            <td>${notice.country || "—"}</td>
            <td>${notice.city || "—"}</td>
            <td>
                <code>${notice.cpv_code || "—"}</code>
            </td>
        `;
        
        // Обработчик клика для accordion
        row.addEventListener("click", async (e) => {
            // Если клик на ссылке - не открываем accordion
            if (e.target.tagName === 'A' || e.target.closest('a')) {
                return;
            }
            
            await toggleAccordion(row, notice.publication_number);
        });
        
        elements.resultsTbody.appendChild(row);
    });
}

// Форматирование даты
function formatDate(dateStr) {
    if (!dateStr) return "—";
    
    // TED даты в формате YYYYMMDD
    if (dateStr.length === 8) {
        const year = dateStr.substring(0, 4);
        const month = dateStr.substring(4, 6);
        const day = dateStr.substring(6, 8);
        return `${day}.${month}.${year}`;
    }
    
    return dateStr;
}

// Accordion: раскрытие/скрытие деталей
async function toggleAccordion(row, publicationNumber) {
    // Закрываем другие открытые accordions
    document.querySelectorAll(".detail-row").forEach(el => el.remove());
    document.querySelectorAll(".notice-row.expanded").forEach(el => 
        el.classList.remove("expanded"));
    
    // Если уже открыт - закрываем
    if (row.classList.contains("expanded")) {
        row.classList.remove("expanded");
        return;
    }
    
    // Отмечаем как открытый
    row.classList.add("expanded");
    
    // Создаем строку для деталей
    const detailRow = document.createElement("tr");
    detailRow.className = "detail-row";
    detailRow.innerHTML = `
        <td colspan="7" class="detail-cell">
            <div class="loading">Загрузка деталей...</div>
        </td>
    `;
    
    row.after(detailRow);
    
    try {
        // Загружаем детали
        const response = await fetch(`${CONFIG.BACKEND_BASE_URL}/notice/${publicationNumber}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const detail = await response.json();
        
        // Отображаем детали
        detailRow.querySelector(".detail-cell").innerHTML = renderDetail(detail);
        
        // Настраиваем переключатель для полного описания
        const toggleBtn = detailRow.querySelector(".notice-toggle");
        const noticeContent = detailRow.querySelector(".notice-content");
        
        if (toggleBtn && noticeContent) {
            toggleBtn.addEventListener("click", () => {
                noticeContent.classList.toggle("open");
                toggleBtn.innerHTML = noticeContent.classList.contains("open")
                    ? '<i class="fas fa-chevron-up"></i> Скрыть полное описание'
                    : '<i class="fas fa-chevron-down"></i> Показать полное описание';
            });
        }
        
    } catch (error) {
        console.error("Error loading details:", error);
        detailRow.querySelector(".detail-cell").innerHTML = `
            <div class="alert alert-error">
                <i class="fas fa-exclamation-triangle"></i>
                Не удалось загрузить детали: ${error.message}
            </div>
        `;
    }
}

// Рендер деталей тендера
function renderDetail(detail) {
    return `
        <div class="detail-container">
            <!-- Прямая ссылка -->
            <div class="detail-section">
                <h3><i class="fas fa-external-link-alt"></i> Прямая ссылка на тендер</h3>
                <p>
                    <a href="${detail.direct_url}" target="_blank" rel="noopener noreferrer">
                        <i class="fas fa-external-link-alt"></i>
                        ${detail.direct_url}
                    </a>
                </p>
            </div>
            
            <!-- Краткая информация -->
            <div class="detail-section">
                <h3><i class="fas fa-info-circle"></i> Основная информация</h3>
                <div class="detail-grid">
                    <div class="detail-item">
                        <strong>Номер публикации</strong>
                        ${detail.publication_number || "—"}
                    </div>
                    <div class="detail-item">
                        <strong>Дата публикации</strong>
                        ${formatDate(detail.publication_date) || "—"}
                    </div>
                    <div class="detail-item">
                        <strong>Дедлайн подачи</strong>
                        ${formatDate(detail.deadline_date) || "—"}
                    </div>
                    <div class="detail-item">
                        <strong>Тип процедуры</strong>
                        ${detail.procedure_type || "—"}
                    </div>
                </div>
            </div>
            
            <!-- Заказчик -->
            <div class="detail-section">
                <h3><i class="fas fa-building"></i> Заказчик</h3>
                <div class="detail-grid">
                    <div class="detail-item">
                        <strong>Название</strong>
                        ${detail.buyer?.name || "—"}
                    </div>
                    <div class="detail-item">
                        <strong>Страна</strong>
                        ${detail.buyer?.country || "—"}
                    </div>
                    <div class="detail-item">
                        <strong>Город</strong>
                        ${detail.buyer?.city || "—"}
                    </div>
                    <div class="detail-item">
                        <strong>Email</strong>
                        ${detail.buyer?.email ? 
                            `<a href="mailto:${detail.buyer.email}">${detail.buyer.email}</a>` : 
                            "—"}
                    </div>
                </div>
            </div>
            
            <!-- Финансовая информация -->
            <div class="detail-section">
                <h3><i class="fas fa-euro-sign"></i> Финансовая информация</h3>
                <div class="detail-grid">
                    <div class="detail-item">
                        <strong>Ориентировочная стоимость</strong>
                        ${detail.estimated_value ? 
                            `${detail.estimated_value.toLocaleString()} ${detail.estimated_value_currency || "EUR"}` : 
                            "—"}
                    </div>
                    <div class="detail-item">
                        <strong>CPV код (SKU)</strong>
                        <code>${detail.cpv_code || "—"}</code>
                    </div>
                </div>
            </div>
            
            <!-- Полное описание -->
            <div class="detail-section">
                <button class="notice-toggle">
                    <i class="fas fa-chevron-down"></i> Показать полное описание
                </button>
                <div class="notice-content">
                    <h3><i class="fas fa-file-alt"></i> Полное описание тендера</h3>
                    <div class="notice-fields">
                        ${renderFullNotice(detail.full_notice)}
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Рендер полного описания
function renderFullNotice(fullNotice) {
    if (!fullNotice || typeof fullNotice !== 'object') {
        return '<div class="alert alert-info">Полное описание отсутствует</div>';
    }
    
    let html = '';
    
    for (const [key, value] of Object.entries(fullNotice)) {
        if (value !== null && value !== undefined) {
            html += `
                <div class="notice-field">
                    <strong>${key}:</strong>
                    <span>${String(value)}</span>
                </div>
            `;
        }
    }
    
    return html || '<div class="alert alert-info">Полное описание отсутствует</div>';
}

// Обновление пагинации
function updatePagination() {
    if (!elements.prevPage || !elements.nextPage || !elements.pageInfo) return;
    
    // Предыдущая страница
    elements.prevPage.disabled = currentPage <= 1;
    
    // Следующая страница
    elements.nextPage.disabled = currentPage >= totalPages;
    
    // Информация о странице
    elements.pageInfo.textContent = `Страница ${currentPage} из ${totalPages}`;
}

// Вспомогательные функции отображения
function showLoading(show) {
    if (elements.loadingSpinner) {
        elements.loadingSpinner.style.display = show ? "block" : "none";
    }
    if (elements.searchBtn) {
        elements.searchBtn.disabled = show;
    }
}

function showError(message) {
    if (elements.errorAlert) {
        elements.errorAlert.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            ${message}
        `;
        elements.errorAlert.style.display = "block";
    }
}

function hideError() {
    if (elements.errorAlert) {
        elements.errorAlert.style.display = "none";
    }
}

function showInfo(message) {
    if (elements.infoAlert) {
        elements.infoAlert.innerHTML = `
            <i class="fas fa-info-circle"></i>
            ${message}
        `;
        elements.infoAlert.style.display = "block";
    }
}

function hideInfo() {
    if (elements.infoAlert) {
        elements.infoAlert.style.display = "none";
    }
}

function showNoResults() {
    if (elements.emptyState) {
        elements.emptyState.style.display = "block";
    }
    if (elements.resultsSummary) {
        elements.resultsSummary.textContent = "Найдено: 0 тендеров";
    }
}

function hideEmptyState() {
    if (elements.emptyState) {
        elements.emptyState.style.display = "none";
    }
}

function showResults() {
    if (elements.resultsContainer) {
        elements.resultsContainer.style.display = "block";
    }
}

function hideResults() {
    if (elements.resultsContainer) {
        elements.resultsContainer.style.display = "none";
    }
}