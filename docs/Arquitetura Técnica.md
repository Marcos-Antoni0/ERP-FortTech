# Arquitetura Técnica - ERP FortTech (ATUALIZADA)

## 1. Stack Tecnológica

O projeto **ERP FortTech** é construído sobre uma arquitetura *full-stack* robusta, utilizando o *framework* Django para o *backend* e *frontend* (via *Template Language*), com estilização moderna provida pelo Tailwind CSS.

| Componente | Tecnologia | Detalhes |
| :--- | :--- | :--- |
| **Backend** | Python 3.13+ | Linguagem de programação principal |
| **Framework** | Django 5.x | Framework *full-stack* (incluindo *Template Language*) |
| **Frontend** | Django Template Language (DTL) | Renderização do *frontend* |
| **Estilização** | Tailwind CSS 3.x | Framework CSS utilitário para design moderno e responsivo |
| **Banco de Dados** | PostgreSQL 15+ | Banco de dados relacional, configurado via `dj_database_url` (ambiente Railway) |
| **Multi-tenancy** | Custom Middleware | Implementação via `TenantMiddleware` e `TenantMixin` para isolamento de dados por empresa |
| **Processamento de Imagens** | Pillow 10.x | Redimensionamento, compressão e manipulação de imagens |
| **Editor Rich Text** | CKEditor 6.x | Editor WYSIWYG para descrições de produtos |
| **Rate Limiting** | Django Ratelimit 4.x | Proteção contra abuso de endpoints públicos |

---

## 2. Modelo de Multi-Tenancy

O sistema suporta múltiplas empresas (tenants) em uma única instância de aplicação e banco de dados.

### 2.1. Componentes Chave

*   **`Company` (Modelo):** Representa a empresa (tenant) no sistema
*   **`UserProfile` (Modelo):** Estende o `User` padrão do Django, associando-o a uma `Company`
*   **`TenantMixin` (Mixin):** Classe abstrata que adiciona o campo `company` a todos os modelos de negócio que precisam ser isolados por tenant
*   **`TenantManager` (Manager):** Manager personalizado que filtra automaticamente os *querysets* pela `company` atual
*   **`TenantMiddleware` (Middleware):** Identifica a empresa do usuário logado e a define no contexto da requisição

### 2.2. Isolamento de Dados

O isolamento é garantido pela filtragem em nível de *queryset* e pela obrigatoriedade de associar um objeto a uma `company` antes de salvar.

**Nota Crítica para Catálogo Público:**
- Views públicas do catálogo identificam a empresa pelo **slug na URL** ao invés do usuário logado
- Implementação: `company = get_object_or_404(Company, catalog_settings__catalog_slug=slug)`
- Não há autenticação necessária para acessar o catálogo
- Isolamento garantido através do slug único por empresa

---

## 3. Estrutura de Apps do Django

### 3.1. Apps Principais (Existentes)

| App | Responsabilidade |
| :--- | :--- |
| `p_v_App` | Configurações centrais, modelos de *multi-tenancy* e *middlewares* |
| `accounts` | Gerenciamento de autenticação e perfis de usuário |
| `core` | Funcionalidades centrais e *views* genéricas (Home, Configurações) |
| `catalog` | Gerenciamento de produtos e categorias (admin) |
| `sales` | Processamento de vendas e transações |
| `orders` | Gerenciamento de pedidos internos (mesa ou delivery) |
| `inventory` | Gerenciamento de estoque e movimentações |
| `tables` | Gerenciamento de mesas (para restaurantes) |
| `staff` | Gerenciamento de funcionários e permissões |
| `clients` | Cadastro e histórico de clientes |
| `debts` | Gestão de débitos e contas a receber |

### 3.2. Nova App: `public_catalog`

#### Responsabilidade
Gerenciar catálogo de produtos público e acessível sem autenticação, com integração WhatsApp para recebimento de pedidos.

