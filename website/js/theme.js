document.addEventListener('DOMContentLoaded', function() {
    const themeSwitcher = document.getElementById('theme-switcher');
    const html = document.documentElement;
    const disable_light_theme_flag = true;

    if (disable_light_theme_flag) {
        html.setAttribute('data-theme', 'dark');
        if (themeSwitcher) {
            themeSwitcher.style.display = 'none';
        }
        return;
    }

    // Set default theme to light if no theme is saved
    const savedTheme = localStorage.getItem('theme') || 'dark';
    html.setAttribute('data-theme', savedTheme);
    updateIcon(savedTheme);

    if (themeSwitcher) {
        themeSwitcher.addEventListener('click', () => {
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateIcon(newTheme);
        });
    }


    function updateIcon(theme) {
        if (themeSwitcher) {
            const icon = themeSwitcher.querySelector('i');
            if (theme === 'dark') {
                icon.classList.remove('fa-sun');
                icon.classList.add('fa-moon');
            } else {
                icon.classList.remove('fa-moon');
                icon.classList.add('fa-sun');
            }
        }
    }
});
