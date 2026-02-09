from django.urls import path

from . import views

urlpatterns = [
    path('<slug:slug>/', views.PublicCatalogHomeView.as_view(), name='public-catalog-home'),
    path('<slug:slug>/categoria/<int:category_id>/', views.PublicCatalogCategoryView.as_view(), name='public-catalog-category'),
    path('<slug:slug>/produto/<int:product_id>/', views.PublicCatalogProductDetailView.as_view(), name='public-catalog-product-detail'),
    path('<slug:slug>/carrinho/', views.PublicCatalogCartView.as_view(), name='public-catalog-cart'),
    path('<slug:slug>/carrinho/adicionar/<int:product_id>/', views.add_to_cart_view, name='public-catalog-add-to-cart'),
    path('<slug:slug>/carrinho/atualizar/<int:product_id>/', views.update_cart_item_view, name='public-catalog-update-cart'),
    path('<slug:slug>/carrinho/remover/<int:product_id>/', views.remove_from_cart_view, name='public-catalog-remove-cart'),
    path('<slug:slug>/checkout/', views.CatalogCheckoutView.as_view(), name='public-catalog-checkout'),
    path('<slug:slug>/enviar-whatsapp/<str:order_number>/', views.SendToWhatsAppView.as_view(), name='public-catalog-send-whatsapp'),
    path('<slug:slug>/confirmacao/<str:order_number>/', views.OrderConfirmationView.as_view(), name='public-catalog-confirmation'),
    path('admin/configuracoes/', views.CatalogSettingsView.as_view(), name='public-catalog-admin-settings'),
    path('admin/produtos/', views.CatalogProductListView.as_view(), name='public-catalog-admin-products'),
    path('admin/produtos/acao-em-massa/', views.CatalogProductBulkActionView.as_view(), name='public-catalog-admin-products-bulk'),
    path('admin/produtos/reordenar/', views.CatalogProductReorderView.as_view(), name='public-catalog-admin-products-reorder'),
    path('admin/produtos/<int:pk>/editar/', views.CatalogProductUpdateView.as_view(), name='public-catalog-admin-product-edit'),
    path('admin/categorias/', views.CatalogCategoryListView.as_view(), name='public-catalog-admin-categories'),
    path('admin/categorias/reordenar/', views.CatalogCategoryReorderView.as_view(), name='public-catalog-admin-categories-reorder'),
    path('admin/categorias/<int:pk>/editar/', views.CatalogCategoryUpdateView.as_view(), name='public-catalog-admin-category-edit'),
    path('admin/pedidos/', views.CatalogOrderListView.as_view(), name='public-catalog-admin-orders'),
    path('admin/pedidos/<str:order_number>/', views.CatalogOrderDetailView.as_view(), name='public-catalog-admin-order-detail'),
    path('admin/pedidos/<str:order_number>/excluir/', views.CatalogOrderDeleteView.as_view(), name='public-catalog-admin-order-delete'),
    path('admin/pedidos/<str:order_number>/cupom/', views.CatalogOrderReceiptView.as_view(), name='public-catalog-admin-order-receipt'),
    path('admin/pedidos/<str:order_number>/cupom/modal/', views.CatalogOrderReceiptModalView.as_view(), name='public-catalog-admin-order-receipt-modal'),
    path('admin/pedidos/<str:order_number>/finalizar/', views.CatalogOrderFinalizeView.as_view(), name='public-catalog-admin-order-finalize'),
    path('admin/relatorios/', views.CatalogAnalyticsView.as_view(), name='public-catalog-admin-analytics'),
    path('admin/relatorios/exportar/', views.CatalogOrdersExportView.as_view(), name='public-catalog-admin-export'),
]
