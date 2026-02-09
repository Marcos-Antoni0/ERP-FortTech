const getCookie = (name) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
        return parts.pop().split(';').shift();
    }
    return '';
};

const showCartModal = () => {
    const modal = document.getElementById('cart-modal');
    if (!modal) return;
    modal.classList.add('show');
    modal.style.display = 'block';
    modal.removeAttribute('aria-hidden');
};

const hideCartModal = () => {
    const modal = document.getElementById('cart-modal');
    if (!modal) return;
    modal.classList.remove('show');
    modal.style.display = 'none';
    modal.setAttribute('aria-hidden', 'true');
};

document.addEventListener('click', (event) => {
    if (event.target.matches('[data-cart-close]')) {
        hideCartModal();
    }
});

document.addEventListener('submit', async (event) => {
    const form = event.target;
    if (!form.matches('.add-to-cart-form')) return;
    event.preventDefault();
    const url = form.action;
    const formData = new FormData(form);
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: formData,
    });
    if (response.ok) {
        showCartModal();
    } else {
        form.submit();
    }
});
