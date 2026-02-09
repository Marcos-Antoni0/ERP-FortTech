(() => {
    const containers = document.querySelectorAll('.infinite-scroll');
    if (!containers.length) {
        return;
    }

    const buildNextUrl = (baseUrl, nextPage) => {
        const url = new URL(baseUrl, window.location.origin);
        url.searchParams.set('page', nextPage);
        return url.toString();
    };

    const attachObserver = (container) => {
        const sentinel = container.nextElementSibling;
        if (!sentinel || !sentinel.classList.contains('infinite-scroll-sentinel')) {
            return;
        }

        let loading = false;

        const observer = new IntersectionObserver(async (entries) => {
            const entry = entries[0];
            if (!entry.isIntersecting || loading) {
                return;
            }

            const hasNext = container.dataset.hasNext === '1';
            const nextPage = container.dataset.nextPage;
            if (!hasNext || !nextPage) {
                observer.disconnect();
                return;
            }

            loading = true;
            sentinel.classList.add('is-loading');

            try {
                const response = await fetch(buildNextUrl(container.dataset.baseUrl, nextPage), {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                });
                if (!response.ok) {
                    observer.disconnect();
                    return;
                }
                const payload = await response.json();
                if (payload.html) {
                    container.insertAdjacentHTML('beforeend', payload.html);
                }
                container.dataset.hasNext = payload.has_next ? '1' : '0';
                container.dataset.nextPage = payload.next_page || '';
                if (!payload.has_next) {
                    observer.disconnect();
                }
            } catch (error) {
                observer.disconnect();
            } finally {
                loading = false;
                sentinel.classList.remove('is-loading');
            }
        }, { rootMargin: '200px' });

        observer.observe(sentinel);
    };

    containers.forEach((container) => {
        if (!container.dataset.baseUrl) {
            container.dataset.baseUrl = window.location.href;
        }
        attachObserver(container);
    });
})();
