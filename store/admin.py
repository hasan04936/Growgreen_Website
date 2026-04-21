from django.contrib import admin, messages
from django.urls import path
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
import pandas as pd
from .models import Category, Volume, Unit, Product


# --- THESE ARE THE PIECES THAT WENT MISSING! ---
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name_en', 'name_ar')
    search_fields = ('name_en', 'name_ar')


@admin.register(Volume)
class VolumeAdmin(admin.ModelAdmin):
    list_display = ('name_en', 'name_ar')


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('name_en', 'name_ar')


# -----------------------------------------------

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name_en', 'category', 'is_new_arrival')
    list_filter = ('category', 'is_new_arrival')
    search_fields = ('name_en', 'name_ar')
    filter_horizontal = ('available_volumes', 'available_units')

    # Custom URLs for our buttons
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('download-template/', self.admin_site.admin_view(self.download_template), name='download_template'),
            path('upload-excel/', self.admin_site.admin_view(self.upload_excel), name='upload_excel'),
        ]
        return custom_urls + urls

    # Generate the Excel Template
    def download_template(self, request):
        columns = [
            'Category (Exact English Name)',
            'Name (English)',
            'Name (Arabic)',
            'Is New Arrival (Yes/No)',
            'Volumes (Comma separated, e.g., 500ml, 1L)',
            'Units (Comma separated, e.g., PCS, Dozen)'
        ]
        df = pd.DataFrame(columns=columns)

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="GrowGreen_Product_Template.xlsx"'
        df.to_excel(response, index=False)
        return response

    # Process the Uploaded Excel
    def upload_excel(self, request):
        if request.method == 'POST':
            excel_file = request.FILES.get('excel_file')

            if not excel_file:
                messages.error(request, "Please select a file.")
                return HttpResponseRedirect(".")

            try:
                df = pd.read_excel(excel_file)
                products_created = 0

                for index, row in df.iterrows():
                    # 1. Find the Category
                    cat_name = str(row['Category (Exact English Name)']).strip()
                    category = Category.objects.filter(name_en__iexact=cat_name).first()

                    if not category:
                        continue

                        # 2. Create the base Product
                    is_new = str(row['Is New Arrival (Yes/No)']).strip().lower() == 'yes'

                    product = Product.objects.create(
                        category=category,
                        name_en=str(row['Name (English)']).strip(),
                        name_ar=str(row['Name (Arabic)']).strip(),
                        is_new_arrival=is_new
                    )

                    # 3. Link Volumes
                    volumes_str = str(row['Volumes (Comma separated, e.g., 500ml, 1L)'])
                    if volumes_str != 'nan':
                        vol_list = [v.strip() for v in volumes_str.split(',')]
                        for v_name in vol_list:
                            vol_obj = Volume.objects.filter(name_en__iexact=v_name).first()
                            if vol_obj:
                                product.available_volumes.add(vol_obj)

                    # 4. Link Units
                    units_str = str(row['Units (Comma separated, e.g., PCS, Dozen)'])
                    if units_str != 'nan':
                        unit_list = [u.strip() for u in units_str.split(',')]
                        for u_name in unit_list:
                            unit_obj = Unit.objects.filter(name_en__iexact=u_name).first()
                            if unit_obj:
                                product.available_units.add(unit_obj)

                    products_created += 1

                messages.success(request, f"Successfully imported {products_created} products!")
                return HttpResponseRedirect("..")

            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
                return HttpResponseRedirect(".")

        return render(request, "admin/excel_upload_form.html")