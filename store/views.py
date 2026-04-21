from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import redirect
import pandas as pd
from .models import Category, Volume, Unit, Product, Banner


def home(request):
    # Pull data from the database
    categories = Category.objects.all()
    new_arrivals = Product.objects.filter(is_new_arrival=True)
    products = Product.objects.all()
    banners = Banner.objects.all()

    # Package it up to send to the HTML template
    context = {
        'categories': categories,
        'new_arrivals': new_arrivals,
        'products': products,
        'banners': banners,
    }
    return render(request, 'store/index.html', context)


@staff_member_required
def admin_dashboard_view(request):
    """
    Custom Luxury Admin Dashboard View
    Requires the user to be logged in as an Admin (staff_member).
    """
    product_count = Product.objects.count()
    category_count = Category.objects.count()
    recent_products = Product.objects.order_by('-id')[:5]  # Get the last 5 added products

    context = {
        'product_count': product_count,
        'category_count': category_count,
        'recent_products': recent_products,
    }

    return render(request, 'store/dashboard.html', context)


@staff_member_required
def admin_excel_upload(request):
    if request.method == 'POST':
        excel_file = request.FILES.get('excel_file')
        if not excel_file:
            messages.error(request, "Please select a file.")
            return redirect('admin_excel_upload')

        try:
            df = pd.read_excel(excel_file)
            products_created = 0

            for index, row in df.iterrows():
                # 1. Handle Category (Auto-Create if missing)
                cat_name = str(row['Category (Exact English Name)']).strip()
                if cat_name == 'nan' or not cat_name:
                    continue  # Skip if category cell is totally empty

                # get_or_create will find it, or build it if it's brand new!
                category, created = Category.objects.get_or_create(
                    name_en__iexact=cat_name,
                    defaults={'name_en': cat_name, 'name_ar': cat_name}
                )

                # 2. Create Product
                is_new = str(row['Is New Arrival (Yes/No)']).strip().lower() == 'yes'

                # Check for empty names to avoid "nan"
                name_en = str(row['Name (English)']).strip()
                name_ar = str(row['Name (Arabic)']).strip()
                if name_en == 'nan': name_en = "Unnamed Product"
                if name_ar == 'nan': name_ar = "منتج غير مسمى"

                product = Product.objects.create(
                    category=category,
                    name_en=name_en,
                    name_ar=name_ar,
                    is_new_arrival=is_new
                )

                # 3. Handle Volumes (Auto-Create if missing)
                volumes_str = str(row['Volumes (Comma separated, e.g., 500ml, 1L)'])
                if volumes_str != 'nan' and volumes_str.strip():
                    vol_list = [v.strip() for v in volumes_str.split(',') if v.strip()]
                    for v_name in vol_list:
                        vol_obj, created = Volume.objects.get_or_create(
                            name_en__iexact=v_name,
                            defaults={'name_en': v_name, 'name_ar': v_name}
                        )
                        product.available_volumes.add(vol_obj)

                # 4. Handle Units (Auto-Create if missing)
                units_str = str(row['Units (Comma separated, e.g., PCS, Dozen)'])
                if units_str != 'nan' and units_str.strip():
                    unit_list = [u.strip() for u in units_str.split(',') if u.strip()]
                    for u_name in unit_list:
                        unit_obj, created = Unit.objects.get_or_create(
                            name_en__iexact=u_name,
                            defaults={'name_en': u_name, 'name_ar': u_name}
                        )
                        product.available_units.add(unit_obj)

                products_created += 1

            messages.success(request,
                             f"Successfully imported {products_created} products! Any missing categories, volumes, or units were auto-generated.")
            return redirect('custom_admin_dashboard')

        except Exception as e:
            messages.error(request, f"Error processing file: {str(e)}")
            return redirect('admin_excel_upload')

    return render(request, 'store/admin_excel_upload.html')

@staff_member_required
def download_excel_template(request):
    columns = [
        'Category (Exact English Name)', 'Name (English)', 'Name (Arabic)',
        'Is New Arrival (Yes/No)', 'Volumes (Comma separated, e.g., 500ml, 1L)',
        'Units (Comma separated, e.g., PCS, Dozen)'
    ]
    df = pd.DataFrame(columns=columns)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="GrowGreen_Product_Template.xlsx"'
    df.to_excel(response, index=False)
    return response

@staff_member_required
def admin_add_product(request):
    if request.method == 'POST':
        # Get basic text data
        name_en = request.POST.get('name_en')
        name_ar = request.POST.get('name_ar')
        category_id = request.POST.get('category')
        is_new_arrival = 'is_new_arrival' in request.POST
        image_1 = request.FILES.get('image_1')

        try:
            # Fetch the selected category
            category = Category.objects.get(id=category_id)

            # Create the product
            product = Product.objects.create(
                name_en=name_en,
                name_ar=name_ar,
                category=category,
                is_new_arrival=is_new_arrival,
            )

            # Add image if uploaded
            if image_1:
                product.image_1 = image_1
                product.save()

            # Handle ManyToMany fields (Volumes and Units)
            # request.POST.getlist() grabs all checked boxes with that name
            volume_ids = request.POST.getlist('volumes')
            if volume_ids:
                volumes = Volume.objects.filter(id__in=volume_ids)
                product.available_volumes.set(volumes)

            unit_ids = request.POST.getlist('units')
            if unit_ids:
                units = Unit.objects.filter(id__in=unit_ids)
                product.available_units.set(units)

            messages.success(request, f"Product '{name_en}' added successfully!")
            return redirect('custom_admin_dashboard')

        except Exception as e:
            messages.error(request, f"Error adding product: {str(e)}")
            return redirect('admin_add_product')

    # If GET request, send all categories, volumes, and units to the template
    context = {
        'categories': Category.objects.all(),
        'volumes': Volume.objects.all(),
        'units': Unit.objects.all(),
    }
    return render(request, 'store/admin_add_product.html', context)


