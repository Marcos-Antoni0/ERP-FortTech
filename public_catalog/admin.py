from django.contrib import admin

from .models import (
    CatalogAuditLog,
    CatalogCategory,
    CatalogOrder,
    CatalogProduct,
    CatalogSettings,
    ProductImage,
)


@admin.register(CatalogSettings)
class CatalogSettingsAdmin(admin.ModelAdmin):
    list_display = ('catalog_title', 'company', 'catalog_slug', 'catalog_enabled')
    search_fields = ('catalog_title', 'catalog_slug', 'company__name')
    list_filter = ('catalog_enabled',)


@admin.register(CatalogCategory)
class CatalogCategoryAdmin(admin.ModelAdmin):
    list_display = ('category', 'is_visible_public', 'display_order')
    list_filter = ('is_visible_public',)
    search_fields = ('category__name',)


@admin.register(CatalogProduct)
class CatalogProductAdmin(admin.ModelAdmin):
    list_display = ('product', 'is_visible_public', 'highlighted', 'display_order')
    list_filter = ('is_visible_public', 'highlighted')
    search_fields = ('product__name', 'product__code')


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'is_primary', 'display_order')
    list_filter = ('is_primary',)
    search_fields = ('product__name',)


@admin.register(CatalogOrder)
class CatalogOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer_name', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order_number', 'customer_name', 'customer_phone')


@admin.register(CatalogAuditLog)
class CatalogAuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'user', 'company', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('action', 'message', 'object_type', 'object_id', 'user__username')
