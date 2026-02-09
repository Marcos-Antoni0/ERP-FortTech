from __future__ import annotations

from decimal import Decimal
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db import transaction
from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncDate
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse
from django.views.generic import FormView, ListView, TemplateView, UpdateView
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.core.paginator import Paginator

from core.utils import generate_sale_code, get_user_company
from p_v_App.models import Category, Products
from p_v_App.models import Estoque, Pedido, PedidoItem, Sales, salesItems

from .forms import (
    CatalogCategoryForm,
    CatalogProductForm,
    CatalogSettingsForm,
    CheckoutForm,
    get_catalog_product_formset,
)
from .models import (
    CatalogAuditLog,
    CatalogCategory,
    CatalogOrder,
    CatalogProduct,
    CatalogSettings,
    ProductImage,
)
from .utils import generate_whatsapp_message, get_whatsapp_url


class CompanyContextMixin(LoginRequiredMixin):
    """Mixin para recuperar e validar a empresa do usuário."""

    def get_company(self):
        """Obtém a empresa do usuário autenticado."""
        return get_user_company(self.request)

    def dispatch(self, request, *args, **kwargs):
        """Garante que o usuário tenha empresa associada."""
        if not self.get_company():
            messages.error(
                request,
                'Não foi possível identificar sua empresa. Verifique seu perfil.',
            )
            return redirect('home-page')
        return super().dispatch(request, *args, **kwargs)


def log_admin_action(
    request,
    action: str,
    message: str,
    target=None,
    metadata: dict | None = None,
) -> None:
    """Registra uma ação administrativa relacionada ao catálogo público."""
    company = get_user_company(request)
    if not company:
        return
    object_type = ''
    object_id = ''
    if target is not None:
        object_type = target._meta.label
        object_id = str(target.pk)
    CatalogAuditLog.objects.create(
        company=company,
        user=request.user if request.user.is_authenticated else None,
        action=action,
        message=message,
        object_type=object_type,
        object_id=object_id,
        metadata=metadata or {},
    )


class CatalogSettingsView(CompanyContextMixin, TemplateView):
    """Tela de configurações do catálogo público."""

    template_name = 'public_catalog/admin/settings.html'
    form_class = CatalogSettingsForm

    def get_object(self) -> CatalogSettings | None:
        """Obtém o registro de configurações do catálogo."""
        company = self.get_company()
        return CatalogSettings.objects.filter(company=company).first()

    def get_form(self):
        """Instancia o formulário com dados existentes."""
        instance = self.get_object()
        if not instance:
            instance = CatalogSettings(
                company=self.get_company(),
                catalog_title=self.get_company().name,
                catalog_slug=slugify(self.get_company().name)[:100],
            )
        return self.form_class(instance=instance)

    def get_context_data(self, **kwargs):
        """Monta o contexto da página."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'page_title': 'Configurações do Catálogo',
                'form': kwargs.get('form') or self.get_form(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        """Salva configurações do catálogo."""
        company = self.get_company()
        instance = self.get_object() or CatalogSettings(company=company)
        form = self.form_class(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            settings = form.save(commit=False)
            settings.company = company
            settings.save()
            clear_public_catalog_cache(company)
            log_admin_action(
                request,
                action='settings_updated',
                message='Configurações do catálogo atualizadas.',
                target=settings,
            )
            messages.success(request, 'Configurações salvas com sucesso.')
            return redirect('public-catalog-admin-settings')
        return self.render_to_response(self.get_context_data(form=form))


class CatalogProductListView(CompanyContextMixin, ListView):
    """Lista de produtos para visibilidade pública."""

    template_name = 'public_catalog/admin/product_list.html'
    context_object_name = 'catalog_products'

    def ensure_catalog_products(self, company):
        """Garante registros de catálogo para todos os produtos."""
        products = Products.objects.filter(company=company)
        existing_ids = CatalogProduct.objects.filter(
            company=company,
        ).values_list('product_id', flat=True)
        missing_products = products.exclude(id__in=existing_ids)
        CatalogProduct.objects.bulk_create(
            [
                CatalogProduct(company=company, product=product)
                for product in missing_products
            ],
            ignore_conflicts=True,
        )

    def get_queryset(self):
        """Filtra produtos conforme parâmetros da listagem."""
        company = self.get_company()
        self.ensure_catalog_products(company)
        queryset = (
            CatalogProduct.objects.select_related('product', 'product__category_id')
            .filter(company=company)
            .order_by('display_order', 'product__name')
        )
        category_id = self.request.GET.get('category')
        visibility = self.request.GET.get('visibility')
        highlighted = self.request.GET.get('highlighted')

        if category_id:
            queryset = queryset.filter(product__category_id=category_id)
        if visibility == 'visible':
            queryset = queryset.filter(is_visible_public=True)
        elif visibility == 'hidden':
            queryset = queryset.filter(is_visible_public=False)
        if highlighted == '1':
            queryset = queryset.filter(highlighted=True)
        elif highlighted == '0':
            queryset = queryset.filter(highlighted=False)
        return queryset

    def get_context_data(self, **kwargs):
        """Inclui filtros e dados auxiliares."""
        context = super().get_context_data(**kwargs)
        company = self.get_company()
        categories = Category.objects.filter(company=company).order_by('name')
        context.update(
            {
                'page_title': 'Produtos do Catálogo',
                'categories': categories,
                'selected_category': self.request.GET.get('category', ''),
                'selected_visibility': self.request.GET.get('visibility', ''),
                'selected_highlighted': self.request.GET.get('highlighted', ''),
            }
        )
        return context


class CatalogProductUpdateView(CompanyContextMixin, UpdateView):
    """Edição de dados públicos do produto."""

    template_name = 'public_catalog/admin/product_edit.html'
    form_class = CatalogProductForm
    model = CatalogProduct

    def get_queryset(self):
        """Restringe o queryset à empresa atual."""
        company = self.get_company()
        return CatalogProduct.objects.select_related('product').filter(company=company)

    def get_formset(self):
        """Cria o formset para imagens."""
        formset_class = get_catalog_product_formset()
        return formset_class(
            instance=self.object.product,
            data=self.request.POST or None,
            files=self.request.FILES or None,
        )

    def get_context_data(self, **kwargs):
        """Inclui formset e produto base."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'page_title': 'Editar Produto do Catálogo',
                'product': self.object.product,
                'formset': kwargs.get('formset') or self.get_formset(),
            }
        )
        return context

    def form_valid(self, form):
        """Salva formulário e formset de imagens."""
        formset = self.get_formset()
        if not formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form, formset=formset))
        with transaction.atomic():
            catalog_product = form.save(commit=False)
            catalog_product.company = self.get_company()
            catalog_product.save()
            instances = formset.save(commit=False)
            for obj in formset.deleted_objects:
                obj.delete()
            for instance in instances:
                if not instance.pk and not instance.image:
                    continue
                instance.company = catalog_product.company
                if instance.display_order is None:
                    instance.display_order = 0
                instance.save()
            formset.save_m2m()
        clear_public_catalog_cache(self.get_company())
        log_admin_action(
            self.request,
            action='product_updated',
            message='Produto do catálogo atualizado.',
            target=catalog_product,
        )
        messages.success(self.request, 'Produto atualizado com sucesso.')
        return redirect('public-catalog-admin-products')


