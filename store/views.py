from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
import pandas as pd
from .models import Category, Volume, Unit, Color, Product, Banner  # Added Color here
import os
import re
from django.db.models import Count
from django.core.serializers import serialize, deserialize
from itertools import chain


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
            missing_attributes_ids = []  # Tracks products that are missing sizes/units

            for index, row in df.iterrows():
                cat_name = str(row['Category (Exact English Name)']).strip()
                if cat_name == 'nan' or not cat_name:
                    continue

                category, created = Category.objects.get_or_create(
                    name_en__iexact=cat_name,
                    defaults={'name_en': cat_name, 'name_ar': cat_name}
                )

                is_new = str(row['Is New Arrival (Yes/No)']).strip().lower() == 'yes'

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

                volumes_str = str(row['Volumes (Comma separated, e.g., 500ml, 1L)'])
                units_str = str(row['Units (Comma separated, e.g., PCS, Dozen)'])

                if 'Colors (Comma separated, e.g., Blue, White)' in row:
                    colors_str = str(row['Colors (Comma separated, e.g., Blue, White)'])
                    if colors_str != 'nan' and colors_str.strip():
                        color_list = [c.strip() for c in colors_str.split(',') if c.strip()]
                        for c_name in color_list:
                            color_obj, created = Color.objects.get_or_create(
                                name_en__iexact=c_name,
                                defaults={'name_en': c_name, 'name_ar': c_name}
                            )
                            product.available_colors.add(color_obj)

                has_vol = volumes_str != 'nan' and volumes_str.strip()
                has_unit = units_str != 'nan' and units_str.strip()

                if has_vol:
                    vol_list = [v.strip() for v in volumes_str.split(',') if v.strip()]
                    for v_name in vol_list:
                        vol_obj, created = Volume.objects.get_or_create(name_en__iexact=v_name,
                                                                        defaults={'name_en': v_name, 'name_ar': v_name})
                        product.available_volumes.add(vol_obj)

                if has_unit:
                    unit_list = [u.strip() for u in units_str.split(',') if u.strip()]
                    for u_name in unit_list:
                        unit_obj, created = Unit.objects.get_or_create(name_en__iexact=u_name,
                                                                       defaults={'name_en': u_name, 'name_ar': u_name})
                        product.available_units.add(unit_obj)

                products_created += 1

                # If either volume or unit is missing, send to the review queue
                if not has_vol or not has_unit:
                    missing_attributes_ids.append(product.id)

            # If there are missing fields, store IDs in session and redirect to Review Page
            if missing_attributes_ids:
                request.session['missing_attr_ids'] = missing_attributes_ids
                messages.warning(request,
                                 f"Imported {products_created} items, but some fields were empty. Please review them.")
                return redirect('admin_excel_review')

            messages.success(request, f"Successfully imported {products_created} products!")
            return redirect('custom_admin_dashboard')

        except Exception as e:
            messages.error(request, f"Error processing file: {str(e)}")
            return redirect('admin_excel_upload')

    return render(request, 'store/admin_excel_upload.html')


@staff_member_required
def admin_excel_review(request):
    missing_ids = request.session.get('missing_attr_ids', [])
    if not missing_ids:
        messages.info(request, "No items need review.")
        return redirect('custom_admin_dashboard')

    products = Product.objects.filter(id__in=missing_ids)

    if request.method == 'POST':
        for product in products:
            vol_input = request.POST.get(f'vol_{product.id}')
            unit_input = request.POST.get(f'unit_{product.id}')

            # If the user typed a volume, auto-create and add it
            if vol_input and vol_input.strip():
                v_list = [v.strip() for v in vol_input.split(',') if v.strip()]
                for v_name in v_list:
                    vol_obj, _ = Volume.objects.get_or_create(name_en__iexact=v_name,
                                                              defaults={'name_en': v_name, 'name_ar': v_name})
                    product.available_volumes.add(vol_obj)

            # If the user typed a unit, auto-create and add it
            if unit_input and unit_input.strip():
                u_list = [u.strip() for u in unit_input.split(',') if u.strip()]
                for u_name in u_list:
                    unit_obj, _ = Unit.objects.get_or_create(name_en__iexact=u_name,
                                                             defaults={'name_en': u_name, 'name_ar': u_name})
                    product.available_units.add(unit_obj)

        # Clear the queue when done
        if 'missing_attr_ids' in request.session:
            del request.session['missing_attr_ids']

        messages.success(request, "Empty fields handled successfully!")
        return redirect('custom_admin_dashboard')

    return render(request, 'store/admin_excel_review.html', {'products': products})


