// static/js/avatar_colors.js
document.addEventListener('DOMContentLoaded', function() {
    const avatarElements = document.querySelectorAll('.avatar-initials');

    // Define a palette of nice background colors
    const colors = [
        '#ef4444', '#f97316', '#f59e0b', '#eab308', '#84cc16', '#22c55e',
        '#10b981', '#06b6d4', '#0ea5e9', '#3b82f6', '#6366f1', '#8b5cf6',
        '#a855f7', '#d946ef', '#ec4899', '#f43f5e'
    ];

    avatarElements.forEach(element => {
        const name = element.getAttribute('data-name');
        if (name) {
            // Simple hash function to get a character code sum
            let hash = 0;
            for (let i = 0; i < name.length; i++) {
                hash = ((hash << 5) - hash) + name.charCodeAt(i); // More distributed hash
                hash |= 0; // Convert to 32bit integer
            }
            // Use modulo to pick a color from the palette
            const colorIndex = Math.abs(hash) % colors.length; // Use Math.abs for positive index
            element.style.backgroundColor = colors[colorIndex];

            // Optional: Determine text color (light/dark) based on background
            const bgColor = colors[colorIndex];
            // Ensure hex format #RRGGBB
            const hex = bgColor.charAt(0) === '#' ? bgColor.substring(1, 7) : bgColor;
            const r = parseInt(hex.substring(0, 2), 16);
            const g = parseInt(hex.substring(2, 4), 16);
            const b = parseInt(hex.substring(4, 6), 16);
            const brightness = (r * 299 + g * 587 + b * 114) / 1000;
            element.style.color = brightness > 150 ? '#333333' : '#ffffff'; // Dark text on light bg, light text on dark bg
        }
    });
});