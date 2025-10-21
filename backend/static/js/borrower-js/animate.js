document.addEventListener('DOMContentLoaded', function() {
    // Add tap feedback for mobile
    const actionCards = document.querySelectorAll('.hover\\:shadow-md');
    
    actionCards.forEach(card => {
        card.addEventListener('touchstart', function() {
            this.style.transform = 'scale(0.98)';
        });
        
        card.addEventListener('touchend', function() {
            this.style.transform = 'scale(1)';
        });
        
        card.addEventListener('click', function(e) {
            e.preventDefault();
            // Add haptic feedback if available
            if (navigator.vibrate) {
                navigator.vibrate(50);
            }
            console.log('Action tapped:', this.querySelector('h4').textContent);
        });
    });
    
    // Simple animation for loan balance
    const balance = document.querySelector('.text-3xl.font-bold');
    if (balance) {
        balance.style.opacity = '0';
        balance.style.transform = 'translateY(10px)';
        
        setTimeout(() => {
            balance.style.transition = 'all 0.5s ease-out';
            balance.style.opacity = '1';
            balance.style.transform = 'translateY(0)';
        }, 300);
    }
});