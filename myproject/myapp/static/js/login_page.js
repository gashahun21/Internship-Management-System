document.addEventListener('DOMContentLoaded', () => {
    // Handle floating label behavior
    const inputs = document.querySelectorAll('.input-group input');

    inputs.forEach(input => {
        const toggleClass = () => {
            input.classList.toggle('has-value', input.value.trim() !== '');
        };

        // Initialize class on load
        toggleClass();

        // Add listener for input changes
        input.addEventListener('input', toggleClass);
    });

    // Password visibility toggle logic
    const passwordInput = document.getElementById('id_password');
    const toggleIcon = document.querySelector('.password-toggle-icon i'); // Assumes <span class="password-toggle-icon"><i class="..."></i></span>

    if (passwordInput && toggleIcon) {
        const toggleWrapper = toggleIcon.closest('.password-toggle-icon');

        toggleWrapper.addEventListener('click', () => {
            const isPasswordVisible = passwordInput.type === 'text';
            passwordInput.type = isPasswordVisible ? 'password' : 'text';

            // Toggle icon classes
            toggleIcon.classList.toggle('fa-eye', isPasswordVisible);
            toggleIcon.classList.toggle('fa-eye-slash', !isPasswordVisible);
        });
    }
});
