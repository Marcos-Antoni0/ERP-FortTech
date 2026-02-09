# INSTRUÇÕES PARA CODEX CLI - CATÁLOGO PÚBLICO

## 📋 ANTES DE COMEÇAR

### Arquivos de Referência (em /docs)
1. **14. Lista de Tarefas.md** - Sprint 7 completa com 40 tarefas
2. **Arquitetura Técnica.md** - Documentação da arquitetura atualizada
3. **Guia de Implementação.md** - Roadmap e solução proposta

### Leitura Obrigatória
Antes de iniciar qualquer tarefa, leia TODOS os arquivos acima para entender:
- Estrutura multi-tenant existente
- Padrões de código do projeto
- Modelos já criados (Company, Products, Category)
- Convenções de nomenclatura

---

## 🚀 FASE 1: INFRAESTRUTURA E MODELOS

### Tarefa T23.1: Criar App
```bash
cd /caminho/do/projeto
python manage.py startapp public_catalog
```

### Tarefa T23.2: Atualizar settings.py

Adicionar em `INSTALLED_APPS`:
```python
INSTALLED_APPS = [
    # ... apps existentes ...
    'public_catalog',
    'ckeditor',
    'ckeditor_uploader',
]
```

Adicionar configurações de mídia e CKEditor:
```python
# Mídia
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# CKEditor
CKEDITOR_UPLOAD_PATH = 'catalog_uploads/'
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Custom',
        'toolbar_Custom': [
            ['Bold', 'Italic', 'Underline'],
            ['NumberedList', 'BulletedList'],
            ['Link', 'Unlink'],
            ['RemoveFormat', 'Source']
        ]
    }
}
```

### Tarefa T24: Criar Modelos

Criar `public_catalog/models.py` com os seguintes modelos:

#### 1. CatalogSettings
- Configurações do catálogo por empresa
- Campos: catalog_enabled, catalog_slug, whatsapp_number, custom_message_template
- Herda de TenantMixin
- OneToOneField com Company

#### 2. CatalogCategory  
- Extensão de Category para catálogo público
- Campos: is_visible_public, display_order, image, description_public
- OneToOneField com Category

#### 3. CatalogProduct
- Extensão de Products para catálogo público
- Campos: is_visible_public, highlighted, display_order, public_description (RichTextField)
- OneToOneField com Products

#### 4. ProductImage
- Múltiplas imagens por produto
- Campos: product (FK), image, is_primary, display_order, alt_text
- Compressão automática de imagens no save()

#### 5. CatalogOrder
- Pedidos recebidos via catálogo
- Campos: order_number, customer_name, customer_phone, items (JSON), total_value, status
- Geração automática de order_number

**CÓDIGO COMPLETO DOS MODELOS:**

