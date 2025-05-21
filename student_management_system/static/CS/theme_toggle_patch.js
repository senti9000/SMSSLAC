function toggleLocalStorage() {
    const isDark = localStorage.getItem('dark-theme') === 'true';
    localStorage.setItem('dark-theme', !isDark);
}

function toggleRootClass() {
    document.documentElement.classList.toggle('dark-theme');
}

document.addEventListener('DOMContentLoaded', function() {
    // Apply theme on page load based on localStorage
    if (localStorage.getItem('dark-theme') === 'true') {
        document.documentElement.classList.add('dark-theme');
    } else {
        document.documentElement.classList.remove('dark-theme');
    }

    const themeToggleBtn = document.querySelector(".theme-toggle");
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener("click", () => {
            toggleLocalStorage();
            toggleRootClass();
        });
    } else {
        console.error('Theme toggle button not found');
    }
});

