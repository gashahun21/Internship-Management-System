// static/js/admin_dashboard_features.js (or your admin_dashboard.js)

document.addEventListener('DOMContentLoaded', function() {
    'use strict';

    const searchInput = document.getElementById('dashboard-search');
    const sectionsToSearch = [
        { listId: 'users-list', itemSelector: '.list-item-card', noResultsSelector: '#users-list .search-no-results', defaultNoDataSelector: '#users-list .default-no-data' },
        { listId: 'departments-list', itemSelector: '.list-item-card', noResultsSelector: '#departments-list .search-no-results', defaultNoDataSelector: '#departments-list .default-no-data' },
        { listId: 'companies-list', itemSelector: '.list-item-card', noResultsSelector: '#companies-list .search-no-results', defaultNoDataSelector: '#companies-list .default-no-data' }
    ];

    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = searchInput.value.toLowerCase().trim();

            sectionsToSearch.forEach(sectionConfig => {
                const listContainer = document.getElementById(sectionConfig.listId);
                if (!listContainer) {
                    console.warn(`Search: List container #${sectionConfig.listId} not found.`);
                    return;
                }

                const items = listContainer.querySelectorAll(sectionConfig.itemSelector);
                const noResultsMsg = listContainer.querySelector(sectionConfig.noResultsSelector);
                const defaultNoDataMsg = listContainer.querySelector(sectionConfig.defaultNoDataSelector);
                let visibleCount = 0;

                items.forEach(item => {
                    const searchableText = item.dataset.searchableText || '';
                    const isMatch = searchableText.includes(searchTerm);

                    // --- CORRECTED LINE ---
                    item.style.display = isMatch ? '' : 'none'; // If it's a match, revert to CSS display (should be flex), otherwise hide it.

                    if (isMatch) {
                        visibleCount++;
                    }
                });

                const hasItemsInitially = items.length > 0; // Check if there were items before filtering
                const isSearching = searchTerm !== '';

                if (noResultsMsg) {
                    noResultsMsg.style.display = (hasItemsInitially && visibleCount === 0 && isSearching) ? 'block' : 'none';
                }
                if (defaultNoDataMsg) {
                    // Show default "no data" if there are no items AT ALL, and we are NOT searching OR if we are searching but found nothing.
                    // Or, more simply, if there are no visible items and we are not specifically showing the "search no results" message.
                    const showDefaultNoData = (visibleCount === 0 && (!isSearching || (isSearching && noResultsMsg && noResultsMsg.style.display === 'none')));
                    defaultNoDataMsg.style.display = showDefaultNoData ? 'block' : 'none';
                }
            });
        });
    } else {
        console.warn("Search input 'dashboard-search' not found.");
    }

    // --- Collapse/Expand Functionality ---
    const toggleButtons = document.querySelectorAll('.section-toggle-btn');

    toggleButtons.forEach(button => {
        const targetSelector = button.dataset.target;
        const targetElement = document.querySelector(targetSelector);
        const parentSection = button.closest('.management-section');
        const icon = button.querySelector('i');

        if (!targetElement || !parentSection || !icon) {
             console.warn("Missing elements for toggle button:", button, "Target:", targetSelector);
             return;
        }

        const toggleSection = () => {
            const isCollapsed = parentSection.classList.toggle('collapsed');
            icon.classList.toggle('fa-minus', !isCollapsed);
            icon.classList.toggle('fa-plus', isCollapsed);
            button.setAttribute('aria-expanded', String(!isCollapsed));
            button.title = isCollapsed ? button.title.replace("Toggle", "Expand").replace("Collapse", "Expand") : button.title.replace("Expand", "Toggle").replace("Collapse", "Toggle");
        };

        button.addEventListener('click', toggleSection);

        // Set initial state based on class and update title
        const initiallyCollapsed = parentSection.classList.contains('collapsed');
        button.setAttribute('aria-expanded', String(!initiallyCollapsed));
        icon.classList.toggle('fa-minus', !initiallyCollapsed);
        icon.classList.toggle('fa-plus', initiallyCollapsed);
        button.title = initiallyCollapsed ? button.title.replace("Toggle", "Expand").replace("Collapse", "Expand") : button.title.replace("Expand", "Toggle").replace("Collapse", "Toggle");
    });

    // Add transition class AFTER initial setup to avoid animation on load
    setTimeout(() => {
        document.querySelectorAll('.item-list-container').forEach(container => {
            if (container) { // Check if container exists
                container.classList.add('transition-active');
            }
        });
    }, 100);

    console.log("Admin dashboard JS initialized with search and collapse.");
});


// pagination



    // Pagination for Users Section
    (function() {
        const usersList = document.querySelector('#users-list');
        const userCards = Array.from(usersList.querySelectorAll('.list-item-card'));
        const prevPageBtn = document.querySelector('#prev-page');
        const nextPageBtn = document.querySelector('#next-page');
        const currentPageSpan = document.querySelector('#current-page');
        const totalPagesSpan = document.querySelector('#total-pages');
        const itemsPerPage = 10;
        let currentPage = 1;

        // Calculate total pages
        const totalPages = Math.ceil(userCards.length / itemsPerPage);
        totalPagesSpan.textContent = totalPages;

        // Function to display users for the current page
        function displayPage(page) {
            // Hide all user cards
            userCards.forEach(card => card.style.display = 'none');

            // Calculate start and end indices
            const start = (page - 1) * itemsPerPage;
            const end = start + itemsPerPage;

            // Show only the cards for the current page
            userCards.slice(start, end).forEach(card => card.style.display = 'flex');

            // Update current page display
            currentPageSpan.textContent = page;

            // Update button states
            prevPageBtn.disabled = page === 1;
            nextPageBtn.disabled = page === totalPages;
        }

        // Initial page load
        if (userCards.length > 0) {
            displayPage(currentPage);
        } else {
            prevPageBtn.disabled = true;
            nextPageBtn.disabled = true;
        }

        // Event listeners for pagination buttons
        prevPageBtn.addEventListener('click', () => {
            if (currentPage > 1) {
                currentPage--;
                displayPage(currentPage);
            }
        });

        nextPageBtn.addEventListener('click', () => {
            if (currentPage < totalPages) {
                currentPage++;
                displayPage(currentPage);
            }
        });

        // Enhance search functionality to reset pagination
        const searchInput = document.querySelector('#dashboard-search');
        searchInput.addEventListener('input', () => {
            const searchTerm = searchInput.value.toLowerCase();
            userCards.forEach(card => {
                const searchableText = card.dataset.searchableText.toLowerCase();
                card.style.display = searchableText.includes(searchTerm) ? 'flex' : 'none';
            });

            // Update visible cards and reset pagination
            const visibleCards = userCards.filter(card => card.style.display === 'flex');
            const newTotalPages = Math.ceil(visibleCards.length / itemsPerPage);
            totalPagesSpan.textContent = newTotalPages || 1;
            currentPage = 1;
            displayPage(currentPage);

            // Show/hide no results message
            const noResults = document.querySelector('.search-no-results');
            noResults.style.display = visibleCards.length === 0 ? 'block' : 'none';
        });

        // Toggle section visibility
        document.querySelectorAll('.section-toggle-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const targetId = btn.dataset.target;
                const target = document.querySelector(targetId);
                const isExpanded = btn.getAttribute('aria-expanded') === 'true';
                target.style.display = isExpanded ? 'none' : 'block';
                btn.setAttribute('aria-expanded', !isExpanded);
                btn.querySelector('i').classList.toggle('fa-minus', isExpanded);
                btn.querySelector('i').classList.toggle('fa-plus', !isExpanded);
            });
        });
    })();