#### Estrutura de Arquivos
```
public_catalog/
├── __init__.py
├── admin.py                    # Configuração Django Admin
├── apps.py                     # Configuração da app
├── models.py                   # Modelos de dados
├── views.py                    # Views públicas e administrativas
├── forms.py                    # Formulários de configuração e checkout
├── urls.py                     # Rotas da aplicação
├── utils.py                    # Funções auxiliares (WhatsApp, formatação)
├── middleware.py               # Middleware específico (rate limiting)
├── migrations/                 # Migrações do banco de dados
├── templates/
│   └── public_catalog/
│       ├── admin/              # Templates administrativos
│       │   ├── settings.html
│       │   ├── product_list.html
│       │   ├── product_edit.html
│       │   ├── category_list.html
│       │   ├── order_list.html
│       │   └── order_detail.html
│       └── public/             # Templates públicos
│           ├── base_public.html
│           ├── home.html
│           ├── category.html
│           ├── product_detail.html
│           ├── cart.html
│           ├── checkout.html
│           └── confirmation.html
├── static/
│   └── public_catalog/
│       ├── css/
│       │   ├── public.css
│       │   └── admin.css
│       ├── js/
│       │   ├── cart.js
│       │   ├── checkout.js
│       │   └── image_upload.js
│       └── img/
└── tests/
    ├── test_models.py
    ├── test_views.py
    ├── test_forms.py
    └── test_integration.py
```

---

## 4. Modelos de Dados - `public_catalog`

### 4.1. `CatalogSettings`
**Propósito:** Configurações do catálogo público por empresa

| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| `company` | ForeignKey(Company) | Empresa proprietária (unique) |
| `catalog_enabled` | BooleanField | Ativa/desativa catálogo público |
| `catalog_slug` | SlugField | URL única do catálogo (ex: "pizzaria-do-joao") |
| `whatsapp_number` | CharField(20) | Número WhatsApp (formato: +5585988888888) |
| `custom_message_template` | TextField | Template da mensagem (com variáveis) |
| `display_prices` | BooleanField | Exibir ou ocultar preços |
| `primary_color` | CharField(7) | Cor primária (hex: #002d6c) |
| `logo` | ImageField | Logo da empresa |
| `catalog_title` | CharField(200) | Título do catálogo |
| `catalog_description` | TextField | Descrição/subtítulo |
| `created_at` | DateTimeField | Data de criação |
| `updated_at` | DateTimeField | Última atualização |

**Validações:**
- `catalog_slug` deve ser único globalmente
- `whatsapp_number` deve seguir formato internacional
- `primary_color` deve ser código hexadecimal válido

### 4.2. `CatalogCategory`
**Propósito:** Categorias visíveis no catálogo público (estende Category)

| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| `category` | OneToOneField(Category) | Categoria base |
| `is_visible_public` | BooleanField | Visível no catálogo público |
| `display_order` | IntegerField | Ordem de exibição |
| `image` | ImageField | Imagem da categoria |
| `description_public` | TextField | Descrição pública (pode ser diferente da interna) |

### 4.3. `CatalogProduct`
**Propósito:** Produtos visíveis no catálogo público (estende Products)

| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| `product` | OneToOneField(Products) | Produto base |
| `is_visible_public` | BooleanField | Visível no catálogo público |
| `highlighted` | BooleanField | Produto em destaque (homepage) |
| `display_order` | IntegerField | Ordem de exibição |
| `public_description` | TextField (CKEditor) | Descrição rica para clientes |
| `view_count` | IntegerField | Contador de visualizações |

### 4.4. `ProductImage`
**Propósito:** Múltiplas imagens por produto

| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| `product` | ForeignKey(Products) | Produto relacionado |
| `image` | ImageField | Arquivo de imagem |
| `is_primary` | BooleanField | Imagem principal |
| `display_order` | IntegerField | Ordem na galeria |
| `alt_text` | CharField(200) | Texto alternativo (SEO) |

**Validações:**
- Apenas uma imagem `is_primary=True` por produto
- Compressão automática para max 1920px de largura
- Formatos aceitos: JPG, PNG, WebP

### 4.5. `CatalogOrder`
**Propósito:** Rastreamento de pedidos recebidos via catálogo

| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| `company` | ForeignKey(Company) | Empresa destinatária |
| `order_number` | CharField(20) | Número único (formato: YYYYMMDD-XXXX) |
| `customer_name` | CharField(200) | Nome do cliente |
| `customer_phone` | CharField(20) | Telefone do cliente |
| `customer_notes` | TextField | Observações do cliente |
| `items` | JSONField | Lista de produtos e quantidades |
| `total_value` | DecimalField | Valor total do pedido |
| `status` | CharField(20) | Status (novo, em_preparo, enviado, entregue, cancelado) |
| `whatsapp_sent_at` | DateTimeField | Data/hora do envio WhatsApp |
| `created_at` | DateTimeField | Data/hora de criação |
| `updated_at` | DateTimeField | Última atualização |

**Formato do campo `items` (JSON):**
```json
[
  {
    "product_id": 123,
    "product_name": "Pizza Margherita",
    "quantity": 2,
    "unit_price": 35.00,
    "subtotal": 70.00
  },
  {
    "product_id": 124,
    "product_name": "Refrigerante 2L",
    "quantity": 1,
    "unit_price": 8.00,
    "subtotal": 8.00
  }
]
```

---

## 5. Fluxo de Dados e Arquitetura de Segurança

### 5.1. Fluxo do Cliente (Público)

```
1. Cliente acessa: /catalogo/{slug}/
   ↓
2. Sistema busca Company por catalog_slug
   ↓
3. Carrega configurações (CatalogSettings)
   ↓
4. Exibe categorias e produtos visíveis (is_visible_public=True)
   ↓
5. Cliente adiciona produtos ao carrinho (Django Session)
   ↓
6. Cliente finaliza pedido (checkout)
   ↓
7. Sistema salva CatalogOrder
   ↓
8. Sistema gera mensagem WhatsApp formatada
   ↓
9. Redireciona para: https://wa.me/{number}?text={mensagem}
   ↓
10. Cliente envia mensagem via WhatsApp
```

### 5.2. Fluxo do Administrador (Autenticado)

```
1. Admin acessa painel administrativo
   ↓
2. Middleware autentica e identifica company
   ↓
3. Admin configura CatalogSettings
   ↓
4. Admin gerencia visibilidade de produtos/categorias
   ↓
5. Admin recebe pedidos via WhatsApp
   ↓
6. Admin visualiza pedidos no painel
   ↓
7. Admin pode converter pedido em venda interna
```

### 5.3. Camadas de Segurança

#### Nível 1: Rate Limiting
```python
# views.py
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='100/h', method='ALL')
def public_catalog_home(request, slug):
    # View implementation
```

#### Nível 2: CSRF Protection
- Todos os formulários incluem `{% csrf_token %}`
- Validação automática pelo Django

#### Nível 3: Input Sanitization
```python
# forms.py
import bleach

class CheckoutForm(forms.Form):
    customer_notes = forms.CharField(widget=forms.Textarea)
    
    def clean_customer_notes(self):
        notes = self.cleaned_data['customer_notes']
        return bleach.clean(notes, tags=[], strip=True)
```

#### Nível 4: CAPTCHA (Google reCAPTCHA)
```html
<!-- checkout.html -->
<div class="g-recaptcha" data-sitekey="{{ recaptcha_site_key }}"></div>
```

#### Nível 5: Auditoria
```python
# models.py
class CatalogSettingsHistory(models.Model):
    settings = models.ForeignKey(CatalogSettings)
    changed_by = models.ForeignKey(User)
    change_type = models.CharField(max_length=50)
    old_value = models.JSONField()
    new_value = models.JSONField()
    timestamp = models.DateTimeField(auto_now_add=True)
```

---

## 6. Otimização de Performance

### 6.1. Database Query Optimization

```python
# views.py - Exemplo de query otimizada
def public_catalog_home(request, slug):
    company = Company.objects.select_related('catalog_settings').get(
        catalog_settings__catalog_slug=slug
    )
    
    categories = CatalogCategory.objects.filter(
        category__company=company,
        is_visible_public=True
    ).select_related('category').order_by('display_order')
    
    featured_products = CatalogProduct.objects.filter(
        product__company=company,
        is_visible_public=True,
        highlighted=True
    ).select_related('product').prefetch_related('product__productimage_set')[:6]
```

### 6.2. Caching Strategy

```python
# views.py
from django.core.cache import cache

def get_catalog_products(company_id, category_id=None):
    cache_key = f'catalog_products_{company_id}_{category_id}'
    products = cache.get(cache_key)
    
    if not products:
        query = CatalogProduct.objects.filter(
            product__company_id=company_id,
            is_visible_public=True
        )
        if category_id:
            query = query.filter(product__category_id=category_id)
        
        products = query.select_related('product').prefetch_related(
            'product__productimage_set'
        ).order_by('display_order')
        
        cache.set(cache_key, products, 60 * 15)  # 15 minutos
    
    return products
```

### 6.3. Image Optimization

```python
# models.py
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile

class ProductImage(models.Model):
    # ... fields ...
    
    def save(self, *args, **kwargs):
        if self.image:
            img = Image.open(self.image)
            
            # Redimensionar se maior que 1920px
            if img.width > 1920:
                aspect_ratio = img.height / img.width
                new_height = int(1920 * aspect_ratio)
                img = img.resize((1920, new_height), Image.LANCZOS)
            
            # Comprimir
            output = BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            output.seek(0)
            
            self.image = InMemoryUploadedFile(
                output, 'ImageField', 
                f"{self.image.name.split('.')[0]}.jpg",
                'image/jpeg', len(output.getvalue()), None
            )
        
        super().save(*args, **kwargs)
```

---

## 7. Integração WhatsApp

### 7.1. Geração de Mensagem

```python
# utils.py
def generate_whatsapp_message(order):
    settings = order.company.catalog_settings
    template = settings.custom_message_template
    
    # Formatar lista de itens
    items_list = "\n".join([
        f"• {item['quantity']}x {item['product_name']} - R$ {item['subtotal']:.2f}"
        for item in order.items
    ])
    
    # Substituir variáveis
    message = template.format(
        customer_name=order.customer_name,
        order_number=order.order_number,
        items=items_list,
        total=f"R$ {order.total_value:.2f}",
        notes=order.customer_notes or "Nenhuma observação"
    )
    
    return message

def format_whatsapp_number(number):
    # Remove formatação
    cleaned = ''.join(filter(str.isdigit, number))
    
    # Adiciona código do país se não tiver
    if not cleaned.startswith('55'):
        cleaned = '55' + cleaned
    
    return cleaned

def get_whatsapp_url(order):
    number = format_whatsapp_number(order.company.catalog_settings.whatsapp_number)
    message = generate_whatsapp_message(order)
    
    from urllib.parse import quote
    encoded_message = quote(message)
    
    return f"https://wa.me/{number}?text={encoded_message}"
```

### 7.2. Template de Mensagem Padrão

```
Olá! Sou {customer_name} e gostaria de fazer um pedido.

📋 Pedido #{order_number}

🛒 Itens:
{items}

💰 Total: {total}

📝 Observações:
{notes}

Aguardo confirmação!
```

---

## 8. URLs e Rotas

### 8.1. URLs Públicas (Sem Autenticação)

```python
# public_catalog/urls.py
urlpatterns = [
    # Catálogo público
    path('<slug:slug>/', views.PublicCatalogHomeView.as_view(), name='home'),
    path('<slug:slug>/categoria/<int:category_id>/', views.PublicCatalogCategoryView.as_view(), name='category'),
    path('<slug:slug>/produto/<int:product_id>/', views.PublicCatalogProductDetailView.as_view(), name='product_detail'),
    
    # Carrinho
    path('<slug:slug>/carrinho/', views.PublicCatalogCartView.as_view(), name='cart'),
    path('<slug:slug>/carrinho/adicionar/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('<slug:slug>/carrinho/atualizar/<int:product_id>/', views.update_cart_item, name='update_cart'),
    path('<slug:slug>/carrinho/remover/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    
    # Checkout e WhatsApp
    path('<slug:slug>/checkout/', views.CatalogCheckoutView.as_view(), name='checkout'),
    path('<slug:slug>/enviar-whatsapp/<str:order_number>/', views.SendToWhatsAppView.as_view(), name='send_whatsapp'),
    path('<slug:slug>/confirmacao/<str:order_number>/', views.OrderConfirmationView.as_view(), name='confirmation'),
]
```

### 8.2. URLs Administrativas (Com Autenticação)

```python
# public_catalog/urls.py
admin_urlpatterns = [
    # Configurações
    path('admin/configuracoes/', views.CatalogSettingsView.as_view(), name='admin_settings'),
    
    # Gestão de Produtos
    path('admin/produtos/', views.CatalogProductListView.as_view(), name='admin_products'),
    path('admin/produtos/<int:pk>/editar/', views.CatalogProductUpdateView.as_view(), name='admin_product_edit'),
    
    # Gestão de Categorias
    path('admin/categorias/', views.CatalogCategoryListView.as_view(), name='admin_categories'),
    path('admin/categorias/<int:pk>/editar/', views.CatalogCategoryUpdateView.as_view(), name='admin_category_edit'),
    
    # Pedidos
    path('admin/pedidos/', views.CatalogOrderListView.as_view(), name='admin_orders'),
    path('admin/pedidos/<str:order_number>/', views.CatalogOrderDetailView.as_view(), name='admin_order_detail'),
    
    # Analytics
    path('admin/relatorios/', views.CatalogAnalyticsView.as_view(), name='admin_analytics'),
]

urlpatterns += admin_urlpatterns
```

---

## 9. Considerações de Deploy

### 9.1. Variáveis de Ambiente

```bash
# .env
CATALOG_RECAPTCHA_SITE_KEY=your_recaptcha_site_key
CATALOG_RECAPTCHA_SECRET_KEY=your_recaptcha_secret_key
CATALOG_MAX_IMAGE_SIZE_MB=5
CATALOG_ALLOWED_IMAGE_FORMATS=jpg,jpeg,png,webp
```

### 9.2. Configurações de Produção

```python
# settings.py
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# WhiteNoise para servir arquivos estáticos
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
    }
}

# CKEditor
CKEDITOR_UPLOAD_PATH = "catalog_uploads/"
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

---

## 10. Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENTE (Navegador)                       │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Catálogo    │  │   Carrinho   │  │   Checkout   │      │
│  │   Público    │  │   (Session)  │  │              │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    DJANGO APPLICATION                        │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              public_catalog (App)                      │ │
│  │                                                        │ │
│  │  ├─ Views (Public & Admin)                           │ │
│  │  ├─ Models (CatalogSettings, CatalogProduct, etc.)   │ │
│  │  ├─ Forms (Checkout, Settings)                       │ │
│  │  └─ Utils (WhatsApp integration)                     │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Catalog  │  │ Products │  │  Sales   │  │  Orders   │  │
│  │  (Core)  │  │  (Core)  │  │  (Core)  │  │  (Core)   │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬─────┘  │
│       │             │              │              │         │
│       └─────────────┴──────────────┴──────────────┘         │
│                           │                                 │
│  ┌────────────────────────▼───────────────────────────┐    │
│  │          TenantMiddleware & TenantMixin            │    │
│  └────────────────────────┬───────────────────────────┘    │
└───────────────────────────┼─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   PostgreSQL Database                        │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Company  │  │ Products │  │ Catalog  │  │  Catalog  │  │
│  │  (Core)  │  │  (Core)  │  │ Settings │  │  Orders   │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  Redis Cache  │
                    │  (Products)   │
                    └───────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │   WhatsApp    │
                    │  Integration  │
                    └───────────────┘
```

---

## 11. Dependências e Tecnologias

| Tecnologia | Versão | Propósito |
| :--- | :--- | :--- |
| Python | 3.13+ | Linguagem base |
| Django | 5.0+ | Framework web |
| PostgreSQL | 15+ | Banco de dados |
| Pillow | 10.0+ | Processamento de imagens |
| django-ckeditor | 6.7+ | Editor rich text |
| django-ratelimit | 4.1+ | Rate limiting |
| bleach | 6.1+ | Sanitização HTML |
| Redis | 7.0+ | Cache |
| Tailwind CSS | 3.4+ | Framework CSS |

---

**Versão:** 2.0  
**Data:** 08/02/2026  
**Última Atualização:** Adição do módulo `public_catalog`  
**Autor:** Equipe de Desenvolvimento