function showBulkActionsModal() {
    document.getElementById('bulk-actions-modal').classList.remove('hidden');
    document.body.classList.add('modal-open'); // Optional: prevent background scroll
}

function hideBulkActionsModal() {
    document.getElementById('bulk-actions-modal').classList.add('hidden');
    document.body.classList.remove('modal-open');
}