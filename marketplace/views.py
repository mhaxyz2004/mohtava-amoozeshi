from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, FileResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.utils.decorators import method_decorator
from .models import Category, Product, Review, Order, Support, UserProfile
from .forms import UserRegistrationForm, UserLoginForm, ReviewForm, SupportForm, UserProfileForm
from .zarinpal import initiate_zarinpal_payment, verify_zarinpal_payment
from datetime import datetime

class IndexView(View):
    def get(self, request):
        featured_products = Product.objects.filter(is_active=True, is_featured=True)[:6]
        categories = Category.objects.all()
        context = {
            'featured_products': featured_products,
            'categories': categories,
        }
        return render(request, 'index.html', context)

class ProductListView(View):
    def get(self, request):
        products = Product.objects.filter(is_active=True)
        categories = Category.objects.all()
        
        # جستجو
        search = request.GET.get('search', '')
        if search:
            products = products.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        
        # فیلتر دسته
        category = request.GET.get('category', '')
        if category:
            products = products.filter(category__slug=category)
        
        # فیلتر قیمت
        price_range = request.GET.get('price_range', '')
        if price_range == 'low':
            products = products.filter(price__lte=100000)
        elif price_range == 'medium':
            products = products.filter(price__gt=100000, price__lte=500000)
        elif price_range == 'high':
            products = products.filter(price__gt=500000)
        
        context = {
            'products': products,
            'categories': categories,
            'search': search,
        }
        return render(request, 'products/list.html', context)

class ProductDetailView(View):
    def get(self, request, slug):
        product = get_object_or_404(Product, slug=slug, is_active=True)
        product.views_count += 1
        product.save(update_fields=['views_count'])
        
        reviews = product.review_set.all()
        user_review = None
        if request.user.is_authenticated:
            user_review = reviews.filter(user=request.user).first()
        
        form = ReviewForm()
        
        context = {
            'product': product,
            'reviews': reviews,
            'user_review': user_review,
            'form': form,
            'average_rating': product.average_rating,
        }
        return render(request, 'products/detail.html', context)
    
    @method_decorator(login_required)
    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug, is_active=True)
        form = ReviewForm(request.POST)
        
        if form.is_valid():
            review, created = Review.objects.get_or_create(
                product=product,
                user=request.user,
                defaults={'rating': form.cleaned_data['rating'], 'comment': form.cleaned_data['comment']}
            )
            if not created:
                review.rating = form.cleaned_data['rating']
                review.comment = form.cleaned_data['comment']
                review.save()
            messages.success(request, 'نظر شما با موفقیت ثبت شد!')
        
        return redirect('product-detail', slug=slug)

class RegisterView(View):
    def get(self, request):
        form = UserRegistrationForm()
        return render(request, 'auth/register.html', {'form': form})
    
    def post(self, request):
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            login(request, user)
            messages.success(request, 'خوش آمدید!')
            return redirect('index')
        return render(request, 'auth/register.html', {'form': form})

class LoginView(View):
    def get(self, request):
        form = UserLoginForm()
        return render(request, 'auth/login.html', {'form': form})
    
    def post(self, request):
        form = UserLoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password']
            )
            if user:
                login(request, user)
                return redirect('index')
            messages.error(request, 'نام کاربری یا رمز عبور اشتباه است!')
        return render(request, 'auth/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'با موفقیت خارج شدید!')
    return redirect('index')

@login_required
def profile_view(request):
    profile = request.user.profile
    orders = Order.objects.filter(user=request.user).select_related('product')
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'پروفیل بروزرسانی شد!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)
    
    context = {
        'profile': profile,
        'form': form,
        'orders': orders,
    }
    return render(request, 'profile.html', context)

@login_required
def purchase_product(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    
    # ایجاد سفارش
    order = Order.objects.create(
        user=request.user,
        product=product,
        amount=product.final_price
    )
    
    # شروع پرداخت
    result = initiate_zarinpal_payment(
        order.id,
        product.final_price,
        f"خریدای {product.title}"
    )
    
    if result['success']:
        order.zarinpal_authority = result['authority']
        order.save()
        return redirect(result['url'])
    else:
        order.status = 'failed'
        order.save()
        messages.error(request, result['error'])
        return redirect('product-detail', slug=slug)

@login_required
def payment_verify(request):
    authority = request.GET.get('Authority')
    status = request.GET.get('Status')
    
    if not authority:
        messages.error(request, 'پرداخت لغو شد!')
        return redirect('index')
    
    order = get_object_or_404(Order, zarinpal_authority=authority)
    
    if status == 'OK':
        result = verify_zarinpal_payment(authority, order.amount)
        if result['success']:
            order.status = 'completed'
            order.zarinpal_ref_id = result['ref_id']
            order.completed_at = datetime.now()
            order.save()
            messages.success(request, 'پرداخت با موفقیت انجام شد!')
            return redirect('payment-success', order_id=order.id)
    
    order.status = 'failed'
    order.save()
    messages.error(request, 'پرداخت ناموفق بود!')
    return redirect('index')

@login_required
def payment_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user, status='completed')
    context = {'order': order}
    return render(request, 'payment/success.html', context)

@login_required
def download_product(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user, status='completed')
    product = order.product
    
    if product.file:
        return FileResponse(product.file.open('rb'), as_attachment=True)
    
    messages.error(request, 'فایل محصول موجود نیست!')
    return redirect('profile')

@login_required
def support_view(request):
    if request.method == 'POST':
        form = SupportForm(request.POST)
        if form.is_valid():
            support = form.save(commit=False)
            support.user = request.user
            support.save()
            messages.success(request, 'پیام شما با موفقیت ارسال شد!')
            return redirect('support')
    else:
        form = SupportForm()
    
    tickets = Support.objects.filter(user=request.user)
    context = {
        'form': form,
        'tickets': tickets,
    }
    return render(request, 'support.html', context)