@staff_member_required
def admin_bulk_image_upload(request):
    if request.method == 'POST':
        images = request.FILES.getlist('images')
        if not images:
            messages.error(request, "Please select at least one image.")
            return redirect('admin_bulk_image_upload')

        match_count = 0
        miss_count = 0

        # --- THE SMART MATCHER LOGIC ---
        def clean_name(name):
            return re.sub(r'[^a-zA-Z0-9]', '', str(name)).lower()

        all_products = Product.objects.all()
        product_dict = {clean_name(p.name_en): p for p in all_products}

        for image in images:
            filename_without_ext = os.path.splitext(image.name)[0]
            cleaned_filename = clean_name(filename_without_ext)

            if cleaned_filename in product_dict:
                product = product_dict[cleaned_filename]
                product.image_1 = image
                product.save()
                match_count += 1
            else:
                miss_count += 1

        messages.success(request,
                         f"Bulk upload complete! Automatically matched {match_count} images to products. ({miss_count} images did not match a product name).")
        return redirect('admin_inventory')

    return render(request, 'store/admin_bulk_image_upload.html')


@staff_member_required
def download_excel_template(request):
    # Added the Colors column to the exact template format
    columns = [
        'Category (Exact English Name)',
        'Name (English)',
        'Name (Arabic)',
        'Is New Arrival (Yes/No)',
        'Volumes (Comma separated, e.g., 500ml, 1L)',
        'Units (Comma separated, e.g., PCS, Dozen)',
        'Colors (Comma separated, e.g., Blue, White)'
    ]
    df = pd.DataFrame(columns=columns)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="GrowGreen_Product_Template.xlsx"'
    df.to_excel(response, index=False)
    return response


@staff_member_required
def admin_add_product(request):
    if request.method == 'POST':
        name_en = request.POST.get('name_en')
        name_ar = request.POST.get('name_ar')
        category_id = request.POST.get('category')
        is_new_arrival = 'is_new_arrival' in request.POST
        image_1 = request.FILES.get('image_1')

        try:
            category = Category.objects.get(id=category_id)
            product = Product.objects.create(
                name_en=name_en,
                name_ar=name_ar,
                category=category,
                is_new_arrival=is_new_arrival,
            )

            if image_1:
                product.image_1 = image_1
                product.save()

            volume_ids = request.POST.getlist('volumes')
            if volume_ids:
                volumes = Volume.objects.filter(id__in=volume_ids)
                product.available_volumes.set(volumes)

            unit_ids = request.POST.getlist('units')
            if unit_ids:
                units = Unit.objects.filter(id__in=unit_ids)
                product.available_units.set(units)

            # Added Color saving logic
            color_ids = request.POST.getlist('colors')
            if color_ids:
                colors = Color.objects.filter(id__in=color_ids)
                product.available_colors.set(colors)

            messages.success(request, f"Product '{name_en}' added successfully!")
            return redirect('custom_admin_dashboard')

        except Exception as e:
            messages.error(request, f"Error adding product: {str(e)}")
            return redirect('admin_add_product')

    context = {
        'categories': Category.objects.all(),
        'volumes': Volume.objects.all(),
        'units': Unit.objects.all(),
        'colors': Color.objects.all(),  # Added Color context
    }
    return render(request, 'store/admin_add_product.html', context)


@staff_member_required
def admin_inventory(request):
    products = Product.objects.all().order_by('-id')
    context = {'products': products}
    return render(request, 'store/admin_inventory.html', context)


@staff_member_required
def admin_categories(request):
    if request.method == 'POST':
        name_en = request.POST.get('name_en')
        name_ar = request.POST.get('name_ar')
        image = request.FILES.get('image')

        try:
            category = Category.objects.create(name_en=name_en, name_ar=name_ar)
            if image:
                category.image = image
                category.save()

            messages.success(request, f"Collection '{name_en}' added successfully!")
            return redirect('admin_categories')

        except Exception as e:
            messages.error(request, f"Error adding collection: {str(e)}")
            return redirect('admin_categories')

    categories = Category.objects.all().order_by('-id')
    context = {'categories': categories}
    return render(request, 'store/admin_categories.html', context)


