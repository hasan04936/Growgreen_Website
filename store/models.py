from django.db import models


class Category(models.Model):
    name_en = models.CharField(max_length=100, verbose_name="Name (English)")
    name_ar = models.CharField(max_length=100, verbose_name="Name (Arabic)")
    image = models.ImageField(upload_to='categories/')

    # This solves your dynamic fields! The admin can type a list of expected fields here.
    # Example: ["Material", "Voltage", "Warranty"]
    custom_fields_template = models.JSONField(default=list, blank=True, null=True, help_text='Enter a list of field names. e.g., ["Color", "Size"]')

    def __str__(self):
        return self.name_en


class Volume(models.Model):
    name_en = models.CharField(max_length=50, help_text="e.g., Milliliter, Liter, Kg")
    name_ar = models.CharField(max_length=50)

    def __str__(self):
        return self.name_en


class Unit(models.Model):
    name_en = models.CharField(max_length=50, help_text="e.g., DOZEN, PCS, CARTON")
    name_ar = models.CharField(max_length=50)

    def __str__(self):
        return self.name_en


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name_en = models.CharField(max_length=200, verbose_name="Product Name (English)")
    name_ar = models.CharField(max_length=200, verbose_name="Product Name (Arabic)")

    # You requested at least 2 images
    image_1 = models.ImageField(upload_to='products/')
    image_2 = models.ImageField(upload_to='products/', blank=True, null=True)

    # Toggle for the "New Arrival" banner
    is_new_arrival = models.BooleanField(default=False)

    # This stores the actual values for the dynamic fields based on the Category
    # Example: {"Material": "Plastic", "Voltage": "220V"}
    dynamic_attributes = models.JSONField(default=dict, blank=True, null=True)

    # This handles your Olive Oil example!
    # The admin can select ONLY the specific volumes and units this product comes in.
    available_volumes = models.ManyToManyField(Volume, blank=True)
    available_units = models.ManyToManyField(Unit, blank=True)

    def __str__(self):
        return self.name_en


class Banner(models.Model):
    small_text_en = models.CharField(max_length=100, help_text="e.g. Grow Green Trading Co.")
    small_text_ar = models.CharField(max_length=100, help_text="e.g. شركة جرو جرين")
    main_text_white_en = models.CharField(max_length=100, help_text="e.g. Luxury")
    main_text_white_ar = models.CharField(max_length=100, help_text="e.g. تصميم")
    main_text_gold_en = models.CharField(max_length=100, help_text="e.g. Design")
    main_text_gold_ar = models.CharField(max_length=100, help_text="e.g. فاخر")
    description_en = models.TextField()
    description_ar = models.TextField()
    button_text_en = models.CharField(max_length=50, default="Shop Now")
    button_text_ar = models.CharField(max_length=50, default="تسوق الآن")
    image = models.ImageField(upload_to='banners/', null=True, blank=True)

    def __str__(self):
        return f"{self.main_text_white_en} {self.main_text_gold_en}"