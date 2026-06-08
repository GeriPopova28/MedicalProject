document.addEventListener('DOMContentLoaded', () => {
    const mobileToggle = document.querySelector('.mobile-toggle');
    const patientSidebar = document.getElementById('patientSidebar');

    if (mobileToggle && patientSidebar) {
        // Отваряне / Затваряне при клик на бутона
        mobileToggle.addEventListener('click', (e) => {
            e.stopPropagation(); 
            patientSidebar.classList.toggle('open');
            
            if (patientSidebar.classList.contains('open')) {
                mobileToggle.innerHTML = '✕';
            } else {
                mobileToggle.innerHTML = '☰';
            }
        });

        document.addEventListener('click', (e) => {
            if (!patientSidebar.contains(e.target) && patientSidebar.classList.contains('open')) {
                patientSidebar.classList.remove('open');
                mobileToggle.innerHTML = '☰';
            }
        });
    }
});