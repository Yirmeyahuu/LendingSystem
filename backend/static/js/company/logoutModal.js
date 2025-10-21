function showLogoutModal(e) {
    e.preventDefault();
    document.getElementById('logout-modal').classList.remove('hidden');
}

window.addEventListener('DOMContentLoaded', function() {
    const cancelBtn = document.getElementById('cancel-logout');
    if (cancelBtn) {
        cancelBtn.onclick = function() {
            document.getElementById('logout-modal').classList.add('hidden');
        };
    }
});