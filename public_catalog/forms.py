from __future__ import annotations

import re

from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet
import bleach

from p_v_App.models import Category, Products, Sales

from .models import CatalogCategory, CatalogProduct, CatalogSettings, ProductImage


class CatalogSettingsForm(forms.ModelForm):
    """Formulário para configurações do catálogo público."""

    class Meta:
        model = CatalogSettings
        fields = [
            'catalog_enabled',
            'catalog_slug',
            'catalog_title',
            'catalog_description',
            'whatsapp_number',
            'custom_message_template',
            'display_prices',
            'primary_color',
            'logo',
        ]
        widgets = {
            'catalog_enabled': forms.CheckboxInput(
                attrs={'class': 'form-check-input'},
            ),
            'catalog_slug': forms.TextInput(
                attrs={'class': 'form-control ds-input'},
            ),
            'catalog_title': forms.TextInput(
                attrs={'class': 'form-control ds-input'},
            ),
            'catalog_description': forms.Textarea(
                attrs={'class': 'form-control ds-input', 'rows': 3},
            ),
            'whatsapp_number': forms.TextInput(
                attrs={'class': 'form-control ds-input'},
            ),
            'custom_message_template': forms.Textarea(
                attrs={'class': 'form-control ds-input', 'rows': 6},
            ),
            'display_prices': forms.CheckboxInput(
                attrs={'class': 'form-check-input'},
            ),
            'primary_color': forms.TextInput(
                attrs={'class': 'form-control ds-input', 'type': 'color'},
            ),
            'logo': forms.ClearableFileInput(
                attrs={'class': 'form-control'},
            ),
        }
        labels = {
            'catalog_enabled': 'Catálogo habilitado',
            'catalog_slug': 'URL do catálogo',
            'catalog_title': 'Título do catálogo',
            'catalog_description': 'Descrição',
            'whatsapp_number': 'Número WhatsApp',
            'custom_message_template': 'Template da mensagem',
            'display_prices': 'Exibir preços',
            'primary_color': 'Cor primária',
            'logo': 'Logo',
        }

    def clean_catalog_slug(self) -> str:
        """Valida unicidade do slug globalmente."""
        slug = (self.cleaned_data.get('catalog_slug') or '').strip()
        qs = CatalogSettings.objects.filter(catalog_slug=slug)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Este slug já está em uso.')
        return slug

    def clean_whatsapp_number(self) -> str:
        """Valida número WhatsApp em formato internacional."""
        raw_number = self.cleaned_data.get('whatsapp_number') or ''
        digits = re.sub(r'\D', '', raw_number)
        if not digits:
            raise ValidationError('Informe um número de WhatsApp válido.')
        if len(digits) < 10 or len(digits) > 15:
            raise ValidationError('Número de WhatsApp inválido. Use formato internacional.')
        if not digits.startswith('55') and len(digits) <= 11:
            digits = f'55{digits}'
        return f'+{digits}'


class CatalogProductForm(forms.ModelForm):
    """Formulário de edição de produto público."""

    class Meta:
        model = CatalogProduct
        fields = [
            'is_visible_public',
            'highlighted',
            'display_order',
            'public_description',
        ]
        widgets = {
            'is_visible_public': forms.CheckboxInput(
                attrs={'class': 'form-check-input'},
            ),
            'highlighted': forms.CheckboxInput(
                attrs={'class': 'form-check-input'},
            ),
            'display_order': forms.NumberInput(
                attrs={'class': 'form-control ds-input', 'min': 0},
            ),
        }
        labels = {
            'is_visible_public': 'Visível no catálogo',
            'highlighted': 'Produto em destaque',
            'display_order': 'Ordem de exibição',
            'public_description': 'Descrição pública',
        }