@staff_member_required
def admin_inventory(request):
    # Fetch all products, ordered by the newest first
    products = Product.objects.all().order_by('-id')

    context = {
        'products': products,
    }
    return render(request, 'store/admin_inventory.html', context)


@staff_member_required
def admin_categories(request):
    if request.method == 'POST':
        name_en = request.POST.get('name_en')
        name_ar = request.POST.get('name_ar')
        image = request.FILES.get('image')

        try:
            category = Category.objects.create(
                name_en=name_en,
                name_ar=name_ar,
            )
            if image:
                category.image = image
                category.save()

            messages.success(request, f"Collection '{name_en}' added successfully!")
            return redirect('admin_categories')

        except Exception as e:
            messages.error(request, f"Error adding collection: {str(e)}")
            return redirect('admin_categories')

    categories = Category.objects.all().order_by('-id')
    context = {
        'categories': categories,
    }
    return render(request, 'store/admin_categories.html', context)


@staff_member_required
def admin_edit_product(request, product_id):
    # Fetch the exact product from the database
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        try:
            # Update basic text data
            product.name_en = request.POST.get('name_en')
            product.name_ar = request.POST.get('name_ar')
            product.category_id = request.POST.get('category')
            product.is_new_arrival = 'is_new_arrival' in request.POST

            # Only update the image if a new one was uploaded
            image_1 = request.FILES.get('image_1')
            if image_1:
                product.image_1 = image_1

            product.save()

            # Update ManyToMany fields (Volumes and Units)
            volume_ids = request.POST.getlist('volumes')
            product.available_volumes.set(Volume.objects.filter(id__in=volume_ids))

            unit_ids = request.POST.getlist('units')
            product.available_units.set(Unit.objects.filter(id__in=unit_ids))

            messages.success(request, f"Product '{product.name_en}' updated successfully!")
            return redirect('admin_inventory')

        except Exception as e:
            messages.error(request, f"Error updating product: {str(e)}")
            return redirect('admin_edit_product', product_id=product.id)

    # If it's a GET request, send the product and all options to the template
    context = {
        'product': product,
        'categories': Category.objects.all(),
        'volumes': Volume.objects.all(),
        'units': Unit.objects.all(),
    }
    return render(request, 'store/admin_edit_product.html', context)


@staff_member_required
def admin_edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        try:
            category.name_en = request.POST.get('name_en')
            category.name_ar = request.POST.get('name_ar')

            # Only update the image if a new one is uploaded
            image = request.FILES.get('image')
            if image:
                category.image = image

            category.save()
            messages.success(request, f"Collection '{category.name_en}' updated successfully!")
            return redirect('admin_categories')

        except Exception as e:
            messages.error(request, f"Error updating collection: {str(e)}")
            return redirect('admin_edit_category', category_id=category.id)

    context = {
        'category': category,
    }
    return render(request, 'store/admin_edit_category.html', context)


@staff_member_required
def admin_attributes(request):
    if request.method == 'POST':
        # Check which form was submitted (Volume or Unit)
        attr_type = request.POST.get('type')
        name_en = request.POST.get('name_en')
        name_ar = request.POST.get('name_ar')

        try:
            if attr_type == 'volume':
                Volume.objects.create(name_en=name_en, name_ar=name_ar)
                messages.success(request, f"Volume '{name_en}' added successfully!")
            elif attr_type == 'unit':
                Unit.objects.create(name_en=name_en, name_ar=name_ar)
                messages.success(request, f"Unit '{name_en}' added successfully!")

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

        return redirect('admin_attributes')

    context = {
        'volumes': Volume.objects.all().order_by('-id'),
        'units': Unit.objects.all().order_by('-id'),
    }
    return render(request, 'store/admin_attributes.html', context)


@staff_member_required
def admin_banners(request):
    if request.method == 'POST':
        # Get a list of ALL uploaded files using getlist() and the name 'images'
        images = request.FILES.getlist('images')

        for image in images:
            Banner.objects.create(
                small_text_en="-",
                small_text_ar="-",
                main_text_white_en="-",
                main_text_white_ar="-",
                main_text_gold_en="-",
                main_text_gold_ar="-",
                description_en="-",
                description_ar="-",
                button_text_en="-",
                button_text_ar="-",
                image=image
            )

        messages.success(request, f"Successfully published {len(images)} banner(s)!")
        return redirect('admin_banners')

    context = {'banners': Banner.objects.all().order_by('-id')}
    return render(request, 'store/admin_banners.html', context)

@staff_member_required
def delete_banner(request, banner_id):
    banner = get_object_or_404(Banner, id=banner_id)
    banner.delete()
    messages.success(request, "Banner removed successfully!")
    return redirect('admin_banners')