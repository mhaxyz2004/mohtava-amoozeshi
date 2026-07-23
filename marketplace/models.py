from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name=_('نام دسته'))
    slug = models.SlugField(unique=True, verbose_name=_('نام انگلیسی'))
    description = models.TextField(blank=True, verbose_name=_('توضیح'))
    icon = models.CharField(max_length=50, default='book', verbose_name=_('آیکن'))
    
    class Meta:
        verbose_name_plural = _('دسته‌بندی‌ها')
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Product(models.Model):
    PRODUCT_TYPES = [
        ('pdf', 'PDF'),
        ('game', 'بازی'),
        ('electronic', 'محصول الکترونیکی'),
        ('video', 'ویدیو'),
        ('other', 'سایر'),
    ]
    
    title = models.CharField(max_length=200, verbose_name=_('عنوان'))
    slug = models.SlugField(unique=True, verbose_name=_('نام انگلیسی'))
    description = models.TextField(verbose_name=_('توضیح'))
    price = models.DecimalField(max_digits=10, decimal_places=0, verbose_name=_('قیمت'))
    discount_price = models.DecimalField(
        max_digits=10, decimal_places=0, null=True, blank=True, 
        verbose_name=_('قیمت تخفیف‌خورده')
    )
    
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name=_('دسته'))
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, verbose_name=_('نوع محصول'))
    
    image = models.ImageField(upload_to='products/', verbose_name=_('تصویر'))
    file = models.FileField(upload_to='products/files/', null=True, blank=True, verbose_name=_('فایل'))
    
    author = models.CharField(max_length=100, verbose_name=_('نویسنده/سازنده'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاریخ ایجاد'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('تاریخ بروزرسانی'))
    
    is_active = models.BooleanField(default=True, verbose_name=_('فعال'))
    is_featured = models.BooleanField(default=False, verbose_name=_('محصول برتر'))
    
    views_count = models.IntegerField(default=0, verbose_name=_('تعداد بازدید'))
    
    class Meta:
        verbose_name_plural = _('محصولات')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def average_rating(self):
        reviews = self.review_set.all()
        if reviews.exists():
            return sum([r.rating for r in reviews]) / len(reviews)
        return 0
    
    @property
    def final_price(self):
        return self.discount_price if self.discount_price else self.price

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name=_('محصول'))
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('کاربر'))
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_('امتیاز')
    )
    comment = models.TextField(verbose_name=_('نظر'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاریخ'))
    is_verified = models.BooleanField(default=False, verbose_name=_('خریدار تأیید‌شده'))
    
    class Meta:
        verbose_name_plural = _('نظرات')
        ordering = ['-created_at']
        unique_together = ('product', 'user')
    
    def __str__(self):
        return f'{self.user.username} - {self.product.title}'

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'در انتظار پرداخت'),
        ('completed', 'تکمیل‌شده'),
        ('failed', 'ناموفق'),
        ('refunded', 'بازگردانده‌شده'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('کاربر'))
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name=_('محصول'))
    amount = models.DecimalField(max_digits=10, decimal_places=0, verbose_name=_('مبلغ'))
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name=_('وضعیت'))
    
    zarinpal_ref_id = models.CharField(max_length=100, null=True, blank=True, verbose_name=_('شناسه زرین‌پال'))
    zarinpal_authority = models.CharField(max_length=100, null=True, blank=True, verbose_name=_('Authority'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاریخ سفارش'))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('تاریخ تکمیل'))
    
    class Meta:
        verbose_name_plural = _('سفارش‌ها')
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.username} - {self.product.title}'

class Support(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'کم'),
        ('medium', 'متوسط'),
        ('high', 'زیاد'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'باز'),
        ('in_progress', 'در حال بررسی'),
        ('closed', 'بسته‌شده'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('کاربر'))
    subject = models.CharField(max_length=200, verbose_name=_('موضوع'))
    message = models.TextField(verbose_name=_('پیام'))
    
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium', verbose_name=_('اولویت'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', verbose_name=_('وضعیت'))
    
    response = models.TextField(null=True, blank=True, verbose_name=_('پاسخ'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاریخ ارسال'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('تاریخ بروزرسانی'))
    
    class Meta:
        verbose_name_plural = _('تیکت‌های پشتیبانی')
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.username} - {self.subject}'

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name=_('کاربر'))
    bio = models.TextField(blank=True, verbose_name=_('درباره'))
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name=_('تصویر پروفیل'))
    phone = models.CharField(max_length=20, blank=True, verbose_name=_('تلفن'))
    city = models.CharField(max_length=100, blank=True, verbose_name=_('شهر'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاریخ ایجاد'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('تاریخ بروزرسانی'))
    
    class Meta:
        verbose_name_plural = _('پروفیل‌های کاربری')
    
    def __str__(self):
        return f'Profile: {self.user.username}'
