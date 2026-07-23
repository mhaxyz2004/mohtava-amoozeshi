from django.urls import path
from . import views

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('products/<slug:slug>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('purchase/<slug:slug>/', views.purchase_product, name='purchase'),
    path('payment/verify/', views.payment_verify, name='payment-verify'),
    path('payment/success/<int:order_id>/', views.payment_success, name='payment-success'),
    path('download/<int:order_id>/', views.download_product, name='download'),
    path('support/', views.support_view, name='support'),
]
