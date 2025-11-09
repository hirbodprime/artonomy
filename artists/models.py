# artists/models.py
from django.db import models
from django.utils.text import slugify

def upload_to_category(instance, filename):
    return f"artists/categories/{instance.pk or 'new'}/{filename}"

def upload_to_subcategory(instance, filename):
    return f"artists/subcategories/{instance.pk or 'new'}/{filename}"

class Category(models.Model):
    name  = models.CharField(max_length=100, unique=True)
    slug  = models.SlugField(max_length=120, unique=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to=upload_to_category, null=True, blank=True)  # ✅ جدید

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Subcategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories")
    name     = models.CharField(max_length=120)
    slug     = models.SlugField(max_length=140, blank=True)
    order    = models.PositiveIntegerField(default=0)
    image    = models.ImageField(upload_to=upload_to_subcategory, null=True, blank=True)  # ✅ جدید

    class Meta:
        ordering = ["category__order", "order", "name"]
        unique_together = [("category", "name")]
        verbose_name = "Subcategory"
        verbose_name_plural = "Subcategories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.name} → {self.name}"
