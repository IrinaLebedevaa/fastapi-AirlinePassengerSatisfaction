let currentFlightData = null;

const urlParams = new URLSearchParams(window.location.search);
const flightId = urlParams.get('flight_id');

document.addEventListener('DOMContentLoaded', function () {
    console.log('Script started');
    console.log('Flight ID from URL:', flightId);

    if (flightId) {
        loadFlightData(flightId);
    } else {
        showError('Flight not selected. Return to main page.');
        document.getElementById('criticalItems').innerHTML = '<p> Flight not selected</p>';
    }
});


async function loadFlightData(flightID){
    showLoading(true);

    try{
        const response = await fetch(`/api/flight/${flightID}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Flight data received:', data);

        if (data) {
            currentFlightData = data;
            updateFlightInfo(data);
        } else {
            showError('Failed to load flight data');
        }
    }catch (error) {
        console.error('Error loading flight data: ', error);
        showError('Error loading data');
    } finally {
        showLoading(false);
    }
}

function updateFlightInfo(flightData) {
    // Обновляем заголовок с номером рейса и маршрутом
    const flightTitle = document.getElementById('flightTitle');
    if (flightTitle) {
        const flightNumber = flightData.flight_number || '?';
        const origin = flightData.origin || '?';
        const destination = flightData.destination || '?';
        flightTitle.textContent = `✈️ Flight: ${flightNumber} | ${origin} → ${destination}`;
    }
// Обновляем время
    const departureEl = document.getElementById('departureTime');
    const arrivalEl = document.getElementById('arrivalTime');

    if (departureEl) departureEl.textContent = formatTime(flightData.departure_time);
    if (arrivalEl) arrivalEl.textContent = formatTime(flightData.arrival_time);

    // Создаем диаграмму удовлетворенности
    if (flightData.satisfaction_data) {
        createSatisfactionChart(flightData.satisfaction_data);
    }

    // Отображаем критические отметки (только минимальные, ниже 3)
    if (flightData.critical_marks && flightData.critical_marks.minimum) {
        displayCriticalMarks(flightData.critical_marks.minimum);
    } else if (flightData.low_metrics) {
        // Альтернативный формат
        const lowArray = Object.entries(flightData.low_metrics).map(([name, value]) => ({
            name: name,
            value: value
        }));
        displayCriticalMarks(lowArray);
    } else {
        const container = document.getElementById('criticalItems');
        if (container) {
            container.innerHTML = '<p>✅No critical marks</p>';
        }
    }
}

// СОЗДАНИЕ КРУГОВОЙ ДИАГРАММЫ
async function createSatisfactionChart(satisfactionData){
    const canvas = document.getElementById('satisfactionChart');
    if (!canvas) {
        console.error('Canvas not found');
        return;
    }

    const ctx = canvas.getContext('2d');

    if (window.satisfactionChart){
        window.satisfactionChart.destroy();
    }

    const satisfied = satisfactionData.satisfied || 0;
    const neutral = satisfactionData.neutral || 0;
    const unsatisfied = satisfactionData.unsatisfied || 0;

    // Если нейтральных нет, показываем только 2 категории
    let labels, data, colors;
    if (neutral === 0) {
        labels = ['Satisfied', 'Not satisfied'];
        data = [satisfied, unsatisfied];
        colors = ['#4caf50', '#f44336'];
    } else {
        labels = ['Satisfied', 'Neutral', 'Dissatisfied'];
        data = [satisfied, neutral, unsatisfied];
        colors = ['#4caf50', '#ffc107', '#f44336'];
    }


    window.satisfactionChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins:{
                legend: {
                    position: 'bottom',
                    labels: { font: { size: 14 } }
                },
                tooltip:{
                    callbacks: {
                        label: function (context){
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// ОТОБРАЖЕНИЕ КРИТИЧЕСКИХ ОТМЕТОК (только минимальные, ниже 3)
function displayCriticalMarks(criticalItems){
    const container = document.getElementById('criticalItems');
    if (!container) return;

    container.innerHTML = '';

    if (!criticalItems || criticalItems.length === 0){
        container.innerHTML = '<p>✅ No critical marks</p>';
        return;
    }

    criticalItems.forEach(item => {
        const card = createCriticalCard(item.name, item.value, 'min');
        container.appendChild(card);
    });
}

// СОЗДАНИЕ КАРТОЧКИ ДЛЯ ОТМЕТКИ
function createCriticalCard(name, value, type){
    const div = document.createElement('div');
    div.className = `critical-card ${type}`;

    const nameSpan = document.createElement('span');
    nameSpan.className = 'critical-name';
    nameSpan.textContent = name;

    const valueSpan = document.createElement('span');
    valueSpan.className = `critical-value ${type}`;
    valueSpan.textContent = value.toFixed(1);

    div.appendChild(nameSpan);
    div.appendChild(valueSpan);

    return div;
}

// ФОРМАТИРОВАНИЕ ВРЕМЕНИ
function formatTime(timeString) {
    if (!timeString) return 'Not specified';

    // Если это уже строка в формате "HH:MM:SS"
    if (typeof timeString === 'string' && timeString.includes(':')) {
        return timeString;
    }

    // Если это объект Date или timestamp
    try {
        const date = new Date(timeString);
        if (!isNaN(date.getTime())) {
            return date.toLocaleString('ru-RU', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    } catch(e) {
        console.error('Error formatting time:', e);
    }

    return String(timeString);
}

// ПОКАЗАТЬ/СКРЫТЬ ЗАГРУЗКУ
function showLoading(show) {
    const loader = document.getElementById('loader');
    if (loader) {
        loader.style.display = show ? 'block' : 'none';
    }
}

// ПОКАЗАТЬ ОШИБКУ
function showError(message) {
    const errorDiv = document.getElementById('errorMessage');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
    }
}