```python
from decimal import Decimal
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from ckeditor.fields import RichTextField
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys

from p_v_App.models import Company, Category, Products
from p_v_App.models_tenant import TenantMixin, TenantManager


class CatalogSettings(TenantMixin):
    """Configurações do catálogo público por empresa"""
    
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name='catalog_settings',
        verbose_name='Empresa'
    )
    
    catalog_enabled = models.BooleanField(
        default=False,
        verbose_name='Catálogo Habilitado'
    )
    catalog_slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name='URL do Catálogo',
        help_text='URL única para acesso público (ex: pizzaria-do-joao)'
    )
    catalog_title = models.CharField(
        max_length=200,
        verbose_name='Título do Catálogo'
    )
    catalog_description = models.TextField(
        blank=True,
        verbose_name='Descrição'
    )
    
    whatsapp_number = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='Número de telefone inválido. Use formato internacional.'
            )
        ],
        verbose_name='Número WhatsApp'
    )
    custom_message_template = models.TextField(
        default='Olá! Sou {customer_name} e gostaria de fazer um pedido.\n\n'
                '📋 Pedido #{order_number}\n\n'
                '🛒 Itens:\n{items}\n\n'
                '💰 Total: {total}\n\n'
                '📝 Observações:\n{notes}\n\n'
                'Aguardo confirmação!',
        verbose_name='Template da Mensagem',
        help_text='Variáveis: {customer_name}, {order_number}, {items}, {total}, {notes}'
    )
    
    display_prices = models.BooleanField(
        default=True,
        verbose_name='Exibir Preços'
    )
    primary_color = models.CharField(
        max_length=7,
        default='#002d6c',
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message='Código de cor hexadecimal inválido'
            )
        ],
        verbose_name='Cor Primária'
    )
    logo = models.ImageField(
        upload_to='catalog_logos/',
        blank=True,
        null=True,
        verbose_name='Logo'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = TenantManager()
    
    class Meta:
        verbose_name = 'Configuração do Catálogo'
        verbose_name_plural = 'Configurações do Catálogo'
    
    def __str__(self):
        return f'Catálogo: {self.catalog_title}'


class CatalogCategory(TenantMixin):
    """Extensão de Category para catálogo público"""
    
    category = models.OneToOneField(
        Category,
        on_delete=models.CASCADE,
        related_name='catalog_info',
        verbose_name='Categoria Base'
    )
    
    is_visible_public = models.BooleanField(
        default=False,
        verbose_name='Visível no Catálogo Público'
    )
    display_order = models.IntegerField(
        default=0,
        verbose_name='Ordem de Exibição'
    )
    image = models.ImageField(
        upload_to='catalog_categories/',
        blank=True,
        null=True,
        verbose_name='Imagem da Categoria'
    )
    description_public = models.TextField(
        blank=True,
        verbose_name='Descrição Pública'
    )
    
    objects = TenantManager()
    
    class Meta:
        verbose_name = 'Categoria do Catálogo'
        verbose_name_plural = 'Categorias do Catálogo'
        ordering = ['display_order', 'category__name']
    
    def __str__(self):
        return f'{self.category.name} - {"Visível" if self.is_visible_public else "Oculto"}'


class CatalogProduct(TenantMixin):
    """Extensão de Products para catálogo público"""
    
    product = models.OneToOneField(
        Products,
        on_delete=models.CASCADE,
        related_name='catalog_info',
        verbose_name='Produto Base'
    )
    
    is_visible_public = models.BooleanField(
        default=False,
        verbose_name='Visível no Catálogo Público'
    )
    highlighted = models.BooleanField(
        default=False,
        verbose_name='Produto em Destaque'
    )
    display_order = models.IntegerField(
        default=0,
        verbose_name='Ordem de Exibição'
    )
    public_description = RichTextField(
        blank=True,
        verbose_name='Descrição Pública'
    )
    view_count = models.IntegerField(
        default=0,
        verbose_name='Visualizações'
    )
    
    objects = TenantManager()
    
    class Meta:
        verbose_name = 'Produto do Catálogo'
        verbose_name_plural = 'Produtos do Catálogo'
        ordering = ['display_order', 'product__name']
    
    def __str__(self):
        return f'{self.product.name} - {"Visível" if self.is_visible_public else "Oculto"}'
    
    def increment_view_count(self):
        self.view_count += 1
        self.save(update_fields=['view_count'])


class ProductImage(TenantMixin):
    """Imagens adicionais para produtos"""
    
    product = models.ForeignKey(
        Products,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Produto'
    )
    
    image = models.ImageField(
        upload_to='catalog_products/',
        verbose_name='Imagem'
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name='Imagem Principal'
    )
    display_order = models.IntegerField(
        default=0,
        verbose_name='Ordem'
    )
    alt_text = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Texto Alternativo'
    )
    
    objects = TenantManager()
    
    class Meta:
        verbose_name = 'Imagem do Produto'
        verbose_name_plural = 'Imagens dos Produtos'
        ordering = ['-is_primary', 'display_order']
    
    def __str__(self):
        return f'{self.product.name} - Imagem {self.display_order}'
    
    def save(self, *args, **kwargs):
        if self.image:
            img = Image.open(self.image)
            
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
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
                sys.getsizeof(output),
                None
            )
        
        super().save(*args, **kwargs)


class CatalogOrder(TenantMixin):
    """Pedidos recebidos via catálogo público"""
    
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
        verbose_name='Número do Pedido'
    )
    
    customer_name = models.CharField(
        max_length=200,
        verbose_name='Nome do Cliente'
    )
    customer_phone = models.CharField(
        max_length=20,
        verbose_name='Telefone do Cliente'
    )
    customer_notes = models.TextField(
        blank=True,
        verbose_name='Observações do Cliente'
    )
    
    items = models.JSONField(
        verbose_name='Itens do Pedido',
        help_text='Lista de produtos com quantidades'
    )
    total_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Valor Total'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='novo',
        verbose_name='Status'
    )
    whatsapp_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Enviado via WhatsApp em'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = TenantManager()
    
    class Meta:
        verbose_name = 'Pedido do Catálogo'
        verbose_name_plural = 'Pedidos do Catálogo'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Pedido #{self.order_number} - {self.customer_name}'
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_order_number():
        from datetime import datetime
        date_prefix = datetime.now().strftime('%Y%m%d')
        
        last_order = CatalogOrder.objects.filter(
            order_number__startswith=date_prefix
        ).order_by('-order_number').first()
        
        if last_order:
            last_number = int(last_order.order_number.split('-')[1])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f'{date_prefix}-{new_number:04d}'
```

### Tarefa T24.6: Migrações
```bash
python manage.py makemigrations public_catalog
python manage.py migrate
```

### Validação da Fase 1
Após concluir, verificar:
- [ ] App criada e em INSTALLED_APPS
- [ ] Settings.py atualizado
- [ ] 5 modelos criados corretamente
- [ ] Migrações aplicadas sem erros
- [ ] Models aparecem no Django Admin

---

## ⏭️ PRÓXIMAS FASES

Após validar a Fase 1, solicite instruções para:
- **Fase 2:** Área Administrativa (Forms e Views Admin)
- **Fase 3:** Interface Pública (Views e Templates)
- **Fase 4:** Integração WhatsApp
- **Fase 5:** Gestão de Pedidos
- **Fase 6:** Segurança e Otimização

---

## 🎯 PADRÕES OBRIGATÓRIOS

### Código Python
- ✅ Aspas simples sempre
- ✅ PEP 8 compliance
- ✅ TenantMixin em todos os modelos
- ✅ Docstrings em classes e métodos
- ✅ Type hints em funções complexas

### Estrutura
- ✅ Class Based Views (CBV)
- ✅ Formulários Django com validações
- ✅ Templates responsivos
- ✅ JavaScript modular

---

**IMPORTANTE:** Este arquivo é uma referência. Cole as instruções diretamente no Codex CLI ao invés de pedir para ele ler este arquivo.