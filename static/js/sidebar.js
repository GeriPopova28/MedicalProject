document.addEventListener('DOMContentLoaded', () => {
    const navToggle = document.querySelector('.mobile-nav-toggle');
    const sidebar = document.getElementById('sidebar');

    if (navToggle && sidebar) {
        // Превключване на менюто при клик върху бутона
        navToggle.addEventListener('click', () => {
            sidebar.classList.toggle('active');
            
            // Сменя иконата на бутона от ☰ на ✕ при отворено меню
            if (sidebar.classList.contains('active')) {
                navToggle.innerHTML = '✕';
            } else {
                navToggle.innerHTML = '☰';
            }
        });

        // Затваряне на менюто, ако се кликне извън него (в основното съдържание)
        document.addEventListener('click', (event) => {
            if (!sidebar.contains(event.target) && !navToggle.contains(event.target)) {
                sidebar.classList.remove('active');
                navToggle.innerHTML = '☰';
            }
        });
    }
});