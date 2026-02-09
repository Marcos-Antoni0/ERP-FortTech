from __future__ import annotations

from urllib.parse import quote


def generate_whatsapp_message(order) -> str:
    """Gera mensagem de WhatsApp a partir do pedido."""
    settings = order.company.catalog_settings
    template = settings.custom_message_template

    items_list = '\n'.join(
        [
            f'- {item["quantity"]}x {item["product_name"]} - R$ {item["subtotal"]:.2f}'
            for item in order.items
        ]
    )

    message = template.format(
        customer_name=order.customer_name,
        order_number=order.order_number,
        items=items_list,
        total=f'R$ {order.total_value:.2f}',
        notes=order.customer_notes or 'Nenhuma observacao',
    )
    return message


def format_whatsapp_number(number: str) -> str:
    """Normaliza numero para formato internacional sem simbolos."""
    digits = ''.join(filter(str.isdigit, number))
    if not digits.startswith('55') and len(digits) <= 11:
        digits = f'55{digits}'
    return digits


def get_whatsapp_url(order) -> str:
    """Monta URL do WhatsApp com mensagem formatada."""
    number = format_whatsapp_number(order.company.catalog_settings.whatsapp_number)
    message = generate_whatsapp_message(order)
    encoded = quote(message)
    return f'https://wa.me/{number}?text={encoded}'
