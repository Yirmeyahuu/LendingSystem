// Global variables to track the current action
let currentAction = null;
let currentApplicationId = null;

/**
 * Show confirmation modal for approve/reject actions
 * @param {string} action - 'approve' or 'reject'
 * @param {number} applicationId - The loan application ID
 */
function showConfirmationModal(action, applicationId) {
    currentAction = action;
    currentApplicationId = applicationId;
    
    const modal = document.getElementById('confirmationModal');
    const title = document.getElementById('confirmationModalTitle');
    const message = document.getElementById('confirmationModalMessage');
    const confirmBtn = document.getElementById('confirmActionBtn');
    const icon = document.getElementById('confirmationModalIcon');
    
    // Set modal content based on action
    if (action === 'approve') {
        title.textContent = 'Approve Loan Application';
        message.textContent = 'Are you sure you want to approve this loan application? This action cannot be undone.';
        confirmBtn.className = 'px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-semibold shadow-lg';
        confirmBtn.innerHTML = '<i class="fas fa-check mr-2"></i>Yes, Approve';
        icon.className = 'fas fa-check-circle text-green-600 text-6xl mb-4';
    } else if (action === 'reject') {
        title.textContent = 'Reject Loan Application';
        message.textContent = 'Are you sure you want to reject this loan application? This action cannot be undone.';
        confirmBtn.className = 'px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-semibold shadow-lg';
        confirmBtn.innerHTML = '<i class="fas fa-times mr-2"></i>Yes, Reject';
        icon.className = 'fas fa-times-circle text-red-600 text-6xl mb-4';
    }
    
    // Show modal
    modal.classList.remove('hidden');
}

/**
 * Close the confirmation modal
 */
function closeConfirmationModal() {
    const modal = document.getElementById('confirmationModal');
    modal.classList.add('hidden');
    currentAction = null;
    currentApplicationId = null;
}

/**
 * Confirm the action and submit the form
 */
function confirmAction() {
    if (!currentAction || !currentApplicationId) {
        console.error('No action or application ID set');
        return;
    }
    
    // Create and submit a form
    const form = document.createElement('form');
    form.method = 'POST';
    
    if (currentAction === 'approve') {
        form.action = `/Company/Loan-Applications/${currentApplicationId}/approve/`;
    } else if (currentAction === 'reject') {
        form.action = `/Company/Loan-Applications/${currentApplicationId}/reject/`;
    }
    
    // Add CSRF token
    const csrfToken = getCookie('csrftoken');
    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrfmiddlewaretoken';
    csrfInput.value = csrfToken;
    form.appendChild(csrfInput);
    
    // Add form to body and submit
    document.body.appendChild(form);
    form.submit();
}

/**
 * Get CSRF token from cookies
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Close modal when clicking outside
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('confirmationModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeConfirmationModal();
            }
        });
    }
    
    // Close modal on ESC key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const modal = document.getElementById('confirmationModal');
            if (modal && !modal.classList.contains('hidden')) {
                closeConfirmationModal();
            }
        }
    });
});