class CatalogProductBulkActionView(CompanyContextMixin, TemplateView):
    """Aplica ações em massa para produtos do catálogo."""

    def post(self, request, *args, **kwargs):
        company = self.get_company()
        action = request.POST.get('action')
        product_ids = request.POST.getlist('product_ids')
        if not product_ids:
            messages.warning(request, 'Selecione ao menos um produto.')
            return redirect('public-catalog-admin-products')

        queryset = CatalogProduct.objects.filter(company=company, id__in=product_ids)
        if action == 'visible':
            queryset.update(is_visible_public=True)
            clear_public_catalog_cache(company)
            log_admin_action(
                request,
                action='product_bulk_visibility',
                message='Produtos marcados como visíveis no catálogo.',
                metadata={'count': queryset.count(), 'value': 'visible'},
            )
            messages.success(request, 'Produtos marcados como visíveis.')
        elif action == 'hidden':
            queryset.update(is_visible_public=False)
            clear_public_catalog_cache(company)
            log_admin_action(
                request,
                action='product_bulk_visibility',
                message='Produtos marcados como ocultos no catálogo.',
                metadata={'count': queryset.count(), 'value': 'hidden'},
            )
            messages.success(request, 'Produtos marcados como ocultos.')
        else:
            messages.error(request, 'Ação inválida.')
        return redirect('public-catalog-admin-products')


class CatalogProductReorderView(CompanyContextMixin, TemplateView):
    """Reordena produtos do catálogo."""

    def post(self, request, *args, **kwargs):
        company = self.get_company()
        order_ids_raw = request.POST.get('order_ids_list', '')
        order_ids = [value for value in order_ids_raw.split(',') if value]
        if not order_ids:
            messages.warning(request, 'Nenhuma ordem informada.')
            return redirect('public-catalog-admin-products')
        with transaction.atomic():
            for index, catalog_id in enumerate(order_ids):
                CatalogProduct.objects.filter(company=company, id=catalog_id).update(
                    display_order=index,
                )
        clear_public_catalog_cache(company)
        log_admin_action(
            request,
            action='product_reorder',
            message='Ordem de produtos do catálogo atualizada.',
            metadata={'count': len(order_ids)},
        )
        messages.success(request, 'Ordem de produtos atualizada.')
        return redirect('public-catalog-admin-products')


