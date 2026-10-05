(() => {
    const path = window.location.pathname.toLowerCase();
    const surface = path.startsWith('/orders/') ? 'orders'
        : path.startsWith('/inventory/') ? 'inventory'
            : path.startsWith('/billing/') ? 'billing'
                : path.startsWith('/deliveries/') ? 'deliveries'
                    : path.startsWith('/clients/') ? 'clients'
                        : path.startsWith('/complaints/') ? 'support'
                            : path.startsWith('/admin/') || path.startsWith('/dashboards/admin/') ? 'admin'
                                : path.startsWith('/dashboards/') ? 'dashboard'
                                    : path.startsWith('/accounts/') ? 'accounts'
                                        : path.startsWith('/products/') ? 'catalog'
                                            : path === '/' ? 'home' : 'dashboard';
    document.body.dataset.surface = surface;

    const sharedStylesheetUrl = '/static/dashboards/css/aquaflow-visuals.css?v=20261004';
    let sharedStylesheet = document.querySelector('link[href*="aquaflow-visuals.css"]');
    if (!sharedStylesheet) {
        const sharedStylesheet = document.createElement('link');
        sharedStylesheet.rel = 'stylesheet';
        sharedStylesheet.href = sharedStylesheetUrl;
        document.head.append(sharedStylesheet);
    } else if (!sharedStylesheet.href.includes('?v=20261004')) {
        sharedStylesheet.href = sharedStylesheetUrl;
    }

    const style = document.createElement('style');
    style.textContent = `
        .site-page-loader {
            position: fixed;
            z-index: 2147483000;
            inset: 0;
            display: grid;
            place-content: center;
            gap: .8rem;
            color: #173b3b;
            background: rgba(242, 247, 244, .96);
            opacity: 1;
            visibility: visible;
            transition: opacity .22s ease, visibility .22s ease;
            pointer-events: all;
        }
        .site-page-loader.is-hidden {
            opacity: 0;
            visibility: hidden;
            pointer-events: none;
        }
        .site-page-loader__spinner {
            width: 2.4rem;
            height: 2.4rem;
            justify-self: center;
            border: 3px solid rgba(8, 117, 104, .2);
            border-top-color: #087568;
            border-radius: 50%;
            animation: site-loader-spin .72s linear infinite;
        }
        .site-page-loader__label {
            font: 600 .78rem/1.2 'Trebuchet MS', sans-serif;
        }
        @keyframes site-loader-spin { to { transform: rotate(360deg); } }
        @supports (content-visibility: auto) {
            main > section:not(:first-child),
            main > .table-wrap,
            .request-card {
                content-visibility: auto;
                contain-intrinsic-size: auto 340px;
            }
        }
        @media (prefers-reduced-motion: reduce) {
            .site-page-loader { transition: none; }
            .site-page-loader__spinner { animation: none; }
        }
    `;
    document.head.append(style);

    const loader = document.createElement('div');
    loader.className = 'site-page-loader';
    loader.setAttribute('role', 'status');
    loader.setAttribute('aria-live', 'polite');
    loader.innerHTML = '<span class="site-page-loader__spinner" aria-hidden="true"></span><span class="site-page-loader__label">Loading</span>';
    document.body.append(loader);

    const hideLoader = () => loader.classList.add('is-hidden');
    const showLoader = () => {
        loader.classList.remove('is-hidden');
        window.setTimeout(hideLoader, 8000);
    };

    window.addEventListener('load', () => window.setTimeout(hideLoader, 120), { once: true });
    window.addEventListener('pageshow', hideLoader);
    window.setTimeout(hideLoader, 3000);

    document.addEventListener('click', (event) => {
        const link = event.target.closest('a[href]');
        if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        if (link.target === '_blank' || link.hasAttribute('download')) return;

        const destination = new URL(link.href, window.location.href);
        if (destination.origin !== window.location.origin) return;
        if (destination.pathname === window.location.pathname && destination.search === window.location.search && destination.hash) return;
        showLoader();
    });

    document.addEventListener('submit', (event) => {
        if (!event.target.matches('form')) return;
        showLoader();
    });

    const media = document.querySelectorAll('img:not([data-no-lazy]), iframe:not([data-no-lazy])');
    media.forEach((element) => {
        const bounds = element.getBoundingClientRect();
        element.loading = bounds.top < window.innerHeight + 160 ? 'eager' : 'lazy';
        if (element.tagName === 'IMG') element.decoding = 'async';
    });

    const deferredMedia = document.querySelectorAll('[data-src], [data-srcset]');
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries, activeObserver) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                const element = entry.target;
                if (element.dataset.src) element.src = element.dataset.src;
                if (element.dataset.srcset) element.srcset = element.dataset.srcset;
                element.removeAttribute('data-src');
                element.removeAttribute('data-srcset');
                activeObserver.unobserve(element);
            });
        }, { rootMargin: '240px 0px' });
        deferredMedia.forEach((element) => observer.observe(element));
    } else {
        deferredMedia.forEach((element) => {
            if (element.dataset.src) element.src = element.dataset.src;
            if (element.dataset.srcset) element.srcset = element.dataset.srcset;
        });
    }
})();
