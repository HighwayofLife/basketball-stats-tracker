/**
 * Player portrait utility functions
 * Shared module for rendering player portraits across the application
 */

/**
 * Get tiny player portrait HTML for box scores (32px)
 * @param {Object} player - Player object with thumbnail_image and name
 * @returns {string} HTML string for the portrait
 */
function getPlayerPortraitTiny(player) {
    // Construct portrait URL from thumbnail_image field
    const portraitUrl = player.thumbnail_image ? `/uploads/${player.thumbnail_image}` : null;
    
    if (portraitUrl && portraitUrl !== 'None') {
        return `<img class="rounded-circle"
                     src="${portraitUrl}"
                     alt="${player.name}"
                     style="width: 32px; height: 32px; object-fit: cover;"
                     onerror="this.onerror=null; this.outerHTML='<div class=\\'rounded-circle bg-light d-flex align-items-center justify-content-center\\' style=\\'width: 32px; height: 32px;\\'><i class=\\'fas fa-user text-muted\\' style=\\'font-size: 14px;\\'></i></div>';">`;                
    } else {
        return `<div class="rounded-circle bg-light d-flex align-items-center justify-content-center" style="width: 32px; height: 32px;">
                    <i class="fas fa-user text-muted" style="font-size: 14px;"></i>
                </div>`;
    }
}

/**
 * Get small player portrait HTML for rosters (40px)
 * @param {Object} player - Player object with thumbnail_image and name
 * @returns {string} HTML string for the portrait
 */
function getPlayerPortraitSmall(player) {
    const portraitUrl = player.thumbnail_image ? `/uploads/${player.thumbnail_image}` : null;
    
    if (portraitUrl && portraitUrl !== 'None') {
        return `<img class="rounded-circle"
                     src="${portraitUrl}"
                     alt="${player.name}"
                     style="width: 40px; height: 40px; object-fit: cover;"
                     onerror="this.onerror=null; this.outerHTML='<div class=\\'rounded-circle bg-light d-flex align-items-center justify-content-center\\' style=\\'width: 40px; height: 40px;\\'><i class=\\'fas fa-user text-muted\\' style=\\'font-size: 16px;\\'></i></div>';">`;                
    } else {
        return `<div class="rounded-circle bg-light d-flex align-items-center justify-content-center" style="width: 40px; height: 40px;">
                    <i class="fas fa-user text-muted" style="font-size: 16px;"></i>
                </div>`;
    }
}

/**
 * Get medium player portrait HTML for game leaders (50px)
 * @param {Object} player - Player object with thumbnail_image and name
 * @returns {string} HTML string for the portrait
 */
function getPlayerPortraitMedium(player) {
    const portraitUrl = player.thumbnail_image ? `/uploads/${player.thumbnail_image}` : null;
    
    if (portraitUrl && portraitUrl !== 'None') {
        return `<img src="${portraitUrl}" alt="${player.name}" style="width: 50px; height: 50px; border-radius: 50%; object-fit: cover;">`;
    } else {
        return `<div class="rounded-circle bg-light d-flex align-items-center justify-content-center" style="width: 50px; height: 50px;">
                    <i class="fas fa-user text-muted" style="font-size: 18px;"></i>
                </div>`;
    }
}

// Export functions for use in other modules if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        getPlayerPortraitTiny,
        getPlayerPortraitSmall,
        getPlayerPortraitMedium
    };
}