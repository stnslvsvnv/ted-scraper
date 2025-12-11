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
                current
