/**
 * Product detail page: swap the main gallery image when a thumbnail is
 * clicked. Kept dependency-free and scoped to the gallery container.
 */
(() => {
    'use strict';

    const gallery = document.getElementById('product-gallery');
    if (!gallery) return;

    const mainImage = document.getElementById('gallery-main');
    const thumbs = gallery.querySelectorAll('.gallery-thumb');
    if (!mainImage || thumbs.length === 0) return;

    gallery.addEventListener('click', (event) => {
        const thumb = event.target.closest('.gallery-thumb');
        if (!thumb) return;
        mainImage.src = thumb.dataset.full;
        mainImage.alt = thumb.alt;
    });
})();
