document.addEventListener('DOMContentLoaded', function () {
    const openBtn = document.getElementById('open-loan-modal');
    const modal = document.getElementById('new-loan-modal');
    const cancelBtn = document.getElementById('cancel-loan-modal');
    const form = document.getElementById('new-loan-form');

    if (openBtn && modal) {
        openBtn.addEventListener('click', function (e) {
            e.preventDefault();
            modal.classList.remove('hidden');
            document.body.classList.add('modal-open');
        });
    }
    if (cancelBtn && modal) {
        cancelBtn.addEventListener('click', function () {
            modal.classList.add('hidden');
            document.body.classList.remove('modal-open');
        });
    }
    if (form) {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            // TODO: AJAX submit or redirect to Django view for processing
            alert('Loan product created!');
            modal.classList.add('hidden');
            document.body.classList.remove('modal-open');
        });
    }
});