@staff_member_required
def admin_edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        try:
            product.name_en = request.POST.get('name_en')
            product.name_ar = request.POST.get('name_ar')
            product.category_id = request.POST.get('category')
            product.is_new_arrival = 'is_new_arrival' in request.POST

            image_1 = request.FILES.get('image_1')
            if image_1:
                product.image_1 = image_1

            product.save()

            volume_ids = request.POST.getlist('volumes')
            product.available_volumes.set(Volume.objects.filter(id__in=volume_ids))

            unit_ids = request.POST.getlist('units')
            product.available_units.set(Unit.objects.filter(id__in=unit_ids))

            # Added Color saving logic
            color_ids = request.POST.getlist('colors')
            product.available_colors.set(Color.objects.filter(id__in=color_ids))

            messages.success(request, f"Product '{product.name_en}' updated successfully!")
            return redirect('admin_inventory')

        except Exception as e:
            messages.error(request, f"Error updating product: {str(e)}")
            return redirect('admin_edit_product', product_id=product.id)

    context = {
        'product': product,
        'categories': Category.objects.all(),
        'volumes': Volume.objects.all(),
        'units': Unit.objects.all(),
        'colors': Color.objects.all(),  # Added Color context
    }
    return render(request, 'store/admin_edit_product.html', context)


@staff_member_required
def admin_edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        try:
            category.name_en = request.POST.get('name_en')
            category.name_ar = request.POST.get('name_ar')

            image = request.FILES.get('image')
            if image:
                category.image = image

            category.save()
            messages.success(request, f"Collection '{category.name_en}' updated successfully!")
            return redirect('admin_categories')

        except Exception as e:
            messages.error(request, f"Error updating collection: {str(e)}")
            return redirect('admin_edit_category', category_id=category.id)

    context = {'category': category}
    return render(request, 'store/admin_edit_category.html', context)


@staff_member_required
def admin_attributes(request):
    if request.method == 'POST':
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
            # Added Color creation logic
            elif attr_type == 'color':
                Color.objects.create(name_en=name_en, name_ar=name_ar)
                messages.success(request, f"Variant/Color '{name_en}' added successfully!")

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

        return redirect('admin_attributes')

    context = {
        'volumes': Volume.objects.all().order_by('-id'),
        'units': Unit.objects.all().order_by('-id'),
        'colors': Color.objects.all().order_by('-id'),  # Added Color context
    }
    return render(request, 'store/admin_attributes.html', context)


@staff_member_required
def admin_banners(request):
    if request.method == 'POST':
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


@staff_member_required
def admin_find_duplicates(request):
    """Scans the database for products with the exact same English name"""
    # Find names that appear more than once (case-insensitive)
    duplicate_names = Product.objects.values('name_en').annotate(name_count=Count('name_en')).filter(name_count__gt=1)

    duplicates_list = []
    for item in duplicate_names:
        # Get all products that share this name
        prods = Product.objects.filter(name_en__iexact=item['name_en']).prefetch_related('available_volumes',
                                                                                         'available_units',
                                                                                         'available_colors')
        duplicates_list.append({
            'name': item['name_en'],
            'products': prods
        })

    context = {'duplicates_list': duplicates_list}
    return render(request, 'store/admin_duplicates.html', context)


@staff_member_required
def admin_merge_duplicates(request):
    """Merges all selected duplicates into a single master product"""
    if request.method == 'POST':
        master_id = request.POST.get('master_id')
        duplicate_ids = request.POST.getlist('duplicate_ids')  # All the IDs to merge and delete

        try:
            master_product = get_object_or_404(Product, id=master_id)

            for dup_id in duplicate_ids:
                if dup_id == master_id:
                    continue  # Don't delete the master by accident!

                dup_product = Product.objects.get(id=dup_id)

                # Move all Volumes, Units, and Colors to the Master Product
                for vol in dup_product.available_volumes.all(): master_product.available_volumes.add(vol)
                for unit in dup_product.available_units.all(): master_product.available_units.add(unit)
                for color in dup_product.available_colors.all(): master_product.available_colors.add(color)

                # Delete the extra duplicate product
                dup_product.delete()

            messages.success(request,
                             f"Successfully merged items into '{master_product.name_en}' and removed the duplicates!")
        except Exception as e:
            messages.error(request, f"Error merging products: {str(e)}")

    return redirect('admin_find_duplicates')


@staff_member_required
def admin_offer_generator(request):
    # We pass all products to the frontend so JavaScript can search them instantly
    # We use prefetch_related to get the volumes, units, and colors easily
    products = Product.objects.all().prefetch_related('available_volumes', 'available_units', 'available_colors')

    # We convert the products into a list of dictionaries so Javascript can read it easily
    product_list = []
    for p in products:
        product_list.append({
            'id': p.id,
            'name_en': p.name_en,
            'name_ar': p.name_ar,
            'image_url': p.image_1.url if p.image_1 else '',
            'volumes': [v.name_en for v in p.available_volumes.all()],
            'units': [u.name_en for u in p.available_units.all()],
            'colors': [c.name_en for c in p.available_colors.all()]
        })

    context = {
        'products_json': product_list,
    }
    return render(request, 'store/admin_offer_generator.html', context)


