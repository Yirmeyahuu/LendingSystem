document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.chart-range-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.chart-range-btn').forEach(b => {
                b.classList.remove('bg-green-100', 'text-green-600');
                b.classList.add('text-gray-600');
            });
            this.classList.add('bg-green-100', 'text-green-600');
            this.classList.remove('text-gray-600');
            // Optionally update chart data here
        });
    });
});