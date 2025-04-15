document.addEventListener('DOMContentLoaded', () => {
    // Confirmation for Delete Actions
    const deleteForms = document.querySelectorAll('.delete-form');
    deleteForms.forEach(form => {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            if (confirm('Are you sure you want to delete this item?')) {
                form.submit();
            }
        });
    });

    // Animate Cards on Load
    const cards = document.querySelectorAll('.stats-card, .management-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        setTimeout(() => {
            card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });

    // Example: Dynamic Filtering for Users (Add search input in HTML if needed)
    const usersGrid = document.getElementById('users-grid');
    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.placeholder = 'Search users...';
    searchInput.className = 'search-input';
    document.querySelector('.management-section:first-child .section-header').appendChild(searchInput);

    searchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        const userCards = usersGrid.querySelectorAll('.management-card');
        userCards.forEach(card => {
            const username = card.querySelector('p:nth-child(2)').textContent.toLowerCase();
            const email = card.querySelector('p:nth-child(3)').textContent.toLowerCase();
            if (username.includes(searchTerm) || email.includes(searchTerm)) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    });

    // Optional: Fetch real-time stats (requires backend API)
    /*
    async function fetchStats() {
        try {
            const response = await fetch('/api/dashboard-stats/');
            const data = await response.json();
            document.querySelector('.card-value-departments').textContent = data.total_departments;
            document.querySelector('.card-value-users').textContent = data.total_users;
            // Update other stats similarly
        } catch (error) {
            console.error('Error fetching stats:', error);
        }
    }
    fetchStats();
    */
});