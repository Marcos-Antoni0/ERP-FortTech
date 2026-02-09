# GUIA RÁPIDO DE IMPLEMENTAÇÃO - CATÁLOGO PÚBLICO

## 📋 CHECKLIST GERAL

### Pré-requisitos
- [ ] Python 3.13+ instalado
- [ ] PostgreSQL configurado
- [ ] Ambiente virtual ativo
- [ ] Dependências atualizadas (requirements.txt)

---

## 🎯 ORDEM DE EXECUÇÃO

### 1️⃣ INSTALAÇÃO DE DEPENDÊNCIAS
```bash
pip install Pillow>=10.0.0 --break-system-packages
pip install django-ckeditor>=6.7.0 --break-system-packages
pip install django-ratelimit>=4.1.0 --break-system-packages
pip install bleach>=6.1.0 --break-system-packages
```

### 2️⃣ CRIAÇÃO DA APP
```bash
cd /caminho/do/projeto
python manage.py startapp public_catalog
```

### 3️⃣ CONFIGURAÇÃO DO SETTINGS.PY
Adicionar em `INSTALLED_APPS`:
```python
'public_catalog',
'ckeditor',
'ckeditor_uploader',
```

Adicionar configurações:
```python
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

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

### 4️⃣ CRIAÇÃO DOS MODELOS
Copiar os modelos do PROMPT_CODEX_CLI_MASTER.md para `public_catalog/models.py`

### 5️⃣ MIGRAÇÕES
```bash
python manage.py makemigrations public_catalog
python manage.py migrate
```

### 6️⃣ CRIAÇÃO DOS FORMS
Copiar forms do PROMPT para `public_catalog/forms.py`

### 7️⃣ CRIAÇÃO DAS VIEWS
Seguir estrutura do PROMPT para criar views em `public_catalog/views.py`

### 8️⃣ CONFIGURAÇÃO DE URLS
Criar `public_catalog/urls.py` e incluir em `p_v/urls.py`

### 9️⃣ CRIAÇÃO DE TEMPLATES
Criar estrutura:
```
public_catalog/templates/public_catalog/
├── admin/
│   ├── settings.html
│   ├── product_list.html
│   ├── product_edit.html
│   └── order_list.html
└── public/
    ├── base_public.html
    ├── home.html
    ├── category.html
    ├── product_detail.html
    ├── cart.html
    └── checkout.html
```

### 🔟 TESTES
```bash
python manage.py test public_catalog
```

---

## 📝 COMANDOS ÚTEIS

### Rodar servidor de desenvolvimento
```bash
python manage.py runserver
```

### Criar superuser
```bash
python manage.py createsuperuser
```

### Verificar migrações pendentes
```bash
python manage.py showmigrations
```

### Coletar arquivos estáticos
```bash
python manage.py collectstatic
```

---

## 🔍 VALIDAÇÕES IMPORTANTES

### Após cada fase, verificar:
- [ ] Código sem erros de sintaxe
- [ ] Migrations aplicadas com sucesso
- [ ] Models aparecem no admin
- [ ] Views retornam 200 OK
- [ ] Templates renderizam corretamente
- [ ] JavaScript funciona sem erros no console
- [ ] Responsividade em mobile

---

## 🚨 TROUBLESHOOTING

### Erro: "No module named 'public_catalog'"
**Solução:** Verificar se a app foi adicionada em INSTALLED_APPS

### Erro: "Table doesn't exist"
**Solução:** Rodar `python manage.py migrate`

### Erro: "Invalid block tag: 'csrf_token'"
**Solução:** Adicionar `{% load static %}` no topo do template

### Erro: "CSRF token missing"
**Solução:** Incluir `{% csrf_token %}` em todos os forms

### Erro: "Company matching query does not exist"
**Solução:** Verificar se company tem CatalogSettings criado

---

## 📊 MÉTRICAS DE SUCESSO

### Performance
- Carregamento inicial < 3s
- Imagens otimizadas (< 200KB cada)
- Cache funcionando (15min)

### Funcionalidade
- Catálogo público acessível
- Carrinho funcionando
- WhatsApp redirecionando
- Admin completo

### Segurança
- Rate limiting ativo
- CSRF tokens presentes
- Inputs sanitizados
- CAPTCHA implementado

---

## 🔗 URLS IMPORTANTES

### Públicas
- `/catalogo/{slug}/` - Homepage do catálogo
- `/catalogo/{slug}/categoria/{id}/` - Produtos por categoria
- `/catalogo/{slug}/produto/{id}/` - Detalhe do produto
- `/catalogo/{slug}/carrinho/` - Carrinho
- `/catalogo/{slug}/checkout/` - Finalização

### Administrativas
- `/catalogo/admin/configuracoes/` - Configurações
- `/catalogo/admin/produtos/` - Gestão de produtos
- `/catalogo/admin/pedidos/` - Pedidos recebidos

---

## 📦 ESTRUTURA FINAL DE ARQUIVOS

```
public_catalog/
├── __init__.py
├── admin.py
├── apps.py
├── models.py          ✅ 5 modelos criados
├── views.py           ✅ 15+ views
├── forms.py           ✅ 5 formulários
├── urls.py            ✅ Rotas configuradas
├── utils.py           ✅ Helpers WhatsApp
├── middleware.py      ✅ Rate limiting
├── migrations/        ✅ Migrações aplicadas
├── templates/
│   └── public_catalog/
│       ├── admin/     ✅ 5 templates
│       └── public/    ✅ 7 templates
├── static/
│   └── public_catalog/
│       ├── css/       ✅ Estilos customizados
│       ├── js/        ✅ Scripts do carrinho
│       └── img/
└── tests/             ✅ Testes unitários
```

---

## 🎨 DESIGN SYSTEM

### Cores Padrão
- **Primária:** `#002d6c` (Azul escuro)
- **Secundária:** `#007da0` (Azul médio)
- **Background:** `#ffffff` (Branco)
- **Texto:** `#333333` (Cinza escuro)
- **Sucesso:** `#10b981` (Verde)
- **Erro:** `#ef4444` (Vermelho)

### Tipografia
- **Fonte:** Inter, system-ui, sans-serif
- **Títulos:** font-bold, text-2xl
- **Corpo:** text-base
- **Small:** text-sm

### Espaçamentos
- **Pequeno:** 0.5rem (8px)
- **Médio:** 1rem (16px)
- **Grande:** 2rem (32px)

---

## 🧪 TESTES MANUAIS

### Fluxo Completo do Cliente
1. Acessar `/catalogo/{slug}/`
2. Navegar pelas categorias
3. Visualizar detalhes de produto
4. Adicionar ao carrinho
5. Atualizar quantidades
6. Preencher checkout
7. Verificar redirecionamento WhatsApp

### Fluxo do Administrador
1. Login no sistema
2. Acessar configurações do catálogo
3. Definir slug e WhatsApp
4. Tornar produtos visíveis
5. Upload de imagens
6. Visualizar pedidos recebidos

---

**Versão:** 1.0  
**Atualizado:** 08/02/2026