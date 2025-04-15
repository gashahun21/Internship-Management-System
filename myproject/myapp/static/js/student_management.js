document.addEventListener('DOMContentLoaded', function () {
    // Initialize tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-toggle="tooltip"]');
    tooltipTriggerList.forEach(tooltipTriggerEl => {
        new bootstrap.Tooltip(tooltipTriggerEl, {
            placement: 'top',
            delay: { show: 100, hide: 200 }
        });
    });

    // Handle delete confirmation
    const deleteButtons = document.querySelectorAll('.btn-danger');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function (e) {
            const confirmDelete = confirm('This will permanently delete the student record. Continue?');
            if (!confirmDelete) {
                e.preventDefault();
            }
        });
    });

    // Auto-refresh with user confirmation
    let refreshTimer;
    function startAutoRefresh() {
        refreshTimer = setTimeout(() => {
            const shouldRefresh = confirm('The page will refresh to show the latest data. Continue?');
            if (shouldRefresh) {
                window.location.reload();
            } else {
                startAutoRefresh();
            }
        }, 300000); // 5 minutes
    }

    // Start auto-refresh
    startAutoRefresh();

    // Reset timer on user interaction
    ['click', 'keydown', 'scroll'].forEach(event => {
        document.addEventListener(event, () => {
            clearTimeout(refreshTimer);
            startAutoRefresh();
        });
    });

    // Highlight active row on click
    const tableRows = document.querySelectorAll('.table tbody tr');
    tableRows.forEach(row => {
        row.addEventListener('click', function () {
            tableRows.forEach(r => r.classList.remove('table-active'));
            this.classList.add('table-active');
        });
    });

    // Animate buttons on hover
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('mouseenter', () => {
            button.style.transform = 'translateY(-2px)';
        });
        button.addEventListener('mouseleave', () => {
            button.style.transform = 'translateY(0)';
        });
    });
});