class CatalogCategoryListView(CompanyContextMixin, ListView):
    """Lista de categorias públicas."""

    template_name = 'public_catalog/admin/category_list.html'
    context_object_name = 'catalog_categories'

    def ensure_catalog_categories(self, company):
        """Garante registros de catálogo para todas as categorias."""
        categories = Category.objects.filter(company=company)
        existing_ids = CatalogCategory.objects.filter(
            company=company,
        ).values_list('category_id', flat=True)
        missing_categories = categories.exclude(id__in=existing_ids)
        CatalogCategory.objects.bulk_create(
            [
                CatalogCategory(company=company, category=category)
                for category in missing_categories
            ],
            ignore_conflicts=True,
        )

    def get_queryset(self):
        """Filtra categorias conforme parâmetros."""
        company = self.get_company()
        self.ensure_catalog_categories(company)
        queryset = (
            CatalogCategory.objects.select_related('category')
            .filter(company=company)
            .order_by('display_order', 'category__name')
        )
        visibility = self.request.GET.get('visibility')
        if visibility == 'visible':
            queryset = queryset.filter(is_visible_public=True)
        elif visibility == 'hidden':
            queryset = queryset.filter(is_visible_public=False)
        return queryset

    def get_context_data(self, **kwargs):
        """Inclui filtros atuais."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'page_title': 'Categorias do Catálogo',
                'selected_visibility': self.request.GET.get('visibility', ''),
            }
        )
        return context


class CatalogCategoryUpdateView(CompanyContextMixin, UpdateView):
    """Edição de categoria pública."""

    template_name = 'public_catalog/admin/category_edit.html'
    form_class = CatalogCategoryForm
    model = CatalogCategory

    def get_queryset(self):
        """Restringe o queryset à empresa atual."""
        company = self.get_company()
        return CatalogCategory.objects.select_related('category').filter(company=company)

    def form_valid(self, form):
        """Salva a categoria pública."""
        category = form.save(commit=False)
        category.company = self.get_company()
        category.save()
        clear_public_catalog_cache(self.get_company())
        log_admin_action(
            self.request,
            action='category_updated',
            message='Categoria do catálogo atualizada.',
            target=category,
        )
        messages.success(self.request, 'Categoria atualizada com sucesso.')
        return redirect('public-catalog-admin-categories')


class CatalogCategoryReorderView(CompanyContextMixin, TemplateView):
    """Reordena categorias do catálogo."""

    def post(self, request, *args, **kwargs):
        company = self.get_company()
        order_ids_raw = request.POST.get('order_ids_list', '')
        order_ids = [value for value in order_ids_raw.split(',') if value]
        if not order_ids:
            messages.warning(request, 'Nenhuma ordem informada.')
            return redirect('public-catalog-admin-categories')
        with transaction.atomic():
            for index, catalog_id in enumerate(order_ids):
                CatalogCategory.objects.filter(company=company, id=catalog_id).update(
                    display_order=index,
                )
        clear_public_catalog_cache(company)
        log_admin_action(
            request,
            action='category_reorder',
            message='Ordem de categorias do catálogo atualizada.',
            metadata={'count': len(order_ids)},
        )
        messages.success(request, 'Ordem de categorias atualizada.')
        return redirect('public-catalog-admin-categories')


class CatalogOrderListView(CompanyContextMixin, ListView):
    """Lista pedidos recebidos via catálogo público."""

    template_name = 'public_catalog/admin/order_list.html'
    context_object_name = 'orders'

    def get_queryset(self):
        company = self.get_company()
        queryset = CatalogOrder.objects.filter(company=company).order_by('-created_at')
        status = self.request.GET.get('status', '')
        customer = (self.request.GET.get('customer') or '').strip()
        order_number = (self.request.GET.get('order_number') or '').strip()
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        if status:
            queryset = queryset.filter(status=status)
        if customer:
            queryset = queryset.filter(customer_name__icontains=customer)
        if order_number:
            queryset = queryset.filter(order_number__icontains=order_number)
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'page_title': 'Pedidos do Catálogo',
                'status_choices': CatalogOrder.STATUS_CHOICES,
                'selected_status': self.request.GET.get('status', ''),
                'selected_customer': self.request.GET.get('customer', ''),
                'selected_order_number': self.request.GET.get('order_number', ''),
                'selected_start_date': self.request.GET.get('start_date', ''),
                'selected_end_date': self.request.GET.get('end_date', ''),
            }
        )
        return context


class CatalogOrderDetailView(CompanyContextMixin, TemplateView):
    """Detalhes e atualização de pedidos do catálogo."""

    template_name = 'public_catalog/admin/order_detail.html'

    def get_order(self):
        company = self.get_company()
        return get_object_or_404(
            CatalogOrder,
            company=company,
            order_number=self.kwargs['order_number'],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.get_order()
        context.update(
            {
                'page_title': f'Pedido {order.order_number}',
                'order': order,
                'status_choices': CatalogOrder.STATUS_CHOICES,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        order = self.get_order()
        action = request.POST.get('action')

        if action == 'update_status':
            new_status = request.POST.get('status')
            if new_status == 'finalizado':
                if finalize_catalog_order(order, company=self.get_company()):
                    log_admin_action(
                        request,
                        action='order_finalized',
                        message='Pedido do catálogo finalizado e convertido em venda.',
                        target=order,
                    )
                    messages.success(request, 'Pedido finalizado e convertido em venda.')
                else:
                    messages.error(request, 'Não foi possível finalizar o pedido.')
                return redirect('public-catalog-admin-orders')

            valid_status = {choice[0] for choice in CatalogOrder.STATUS_CHOICES}
            if new_status in valid_status:
                order.status = new_status
                order.save(update_fields=['status'])
                log_admin_action(
                    request,
                    action='order_status_updated',
                    message='Status do pedido do catálogo atualizado.',
                    target=order,
                    metadata={'status': new_status},
                )
                messages.success(request, 'Status atualizado com sucesso.')
            else:
                messages.error(request, 'Status inválido.')
            return redirect('public-catalog-admin-order-detail', order_number=order.order_number)

        if action == 'convert_to_order':
            company = self.get_company()
            pedido_code = generate_sale_code(company, extra_querysets=[Pedido.objects.filter(company=company)])
            with transaction.atomic():
                pedido = Pedido.objects.create(
                    company=company,
                    customer_name=order.customer_name,
                    code=pedido_code,
                    sub_total=float(order.total_value),
                    tax=0,
                    tax_amount=0,
                    grand_total=float(order.total_value),
                    tendered_amount=0,
                    amount_change=0,
                    forma_pagamento=order.payment_method or 'PIX',
                    endereco_entrega=order.delivery_address or '',
                    taxa_entrega=0,
                    discount_total=0,
                    discount_reason='',
                    status='pendente',
                )

                for item in order.items:
                    product = Products.objects.filter(company=company, id=item['product_id']).first()
                    if not product:
                        continue
                    qty = float(item['quantity'])
                    price = float(item['unit_price'])
                    total = float(item['subtotal'])
                    PedidoItem.objects.create(
                        pedido=pedido,
                        product=product,
                        price=price,
                        qty=qty,
                        total=total,
                    )

            messages.success(request, 'Pedido convertido para o sistema interno.')
            log_admin_action(
                request,
                action='order_converted',
                message='Pedido do catálogo convertido para pedido interno.',
                target=order,
                metadata={'pedido_id': pedido.id},
            )
            return redirect('public-catalog-admin-order-detail', order_number=order.order_number)

        messages.error(request, 'Ação inválida.')
        return redirect('public-catalog-admin-order-detail', order_number=order.order_number)


class CatalogOrderDeleteView(CompanyContextMixin, TemplateView):
    """Exclui pedidos do catálogo."""

    def post(self, request, *args, **kwargs):
        company = self.get_company()
        order_number = kwargs['order_number']
        order = get_object_or_404(CatalogOrder, company=company, order_number=order_number)
        order.delete()
        log_admin_action(
            request,
            action='order_deleted',
            message='Pedido do catálogo excluído.',
            metadata={'order_number': order_number},
        )
        messages.success(request, 'Pedido excluído com sucesso.')
        return redirect('public-catalog-admin-orders')


class CatalogAnalyticsView(CompanyContextMixin, TemplateView):
    """Dashboard de mÃ©tricas do catÃ¡logo pÃºblico."""

    template_name = 'public_catalog/admin/analytics.html'

    def get_date_range(self):
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if not start_date:
            start_date = (timezone.localdate() - timedelta(days=30)).isoformat()
        if not end_date:
            end_date = timezone.localdate().isoformat()
        return start_date, end_date

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.get_company()
        start_date, end_date = self.get_date_range()

        orders = CatalogOrder.objects.filter(
            company=company,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )

        total_orders = orders.count()
        total_value = orders.aggregate(total=Sum('total_value')).get('total') or 0
        avg_value = orders.aggregate(avg=Avg('total_value')).get('avg') or 0

        orders_by_day = (
            orders.annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        chart_labels = [item['day'].strftime('%d/%m') for item in orders_by_day]
        chart_values = [item['count'] for item in orders_by_day]

        top_viewed_products = (
            CatalogProduct.objects.filter(company=company)
            .select_related('product')
            .order_by('-view_count')[:10]
        )

        context.update(
            {
                'page_title': 'RelatÃ³rios do CatÃ¡logo',
                'total_orders': total_orders,
                'total_value': total_value,
                'avg_value': avg_value,
                'chart_labels': chart_labels,
                'chart_values': chart_values,
                'top_viewed_products': top_viewed_products,
                'selected_start_date': start_date,
                'selected_end_date': end_date,
            }
        )
        return context


def finalize_catalog_order(order: CatalogOrder, company) -> bool:
    """Converte pedido do catálogo em venda."""
    if not order or not company:
        return False
    try:
        with transaction.atomic():
            sale_code = generate_sale_code(company)
            venda = Sales.objects.create(
                company=company,
                code=sale_code,
                sub_total=float(order.total_value),
                tax=0,
                tax_amount=0,
                grand_total=float(order.total_value),
                tendered_amount=0,
                amount_change=0,
                forma_pagamento=order.payment_method or 'PIX',
                endereco_entrega=order.delivery_address or '',
                customer_name=order.customer_name,
                delivery_fee=0,
                discount_total=0,
                discount_reason='',
                type='pedido',
            )

            for item in order.items:
                product = Products.objects.filter(company=company, id=item['product_id']).first()
                if not product:
                    continue
                qty = float(item['quantity'])
                price = float(item['unit_price'])
                total = float(item['subtotal'])
                salesItems.objects.create(
                    sale_id=venda,
                    product_id=product,
                    price=price,
                    qty=qty,
                    total=total,
                )
                try:
                    estoque_item = Estoque.objects.get(produto=product, company=company)
                    estoque_item.quantidade -= qty
                    estoque_item.save(update_fields=['quantidade'])
                except Estoque.DoesNotExist:
                    pass

            order.delete()
    except Exception:
        return False
    return True


class CatalogOrderFinalizeView(CompanyContextMixin, TemplateView):
    """Finaliza pedido e converte em venda."""

    def post(self, request, *args, **kwargs):
        company = self.get_company()
        order = get_object_or_404(
            CatalogOrder,
            company=company,
            order_number=kwargs['order_number'],
        )
        if finalize_catalog_order(order, company=company):
            log_admin_action(
                request,
                action='order_finalized',
                message='Pedido do catálogo finalizado e convertido em venda.',
                target=order,
            )
            messages.success(request, 'Pedido finalizado e convertido em venda.')
        else:
            messages.error(request, 'Não foi possível finalizar o pedido.')
        return redirect('public-catalog-admin-orders')


class CatalogOrdersExportView(CompanyContextMixin, TemplateView):
    """Exporta pedidos do catÃ¡logo para CSV."""

    def get(self, request, *args, **kwargs):
        company = self.get_company()
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        orders = CatalogOrder.objects.filter(company=company)
        if start_date:
            orders = orders.filter(created_at__date__gte=start_date)
        if end_date:
            orders = orders.filter(created_at__date__lte=end_date)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=\"catalog_orders.csv\"'
        response.write('order_number,customer_name,customer_phone,status,total_value,created_at\n')
        for order in orders.order_by('-created_at'):
            row = (
                f'{order.order_number},{order.customer_name},{order.customer_phone},'
                f'{order.status},{order.total_value},{order.created_at:%Y-%m-%d %H:%M:%S}\n'
            )
            response.write(row)
        log_admin_action(
            request,
            action='orders_exported',
            message='Exportação de pedidos do catálogo realizada.',
            metadata={'count': orders.count()},
        )
        return response


class CatalogOrderReceiptView(CompanyContextMixin, TemplateView):
    """Cupom de pedido do catÃ¡logo para impressÃ£o."""

    template_name = 'public_catalog/admin/receipt_catalog_order.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.get_company()
        order = get_object_or_404(
            CatalogOrder,
            company=company,
            order_number=self.kwargs['order_number'],
        )
        items = [
            {
                'name': item.get('product_name'),
                'quantity': item.get('quantity'),
                'notes': item.get('notes', ''),
            }
            for item in order.items
        ]
        context.update(
            {
                'order': order,
                'company': company,
                'items': items,
                'title': 'Cupom do Pedido',
            }
        )
        return context


class CatalogOrderReceiptModalView(CompanyContextMixin, TemplateView):
    """Renderiza o cupom do pedido em modal."""

    template_name = 'public_catalog/admin/receipt_catalog_order_modal.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.get_company()
        order = get_object_or_404(
            CatalogOrder,
            company=company,
            order_number=self.kwargs['order_number'],
        )
        items = [
            {
                'name': item.get('product_name'),
                'quantity': item.get('quantity'),
            }
            for item in order.items
        ]
        context.update(
            {
                'order': order,
                'company': company,
                'items': items,
                'title': 'Cupom do Pedido',
            }
        )
        return context


def get_company_by_slug(slug: str):
    """Obtém a empresa com base no slug do catálogo."""
    settings = CatalogSettings.objects.filter(catalog_slug=slug, catalog_enabled=True).select_related('company').first()
    if not settings:
        raise Http404('Catálogo não encontrado.')
    return settings.company, settings


def ensure_public_catalog_records(company):
    """Garante registros de catálogo para categorias e produtos."""
    categories = Category.objects.filter(company=company)
    existing_category_ids = CatalogCategory.objects.filter(company=company).values_list('category_id', flat=True)
    missing_categories = categories.exclude(id__in=existing_category_ids)
    CatalogCategory.objects.bulk_create(
        [CatalogCategory(company=company, category=category) for category in missing_categories],
        ignore_conflicts=True,
    )

    products = Products.objects.filter(company=company)
    existing_product_ids = CatalogProduct.objects.filter(company=company).values_list('product_id', flat=True)
    missing_products = products.exclude(id__in=existing_product_ids)
    CatalogProduct.objects.bulk_create(
        [CatalogProduct(company=company, product=product) for product in missing_products],
        ignore_conflicts=True,
    )


def get_cached_list(cache_key: str, queryset, ttl: int = 900):
    """Retorna lista cacheada de queryset."""
    try:
        data = cache.get(cache_key)
    except Exception:
        data = None
    if data is None:
        data = list(queryset)
        try:
            cache.set(cache_key, data, ttl)
        except Exception:
            pass
    return data


def build_infinite_payload(request, items, slug, settings, page_obj, show_cart_action=False):
    """Monta resposta JSON para paginação infinita."""
    html = render_to_string(
        'public_catalog/public/_product_cards.html',
        {
            'products': items,
            'settings': settings,
            'slug': slug,
            'show_cart_action': show_cart_action,
        },
        request=request,
    )
    return JsonResponse(
        {
            'html': html,
            'has_next': page_obj.has_next(),
            'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
        }
    )


def get_cart_key(slug: str) -> str:
    """Gera a chave de sessão para o carrinho de um catálogo."""
    return f'public_catalog_cart_{slug}'


def clear_public_catalog_cache(company) -> None:
    """Limpa caches do cat?logo p?blico para a empresa."""
    if not company:
        return
    keys = [
        f'public_catalog_categories_{company.id}',
        f'public_catalog_featured_{company.id}',
    ]
    category_ids = Category.objects.filter(company=company).values_list('id', flat=True)
    keys.extend([
        f'public_catalog_products_{company.id}_{category_id}_all'
        for category_id in category_ids
    ])
    try:
        cache.delete_many(keys)
        cache.clear()
    except Exception:
        try:
            cache.clear()
        except Exception:
            pass


def get_cart_items(request, slug: str, company):
    """Retorna itens do carrinho com detalhes do produto."""
    cart = request.session.get(get_cart_key(slug), {})
    product_ids = [int(pid) for pid in cart.keys()]
    products = Products.objects.filter(company=company, id__in=product_ids)
    items = []
    total = Decimal('0.00')
    for product in products:
        qty = int(cart.get(str(product.id), 0))
        if qty <= 0:
            continue
        price = Decimal(str(product.price))
        subtotal = price * qty
        total += subtotal
        items.append(
            {
                'product': product,
                'quantity': qty,
                'unit_price': price,
                'subtotal': subtotal,
            }
        )
    return items, total


def add_to_cart(request, slug: str, product_id: int, quantity: int = 1):
    """Adiciona um produto ao carrinho."""
    cart_key = get_cart_key(slug)
    cart = request.session.get(cart_key, {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + quantity
    request.session[cart_key] = cart
    request.session.modified = True


def update_cart_item(request, slug: str, product_id: int, quantity: int):
    """Atualiza a quantidade de um item no carrinho."""
    cart_key = get_cart_key(slug)
    cart = request.session.get(cart_key, {})
    if quantity <= 0:
        cart.pop(str(product_id), None)
    else:
        cart[str(product_id)] = quantity
    request.session[cart_key] = cart
    request.session.modified = True


def remove_from_cart(request, slug: str, product_id: int):
    """Remove item do carrinho."""
    cart_key = get_cart_key(slug)
    cart = request.session.get(cart_key, {})
    cart.pop(str(product_id), None)
    request.session[cart_key] = cart
    request.session.modified = True


@method_decorator(ratelimit(key='ip', rate='100/h', method='GET', block=True), name='dispatch')
class PublicCatalogHomeView(TemplateView):
    """Página inicial do catálogo público."""

    template_name = 'public_catalog/public/home.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' and context.get('search_query'):
            return build_infinite_payload(
                request,
                context.get('search_results', []),
                context.get('slug'),
                context.get('settings'),
                context.get('search_page_obj'),
                show_cart_action=False,
            )
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs['slug']
        company, settings = get_company_by_slug(slug)
        ensure_public_catalog_records(company)
        categories = get_cached_list(
            f'public_catalog_categories_{company.id}',
            CatalogCategory.objects.filter(
                company=company,
                is_visible_public=True,
            ).select_related('category').order_by('display_order', 'category__name'),
        )
        featured_products = get_cached_list(
            f'public_catalog_featured_{company.id}',
            CatalogProduct.objects.filter(
                company=company,
                is_visible_public=True,
                highlighted=True,
            ).select_related('product').prefetch_related('product__images')[:6],
        )
        query = (self.request.GET.get('q') or '').strip()
        search_page_obj = None
        search_results = []
        if query:
            search_queryset = (
                CatalogProduct.objects.filter(
                    company=company,
                    is_visible_public=True,
                    product__name__icontains=query,
                )
                .select_related('product')
                .prefetch_related('product__images')
            )
            paginator = Paginator(search_queryset, 12)
            search_page_obj = paginator.get_page(self.request.GET.get('page') or 1)
            search_results = search_page_obj.object_list
        context.update(
            {
                'company': company,
                'settings': settings,
                'categories': categories,
                'featured_products': featured_products,
                'search_query': query,
                'search_results': search_results,
                'search_page_obj': search_page_obj,
                'slug': slug,
                'current_path': self.request.get_full_path(),
            }
        )
        return context


@method_decorator(ratelimit(key='ip', rate='100/h', method='GET', block=True), name='dispatch')
class PublicCatalogCategoryView(TemplateView):
    """Produtos por categoria no catálogo público."""

    template_name = 'public_catalog/public/category.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return build_infinite_payload(
                request,
                context.get('products', []),
                context.get('slug'),
                context.get('settings'),
                context.get('page_obj'),
                show_cart_action=True,
            )
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs['slug']
        category_id = self.kwargs['category_id']
        company, settings = get_company_by_slug(slug)
        ensure_public_catalog_records(company)
        category = get_object_or_404(
            CatalogCategory,
            company=company,
            category_id=category_id,
            is_visible_public=True,
        )
        query = (self.request.GET.get('q') or '').strip()
        product_queryset = CatalogProduct.objects.filter(
            company=company,
            is_visible_public=True,
            product__category_id=category.category_id,
        )
        if query:
            product_queryset = product_queryset.filter(product__name__icontains=query)
        product_list = get_cached_list(
            f'public_catalog_products_{company.id}_{category.category_id}_{query or "all"}',
            product_queryset.select_related('product').prefetch_related('product__images').order_by(
                'display_order',
                'product__name',
            ),
        )
        paginator = Paginator(product_list, 12)
        page_obj = paginator.get_page(self.request.GET.get('page') or 1)
        products = page_obj.object_list
        context.update(
            {
                'company': company,
                'settings': settings,
                'category': category,
                'products': products,
                'page_obj': page_obj,
                'slug': slug,
                'search_query': query,
                'current_path': self.request.get_full_path(),
            }
        )
        return context


@method_decorator(ratelimit(key='ip', rate='100/h', method='GET', block=True), name='dispatch')
class PublicCatalogProductDetailView(TemplateView):
    """Detalhes de produto do catálogo público."""

    template_name = 'public_catalog/public/product_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs['slug']
        product_id = self.kwargs['product_id']
        company, settings = get_company_by_slug(slug)
        ensure_public_catalog_records(company)
        catalog_product = get_object_or_404(
            CatalogProduct,
            company=company,
            product_id=product_id,
            is_visible_public=True,
        )
        images = ProductImage.objects.filter(product_id=product_id).order_by('-is_primary', 'display_order')
        catalog_product.increment_view_count()
        context.update(
            {
                'company': company,
                'settings': settings,
                'catalog_product': catalog_product,
                'images': images,
                'slug': slug,
            }
        )
        return context


@method_decorator(ratelimit(key='ip', rate='100/h', method='GET', block=True), name='dispatch')
class PublicCatalogCartView(TemplateView):
    """Visualização do carrinho."""

    template_name = 'public_catalog/public/cart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs['slug']
        company, settings = get_company_by_slug(slug)
        items, total = get_cart_items(self.request, slug, company)
        context.update(
            {
                'company': company,
                'settings': settings,
                'items': items,
                'total': total,
                'slug': slug,
            }
        )
        return context


@method_decorator(ratelimit(key='ip', rate='100/h', method='GET', block=True), name='dispatch')
@method_decorator(ratelimit(key='ip', rate='30/h', method='POST', block=True), name='dispatch')
class CatalogCheckoutView(FormView):
    """Formulário de checkout do catálogo público."""

    template_name = 'public_catalog/public/checkout.html'
    form_class = CheckoutForm

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs['slug']
        self.company, self.settings = get_company_by_slug(self.slug)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        items, total = get_cart_items(self.request, self.slug, self.company)
        context.update(
            {
                'company': self.company,
                'settings': self.settings,
                'items': items,
                'total': total,
                'slug': self.slug,
            }
        )
        return context

    def form_valid(self, form):
        items, total = get_cart_items(self.request, self.slug, self.company)
        if not items:
            messages.error(self.request, 'Seu carrinho está vazio.')
            return redirect('public-catalog-cart', slug=self.slug)

        order_items = []
        for item in items:
            order_items.append(
                {
                    'product_id': item['product'].id,
                    'product_name': item['product'].name,
                    'quantity': item['quantity'],
                    'unit_price': float(item['unit_price']),
                    'subtotal': float(item['subtotal']),
                }
            )

        order = CatalogOrder.objects.create(
            company=self.company,
            customer_name=form.cleaned_data['customer_name'],
            customer_phone=form.cleaned_data['customer_phone'],
            customer_notes=form.cleaned_data.get('customer_notes', ''),
            delivery_address=form.cleaned_data.get('delivery_address', ''),
            payment_method=form.cleaned_data.get('payment_method', 'PIX'),
            items=order_items,
            total_value=total,
            status='novo',
        )

        self.request.session[get_cart_key(self.slug)] = {}
        self.request.session.modified = True

        return redirect('public-catalog-send-whatsapp', slug=self.slug, order_number=order.order_number)


@method_decorator(ratelimit(key='ip', rate='30/h', method='GET', block=True), name='dispatch')
class SendToWhatsAppView(TemplateView):
    """Gera mensagem e redireciona para WhatsApp."""

    def get(self, request, *args, **kwargs):
        slug = kwargs['slug']
        order_number = kwargs['order_number']
        company, settings = get_company_by_slug(slug)
        order = get_object_or_404(CatalogOrder, company=company, order_number=order_number)

        if not settings.whatsapp_number:
            messages.error(
                request,
                'Número de WhatsApp não configurado. Entre em contato com a empresa.',
            )
            return redirect('public-catalog-confirmation', slug=slug, order_number=order_number)

        order.whatsapp_sent_at = timezone.now()
        order.save(update_fields=['whatsapp_sent_at'])
        return redirect(get_whatsapp_url(order))


@method_decorator(ratelimit(key='ip', rate='100/h', method='GET', block=True), name='dispatch')
class OrderConfirmationView(TemplateView):
    """Página de confirmação após envio do pedido."""

    template_name = 'public_catalog/public/confirmation.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs['slug']
        order_number = self.kwargs['order_number']
        company, settings = get_company_by_slug(slug)
        order = get_object_or_404(CatalogOrder, company=company, order_number=order_number)
        context.update(
            {
                'company': company,
                'settings': settings,
                'order': order,
                'slug': slug,
            }
        )
        return context


@require_POST
@ratelimit(key='ip', rate='100/h', method='POST', block=True)
def add_to_cart_view(request, slug: str, product_id: int):
    """Endpoint de adição ao carrinho."""
    company, _settings = get_company_by_slug(slug)
    get_object_or_404(
        CatalogProduct,
        company=company,
        product_id=product_id,
        is_visible_public=True,
    )
    add_to_cart(request, slug, product_id, quantity=int(request.POST.get('quantity', 1)))
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})
    messages.success(request, 'Produto adicionado ao carrinho.')
    return redirect('public-catalog-cart', slug=slug)


@require_POST
@ratelimit(key='ip', rate='100/h', method='POST', block=True)
def update_cart_item_view(request, slug: str, product_id: int):
    """Endpoint de atualização de carrinho."""
    company, _settings = get_company_by_slug(slug)
    get_object_or_404(CatalogProduct, company=company, product_id=product_id)
    update_cart_item(request, slug, product_id, quantity=int(request.POST.get('quantity', 1)))
    messages.success(request, 'Carrinho atualizado.')
    return redirect('public-catalog-cart', slug=slug)


@require_POST
@ratelimit(key='ip', rate='100/h', method='POST', block=True)
def remove_from_cart_view(request, slug: str, product_id: int):
    """Endpoint de remoção do carrinho."""
    company, _settings = get_company_by_slug(slug)
    get_object_or_404(CatalogProduct, company=company, product_id=product_id)
    remove_from_cart(request, slug, product_id)
    messages.success(request, 'Item removido do carrinho.')
    return redirect('public-catalog-cart', slug=slug)