class CatalogCategoryForm(forms.ModelForm):
    """Formulário de edição de categoria pública."""

    class Meta:
        model = CatalogCategory
        fields = [
            'is_visible_public',
            'display_order',
            'image',
            'description_public',
        ]
        widgets = {
            'is_visible_public': forms.CheckboxInput(
                attrs={'class': 'form-check-input'},
            ),
            'display_order': forms.NumberInput(
                attrs={'class': 'form-control ds-input', 'min': 0},
            ),
            'image': forms.ClearableFileInput(
                attrs={'class': 'form-control'},
            ),
            'description_public': forms.Textarea(
                attrs={'class': 'form-control ds-input', 'rows': 3},
            ),
        }
        labels = {
            'is_visible_public': 'Visível no catálogo',
            'display_order': 'Ordem de exibição',
            'image': 'Imagem',
            'description_public': 'Descrição pública',
        }


class ProductImageForm(forms.ModelForm):
    """Formulário para imagens adicionais do produto."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].required = False
        self.fields['display_order'].required = False

    def clean(self):
        cleaned_data = super().clean()
        image = cleaned_data.get('image')
        is_primary = cleaned_data.get('is_primary')
        display_order = cleaned_data.get('display_order')
        alt_text = (cleaned_data.get('alt_text') or '').strip()
        has_any_data = bool(image or is_primary or alt_text or display_order not in (None, ''))

        if not image and not self.instance.pk and has_any_data:
            raise ValidationError('Informe uma imagem para cadastrar.')

        if display_order in (None, '') and (image or self.instance.pk):
            cleaned_data['display_order'] = 0

        return cleaned_data

    class Meta:
        model = ProductImage
        fields = ['image', 'is_primary', 'display_order', 'alt_text']
        widgets = {
            'image': forms.ClearableFileInput(
                attrs={'class': 'form-control'},
            ),
            'is_primary': forms.CheckboxInput(
                attrs={'class': 'form-check-input'},
            ),
            'display_order': forms.NumberInput(
                attrs={'class': 'form-control ds-input', 'min': 0},
            ),
            'alt_text': forms.TextInput(
                attrs={'class': 'form-control ds-input'},
            ),
        }
        labels = {
            'image': 'Imagem',
            'is_primary': 'Imagem principal',
            'display_order': 'Ordem',
            'alt_text': 'Texto alternativo',
        }


class BaseProductImageFormSet(BaseInlineFormSet):
    """Garante que apenas uma imagem seja marcada como principal."""

    def clean(self) -> None:
        super().clean()
        primary_count = 0
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            if form.cleaned_data.get('is_primary'):
                primary_count += 1
        if primary_count > 1:
            raise ValidationError('Apenas uma imagem pode ser principal.')


def get_catalog_product_formset() -> type[BaseInlineFormSet]:
    """Cria formset para imagens de produto."""
    return forms.inlineformset_factory(
        parent_model=Products,
        model=ProductImage,
        form=ProductImageForm,
        formset=BaseProductImageFormSet,
        extra=1,
        can_delete=True,
    )


class CheckoutForm(forms.Form):
    """Formulário de checkout do catálogo público."""

    customer_name = forms.CharField(
        label='Nome',
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    customer_phone = forms.CharField(
        label='Telefone',
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    customer_notes = forms.CharField(
        label='Observações',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    )
    delivery_address = forms.CharField(
        label='Endereço',
        required=True,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    )
    payment_method = forms.ChoiceField(
        label='Forma de pagamento',
        choices=Sales.FORMA_PAGAMENTO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    def clean_customer_notes(self) -> str:
        """Sanitiza observações do cliente."""
        notes = self.cleaned_data.get('customer_notes') or ''
        return bleach.clean(notes, tags=[], strip=True)

    def clean_customer_phone(self) -> str:
        """Normaliza telefone para formato internacional simples."""
        raw_number = self.cleaned_data.get('customer_phone') or ''
        digits = re.sub(r'\D', '', raw_number)
        if len(digits) < 10 or len(digits) > 15:
            raise ValidationError('Telefone inválido.')
        if not digits.startswith('55') and len(digits) <= 11:
            digits = f'55{digits}'
        return f'+{digits}'

    def clean_delivery_address(self) -> str:
        """Sanitiza endereço informado pelo cliente."""
        address = self.cleaned_data.get('delivery_address') or ''
        return bleach.clean(address, tags=[], strip=True)