@staff_member_required
def admin_quick_rename(request):
    """Allows admin to instantly rename a product so it is no longer a duplicate"""
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        new_name_en = request.POST.get('new_name_en')
        new_name_ar = request.POST.get('new_name_ar')

        try:
            # Find the product and update its names
            product = get_object_or_404(Product, id=product_id)
            product.name_en = new_name_en
            product.name_ar = new_name_ar
            product.save()

            messages.success(request,
                             f"Successfully renamed to '{new_name_en}'. It has been separated from the duplicates!")
        except Exception as e:
            messages.error(request, f"Error renaming product: {str(e)}")

    return redirect('admin_find_duplicates')


@staff_member_required
def admin_bulk_merge_all(request):
    """Automatically merges all duplicate groups in the database with one click. Keeps the oldest product as Master."""
    if request.method == 'POST':
        duplicate_names = Product.objects.values('name_en').annotate(name_count=Count('name_en')).filter(
            name_count__gt=1)

        merged_groups = 0
        items_deleted = 0

        for item in duplicate_names:
            # Get all products with this name, ordered by ID (oldest first)
            prods = list(Product.objects.filter(name_en__iexact=item['name_en']).order_by('id'))
            if len(prods) > 1:
                master = prods[0]  # Oldest is Master
                duplicates = prods[1:]  # The rest are duplicates

                for dup in duplicates:
                    for vol in dup.available_volumes.all(): master.available_volumes.add(vol)
                    for unit in dup.available_units.all(): master.available_units.add(unit)
                    for color in dup.available_colors.all(): master.available_colors.add(color)
                    dup.delete()
                    items_deleted += 1

                merged_groups += 1

        messages.success(request,
                         f"⚡ Bulk Auto-Merge complete! Resolved {merged_groups} groups and removed {items_deleted} duplicate items.")
    return redirect('admin_find_duplicates')


@staff_member_required
def admin_factory_reset(request):
    """
    DANGER ZONE: Wipes all store data for a fresh start,
    but safely keeps the Admin user accounts active.
    """
    if request.method == 'POST':
        try:
            # Delete all products first (to prevent relationship errors)
            Product.objects.all().delete()

            # Delete all categories and attributes
            Category.objects.all().delete()
            Volume.objects.all().delete()
            Unit.objects.all().delete()
            Color.objects.all().delete()

            # Delete any uploaded banners
            Banner.objects.all().delete()

            messages.success(request,
                             "♻️ SYSTEM RESET COMPLETE: All products, categories, and attributes have been wiped. You have a fresh database!")
        except Exception as e:
            messages.error(request, f"Error wiping database: {str(e)}")

    return redirect('custom_admin_dashboard')


@staff_member_required
def admin_system_settings(request):
    """Loads the dedicated System & Database Management page."""
    return render(request, 'store/admin_system_settings.html')


@staff_member_required
def admin_database_backup(request):
    """Exports all store data into a downloadable JSON file."""
    # Gather all database objects
    objects = list(chain(
        Category.objects.all(),
        Volume.objects.all(),
        Unit.objects.all(),
        Color.objects.all(),
        Product.objects.all()
    ))
    # Convert to JSON
    data = serialize('json', objects)

    # Send as a downloadable file
    response = HttpResponse(data, content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="GrowGreen_DB_Backup.json"'
    return response


@staff_member_required
def admin_database_restore(request):
    """Wipes current data and restores from a JSON backup file."""
    if request.method == 'POST' and request.FILES.get('backup_file'):
        backup_file = request.FILES['backup_file']
        try:
            # 1. Clear existing data to avoid conflicts
            Product.objects.all().delete()
            Category.objects.all().delete()
            Volume.objects.all().delete()
            Unit.objects.all().delete()
            Color.objects.all().delete()

            # 2. Read the uploaded file and restore the data
            for obj in deserialize('json', backup_file.read()):
                obj.save()

            messages.success(request, "Database restored successfully from backup!")
        except Exception as e:
            messages.error(request, f"Restore failed. Ensure the file is a valid Grow Green backup. Error: {str(e)}")

    return redirect('admin_system_settings')


@staff_member_required
def admin_factory_reset(request):
    """Wipes all store data for a fresh start."""
    if request.method == 'POST':
        try:
            Product.objects.all().delete()
            Category.objects.all().delete()
            Volume.objects.all().delete()
            Unit.objects.all().delete()
            Color.objects.all().delete()
            Banner.objects.all().delete()
            messages.success(request,
                             "♻️ SYSTEM RESET COMPLETE: All store records have been wiped. You have a fresh database!")
        except Exception as e:
            messages.error(request, f"Error wiping database: {str(e)}")

    return redirect('admin_system_settings')