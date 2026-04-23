from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from store import views

urlpatterns = [
    path('dashboard/', views.admin_dashboard_view, name='custom_admin_dashboard'),
    path('admin/', admin.site.urls),
    path('', include('store.urls')), # This connects to your store!
    path('dashboard/upload-excel/', views.admin_excel_upload, name='admin_excel_upload'),
    path('dashboard/download-template/', views.download_excel_template, name='download_excel_template'),
    path('dashboard/product/add/', views.admin_add_product, name='admin_add_product'),
    path('dashboard/inventory/', views.admin_inventory, name='admin_inventory'),
    path('dashboard/categories/', views.admin_categories, name='admin_categories'),
    path('dashboard/product/<int:product_id>/edit/', views.admin_edit_product, name='admin_edit_product'),
    path('dashboard/category/<int:category_id>/edit/', views.admin_edit_category, name='admin_edit_category'),
    path('dashboard/attributes/', views.admin_attributes, name='admin_attributes'),
    path('dashboard/banners/', views.admin_banners, name='admin_banners'),
    path('dashboard/banners/delete/<int:banner_id>/', views.delete_banner, name='delete_banner'),
    path('dashboard/excel-review/', views.admin_excel_review, name='admin_excel_review'),
    path('dashboard/bulk-images/', views.admin_bulk_image_upload, name='admin_bulk_image_upload'),
    path('dashboard/duplicates/', views.admin_find_duplicates, name='admin_find_duplicates'),
    path('dashboard/duplicates/merge/', views.admin_merge_duplicates, name='admin_merge_duplicates'),
    path('dashboard/offer-generator/', views.admin_offer_generator, name='admin_offer_generator'),
    path('dashboard/duplicates/rename/', views.admin_quick_rename, name='admin_quick_rename'),
    path('dashboard/duplicates/bulk-merge/', views.admin_bulk_merge_all, name='admin_bulk_merge_all'),
    path('dashboard/system/factory-reset/', views.admin_factory_reset, name='admin_factory_reset'),
    path('dashboard/system/', views.admin_system_settings, name='admin_system_settings'),
    path('dashboard/system/backup/', views.admin_database_backup, name='admin_database_backup'),
    path('dashboard/system/restore/', views.admin_database_restore, name='admin_database_restore'),
    path('dashboard/system/factory-reset/', views.admin_factory_reset, name='admin_factory_reset'),
]

# This is required to show uploaded images during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)