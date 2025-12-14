import django_filters
from .models import Customer, Product, Order, OrderItem
import re

class CustomerFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    email = django_filters.CharFilter(lookup_expr='icontains')
    created_at_gte = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_at_lte = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    phone_pattern = django_filters.CharFilter(method='filter_phone_pattern')
    
    class Meta:
        model = Customer
        fields = ['name', 'email', 'phone']
    
    def filter_phone_pattern(self, queryset, name, value):
        """Custom filter for phone number patterns"""
        if value == '+1':
            
            return queryset.filter(phone__startswith='+1')
        elif value == 'us':
            
            return queryset.filter(phone__regex=r'^(\+1|1-)')
        elif value == 'international':
            
            return queryset.filter(phone__startswith='+')
        return queryset

class ProductFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    price_gte = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_lte = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    stock_gte = django_filters.NumberFilter(field_name='stock', lookup_expr='gte')
    stock_lte = django_filters.NumberFilter(field_name='stock', lookup_expr='lte')
    low_stock = django_filters.BooleanFilter(method='filter_low_stock')
    
    class Meta:
        model = Product
        fields = ['name', 'price', 'stock']
    
    def filter_low_stock(self, queryset, name, value):
        """Filter products with low stock (stock < 10)"""
        if value:
            return queryset.filter(stock__lt=10)
        return queryset

class OrderFilter(django_filters.FilterSet):
    total_amount_gte = django_filters.NumberFilter(field_name='total_amount', lookup_expr='gte')
    total_amount_lte = django_filters.NumberFilter(field_name='total_amount', lookup_expr='lte')
    order_date_gte = django_filters.DateFilter(field_name='order_date', lookup_expr='gte')
    order_date_lte = django_filters.DateFilter(field_name='order_date', lookup_expr='lte')
    customer_name = django_filters.CharFilter(field_name='customer__name', lookup_expr='icontains')
    product_name = django_filters.CharFilter(field_name='products__name', lookup_expr='icontains')
    product_id = django_filters.UUIDFilter(field_name='products__id')
    
    class Meta:
        model = Order
        fields = ['total_amount', 'order_date', 'status']

class OrderItemFilter(django_filters.FilterSet):
    product_name = django_filters.CharFilter(field_name='product__name', lookup_expr='icontains')
    order_status = django_filters.CharFilter(field_name='order__status', lookup_expr='exact')
    
    class Meta:
        model = OrderItem
        fields = ['quantity']
