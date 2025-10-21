document.addEventListener('DOMContentLoaded', function () {
    const ctx = document.getElementById('loanApplicationsChart').getContext('2d');

    // Use backend data
    const dataSets = window.loanApplicationsChartData || {'7': [], '30': [], '90': []};
    let currentRange = '7';

    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: Array.from({length: dataSets[currentRange].length}, (_, i) => `Day ${i + 1}`),
            datasets: [{
                label: 'Applications',
                data: dataSets[currentRange],
                fill: true,
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderColor: 'rgba(16, 185, 129, 1)',
                tension: 0.4,
                pointRadius: 3,
                pointBackgroundColor: 'rgba(16, 185, 129, 1)',
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                title: { display: false }
            },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#64748b', font: { family: 'Poppins', size: 12 } } },
                y: { grid: { color: '#e5e7eb' }, ticks: { color: '#64748b', font: { family: 'Poppins', size: 12 } } }
            }
        }
    });

    document.querySelectorAll('.chart-range-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            currentRange = this.dataset.range;
            chart.data.labels = Array.from({length: dataSets[currentRange].length}, (_, i) => `Day ${i + 1}`);
            chart.data.datasets[0].data = dataSets[currentRange];
            chart.update();
            document.querySelectorAll('.chart-range-btn').forEach(b => {
                b.classList.remove('bg-green-100', 'text-green-600');
                b.classList.add('text-gray-600');
            });
            this.classList.add('bg-green-100', 'text-green-600');
            this.classList.remove('text-gray-600');
        });
    });
});