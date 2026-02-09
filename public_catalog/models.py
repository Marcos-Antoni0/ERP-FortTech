from __future__ import annotations

from io import BytesIO
from typing import Any

from ckeditor.fields import RichTextField
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from PIL import Image

from p_v_App.models import Category, Products, Sales
from p_v_App.models_tenant import Company, TenantManager, TenantMixin


class CatalogSettings(TenantMixin):
    """Configurações do catálogo público por empresa."""

    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name='catalog_settings',
        verbose_name='Empresa',
    )

    catalog_enabled = models.BooleanField(
        default=False,
        verbose_name='Catálogo Habilitado',
    )
    catalog_slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name='URL do Catálogo',
        help_text='URL única para acesso público (ex: pizzaria-do-joao)',
    )
    catalog_title = models.CharField(
        max_length=200,
        verbose_name='Título do Catálogo',
    )
    catalog_description = models.TextField(
        blank=True,
        verbose_name='Descrição',
    )

    whatsapp_number = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='Número de telefone inválido. Use formato internacional.',
            ),
        ],
        verbose_name='Número WhatsApp',
    )
    custom_message_template = models.TextField(
        default=(
            'Olá! Sou {customer_name} e gostaria de fazer um pedido.\n\n'
            '📋 Pedido #{order_number}\n\n'
            '🛒 Itens:\n{items}\n\n'
            '💰 Total: {total}\n\n'
            '📝 Observações:\n{notes}\n\n'
            'Aguardo confirmação!'
        ),
        verbose_name='Template da Mensagem',
        help_text='Variáveis: {customer_name}, {order_number}, {items}, {total}, {notes}',
    )

    display_prices = models.BooleanField(
        default=True,
        verbose_name='Exibir Preços',
    )
    primary_color = models.CharField(
        max_length=7,
        default='#002d6c',
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message='Código de cor hexadecimal inválido',
            ),
        ],
        verbose_name='Cor Primária',
    )
    logo = models.ImageField(
        upload_to='catalog_logos/',
        blank=True,
        null=True,
        verbose_name='Logo',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        verbose_name = 'Configuração do Catálogo'
        verbose_name_plural = 'Configurações do Catálogo'

    def __str__(self) -> str:
        return f'Catálogo: {self.catalog_title}'


class CatalogCategory(TenantMixin):
    """Extensão de Category para catálogo público."""

    category = models.OneToOneField(
        Category,
        on_delete=models.CASCADE,
        related_name='catalog_info',
        verbose_name='Categoria Base',
    )

    is_visible_public = models.BooleanField(
        default=False,
        verbose_name='Visível no Catálogo Público',
    )
    display_order = models.IntegerField(
        default=0,
        verbose_name='Ordem de Exibição',
    )
    image = models.ImageField(
        upload_to='catalog_categories/',
        blank=True,
        null=True,
        verbose_name='Imagem da Categoria',
    )
    description_public = models.TextField(
        blank=True,
        verbose_name='Descrição Pública',
    )

    objects = TenantManager()

    class Meta:
        verbose_name = 'Categoria do Catálogo'
        verbose_name_plural = 'Categorias do Catálogo'
        ordering = ['display_order', 'category__name']

    def __str__(self) -> str:
        status = 'Visível' if self.is_visible_public else 'Oculto'
        return f'{self.category.name} - {status}'


class CatalogProduct(TenantMixin):
    """Extensão de Products para catálogo público."""

    product = models.OneToOneField(
        Products,
        on_delete=models.CASCADE,
        related_name='catalog_info',
        verbose_name='Produto Base',
    )

    is_visible_public = models.BooleanField(
        default=False,
        verbose_name='Visível no Catálogo Público',
    )
    highlighted = models.BooleanField(
        default=False,
        verbose_name='Produto em Destaque',
    )
    display_order = models.IntegerField(
        default=0,
        verbose_name='Ordem de Exibição',
    )
    public_description = RichTextField(
        blank=True,
        verbose_name='Descrição Pública',
    )
    view_count = models.IntegerField(
        default=0,
        verbose_name='Visualizações',
    )

    objects = TenantManager()

    class Meta:
        verbose_name = 'Produto do Catálogo'
        verbose_name_plural = 'Produtos do Catálogo'
        ordering = ['display_order', 'product__name']

    def __str__(self) -> str:
        status = 'Visível' if self.is_visible_public else 'Oculto'
        return f'{self.product.name} - {status}'

    def increment_view_count(self) -> None:
        """Incrementa o contador de visualizações."""
        self.view_count += 1
        self.save(update_fields=['view_count'])


class ProductImage(TenantMixin):
    """Imagens adicionais para produtos."""

    product = models.ForeignKey(
        Products,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Produto',
    )

    image = models.ImageField(
        upload_to='catalog_products/',
        verbose_name='Imagem',
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name='Imagem Principal',
    )
    display_order = models.IntegerField(
        default=0,
        verbose_name='Ordem',
    )
    alt_text = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Texto Alternativo',
    )

    objects = TenantManager()

    class Meta:
        verbose_name = 'Imagem do Produto'
        verbose_name_plural = 'Imagens dos Produtos'
        ordering = ['-is_primary', 'display_order']

    def __str__(self) -> str:
        return f'{self.product.name} - Imagem {self.display_order}'

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Redimensiona e comprime a imagem antes de salvar."""
        if self.image:
            img = Image.open(self.image)

            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                alpha_channel = img.split()[-1] if img.mode == 'RGBA' else None
                background.paste(img, mask=alpha_channel)
                img = background

            if img.width > 1920:
                aspect_ratio = img.height / img.width
                new_height = int(1920 * aspect_ratio)
                img = img.resize((1920, new_height), Image.LANCZOS)

            output = BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            output.seek(0)

            self.image = InMemoryUploadedFile(
                output,
                'ImageField',
                f'{self.image.name.split(".")[0]}.jpg',
                'image/jpeg',
                output.getbuffer().nbytes,
                None,
            )

        super().save(*args, **kwargs)


class CatalogOrder(TenantMixin):
    """Pedidos recebidos via catálogo público."""

    STATUS_CHOICES = [
        ('novo', 'Novo'),
        ('em_preparo', 'Em Preparo'),
        ('enviado', 'Enviado'),
        ('entregue', 'Entregue'),
        ('cancelado', 'Cancelado'),
    ]

    order_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Número do Pedido',
    )

    customer_name = models.CharField(
        max_length=200,
        verbose_name='Nome do Cliente',
    )
    customer_phone = models.CharField(
        max_length=20,
        verbose_name='Telefone do Cliente',
    )
    customer_notes = models.TextField(
        blank=True,
        verbose_name='Observações do Cliente',
    )
    delivery_address = models.TextField(
        blank=True,
        default='',
        verbose_name='Endereço de Entrega',
    )
    payment_method = models.CharField(
        max_length=10,
        choices=Sales.FORMA_PAGAMENTO_CHOICES,
        default='PIX',
        verbose_name='Forma de Pagamento',
    )

    items = models.JSONField(
        verbose_name='Itens do Pedido',
        help_text='Lista de produtos com quantidades',
    )
    total_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Valor Total',
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='novo',
        verbose_name='Status',
    )
    whatsapp_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Enviado via WhatsApp em',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        verbose_name = 'Pedido do Catálogo'
        verbose_name_plural = 'Pedidos do Catálogo'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'Pedido #{self.order_number} - {self.customer_name}'

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Gera número do pedido antes de salvar, se necessário."""
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_order_number() -> str:
        """Gera número de pedido no formato YYYYMMDD-XXXX."""
        date_prefix = timezone.localtime().strftime('%Y%m%d')

        last_order = CatalogOrder.objects.filter(
            order_number__startswith=date_prefix,
        ).order_by('-order_number').first()

        if last_order:
            last_number = int(last_order.order_number.split('-')[1])
            new_number = last_number + 1
        else:
            new_number = 1

        return f'{date_prefix}-{new_number:04d}'


class CatalogAuditLog(TenantMixin):
    """Registra ações administrativas realizadas no catálogo público."""

    action = models.CharField(
        max_length=60,
        verbose_name='Ação',
    )
    message = models.TextField(
        verbose_name='Mensagem',
    )
    object_type = models.CharField(
        max_length=120,
        blank=True,
        verbose_name='Tipo do Objeto',
    )
    object_id = models.CharField(
        max_length=64,
        blank=True,
        verbose_name='ID do Objeto',
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Metadados',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='catalog_audit_logs',
        verbose_name='Usuário',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Criado em',
    )

    objects = TenantManager()

    class Meta:
        verbose_name = 'Auditoria do Catálogo'
        verbose_name_plural = 'Auditorias do Catálogo'
        ordering = ['-created_at']

    def __str__(self) -> str:
        user_label = self.user.username if self.user else 'Sistema'
        return f'{self.action} - {user_label} - {self.created_at:%d/%m/%Y %H:%M}'
