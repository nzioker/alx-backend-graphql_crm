import graphene
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphene import relay
import re
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from .models import Customer, Product, Order, OrderItem
from .filters import CustomerFilter, ProductFilter, OrderFilter
from crm.models import Product

# ==================== TYPES WITH FILTERING ====================

class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        interfaces = (relay.Node,)
        filterset_class = CustomerFilter

class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        interfaces = (relay.Node,)
        filterset_class = ProductFilter

class OrderItemType(DjangoObjectType):
    class Meta:
        model = OrderItem
        interfaces = (relay.Node,)

class OrderType(DjangoObjectType):
    items = graphene.List(OrderItemType)
    
    class Meta:
        model = Order
        interfaces = (relay.Node,)
        filterset_class = OrderFilter
    
    def resolve_items(self, info):
        return self.items.all()

# ==================== FILTER INPUT TYPES ====================

class CustomerFilterInput(graphene.InputObjectType):
    name = graphene.String()
    name_icontains = graphene.String()
    email = graphene.String()
    email_icontains = graphene.String()
    phone = graphene.String()
    phone_icontains = graphene.String()
    created_at_gte = graphene.Date()
    created_at_lte = graphene.Date()
    phone_pattern = graphene.String()

class ProductFilterInput(graphene.InputObjectType):
    name = graphene.String()
    name_icontains = graphene.String()
    price_gte = graphene.Float()
    price_lte = graphene.Float()
    stock_gte = graphene.Int()
    stock_lte = graphene.Int()
    low_stock = graphene.Boolean()

class OrderFilterInput(graphene.InputObjectType):
    total_amount_gte = graphene.Float()
    total_amount_lte = graphene.Float()
    order_date_gte = graphene.Date()
    order_date_lte = graphene.Date()
    customer_name = graphene.String()
    product_name = graphene.String()
    product_id = graphene.ID()
    status = graphene.String()

# ==================== MUTATIONS (same as before) ====================

class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)
    
    customer = graphene.Field(CustomerType)
    message = graphene.String()
    
    @classmethod
    def mutate(cls, root, info, input):
        try:
            # Validate inputs
            if not input.name or not input.email:
                raise ValidationError("Name and email are required")
            
            validate_email(input.email)
            
            if Customer.objects.filter(email=input.email).exists():
                raise ValidationError(f"Email '{input.email}' already exists")
            
            if input.phone:
                pattern = r'^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$'
                if not re.match(pattern, input.phone):
                    raise ValidationError("Phone number must be in format: +1234567890 or 123-456-7890")
            
            customer = Customer(
                name=input.name,
                email=input.email,
                phone=input.phone
            )
            customer.full_clean()
            customer.save()
            
            return CreateCustomer(
                customer=customer,
                message="Customer created successfully"
            )
            
        except ValidationError as e:
            raise Exception(f"Validation error: {', '.join(e.messages)}")
        except Exception as e:
            raise Exception(f"Error creating customer: {str(e)}")

class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = BulkCustomerInput(required=True)
    
    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)
    
    @classmethod
    def mutate(cls, root, info, input):
        customers = []
        errors = []
        
        with transaction.atomic():
            for idx, customer_data in enumerate(input.customers):
                try:
                    if not customer_data.name or not customer_data.email:
                        errors.append(f"Customer {idx+1}: Name and email are required")
                        continue
                    
                    try:
                        validate_email(customer_data.email)
                    except ValidationError:
                        errors.append(f"Customer {idx+1}: Invalid email format")
                        continue
                    
                    existing_emails = [c.email for c in customers]
                    if customer_data.email in existing_emails:
                        errors.append(f"Customer {idx+1}: Email already in batch")
                        continue
                    
                    if Customer.objects.filter(email=customer_data.email).exists():
                        errors.append(f"Customer {idx+1}: Email already exists in database")
                        continue
                    
                    if customer_data.phone:
                        pattern = r'^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$'
                        if not re.match(pattern, customer_data.phone):
                            errors.append(f"Customer {idx+1}: Phone number must be in format: +1234567890 or 123-456-7890")
                            continue
                    
                    customer = Customer(
                        name=customer_data.name,
                        email=customer_data.email,
                        phone=customer_data.phone
                    )
                    customer.full_clean()
                    customer.save()
                    customers.append(customer)
                    
                except ValidationError as e:
                    errors.append(f"Customer {idx+1}: {', '.join(e.messages)}")
                except Exception as e:
                    errors.append(f"Customer {idx+1}: {str(e)}")
        
        return BulkCreateCustomers(customers=customers, errors=errors)

class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)
    
    product = graphene.Field(ProductType)
    
    @classmethod
    def mutate(cls, root, info, input):
        try:
            if Decimal(str(input.price)) <= 0:
                raise ValidationError("Price must be positive")
            
            if input.stock is not None and input.stock < 0:
                raise ValidationError("Stock cannot be negative")
            
            product = Product(
                name=input.name,
                description=input.description or "",
                price=input.price,
                stock=input.stock or 0
            )
            product.full_clean()
            product.save()
            
            return CreateProduct(product=product)
            
        except ValidationError as e:
            raise Exception(f"Validation error: {', '.join(e.messages)}")
        except Exception as e:
            raise Exception(f"Error creating product: {str(e)}")

class CreateOrder(graphene.Mutation):
    class Arguments:
        input = OrderInput(required=True)
    
    order = graphene.Field(OrderType)
    
    @classmethod
    def mutate(cls, root, info, input):
        try:
            if not input.product_ids:
                raise ValidationError("At least one product is required")
            
            try:
                customer = Customer.objects.get(id=input.customer_id)
            except Customer.DoesNotExist:
                raise ValidationError(f"Customer with ID {input.customer_id} not found")
            
            products = []
            for product_id in input.product_ids:
                try:
                    product = Product.objects.get(id=product_id)
                    if product.stock <= 0:
                        raise ValidationError(f"Product '{product.name}' is out of stock")
                    products.append(product)
                except Product.DoesNotExist:
                    raise ValidationError(f"Product with ID {product_id} not found")
            
            total_amount = Decimal('0.00')
            for product in products:
                total_amount += product.price
            
            with transaction.atomic():
                order = Order.objects.create(
                    customer=customer,
                    total_amount=total_amount,
                    order_date=input.order_date if input.order_date else None
                )
                
                for product in products:
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=1,
                        price_at_purchase=product.price
                    )
                    
                    product.stock -= 1
                    product.save()
            
            order.refresh_from_db()
            
            return CreateOrder(order=order)
            
        except ValidationError as e:
            raise Exception(f"Validation error: {', '.join(e.messages)}")
        except Exception as e:
            raise Exception(f"Error creating order: {str(e)}")

# ==================== QUERY CLASS WITH FILTERING AND ORDERING ====================

class Query(graphene.ObjectType):
    hello = graphene.String()
    
    # Customer queries with filtering and ordering
    customer = relay.Node.Field(CustomerType)
    all_customers = DjangoFilterConnectionField(
        CustomerType,
        filter=CustomerFilterInput(),
        order_by=graphene.String()
    )
    
    # Product queries with filtering and ordering
    product = relay.Node.Field(ProductType)
    all_products = DjangoFilterConnectionField(
        ProductType,
        filter=ProductFilterInput(),
        order_by=graphene.String()
    )
    
    # Order queries with filtering and ordering
    order = relay.Node.Field(OrderType)
    all_orders = DjangoFilterConnectionField(
        OrderType,
        filter=OrderFilterInput(),
        order_by=graphene.String()
    )
    
    # Custom filtered queries
    customers_by_name = graphene.List(
        CustomerType,
        name=graphene.String(),
        email=graphene.String()
    )
    
    products_by_price_range = graphene.List(
        ProductType,
        min_price=graphene.Float(),
        max_price=graphene.Float()
    )
    
    orders_by_customer = graphene.List(
        OrderType,
        customer_name=graphene.String(),
        customer_email=graphene.String()
    )
    
    def resolve_hello(self, info):
        return "Hello, GraphQL!"
    
    def resolve_all_customers(self, info, filter=None, order_by=None, **kwargs):
        qs = Customer.objects.all()
        
        # Apply custom filtering
        if filter:
            if filter.get('name_icontains'):
                qs = qs.filter(name__icontains=filter['name_icontains'])
            if filter.get('email_icontains'):
                qs = qs.filter(email__icontains=filter['email_icontains'])
            if filter.get('phone_pattern'):
                if filter['phone_pattern'] == '+1':
                    qs = qs.filter(phone__startswith='+1')
                elif filter['phone_pattern'] == 'us':
                    qs = qs.filter(Q(phone__startswith='+1') | Q(phone__startswith='1-'))
        
        # Apply ordering
        if order_by:
            if order_by.startswith('-'):
                qs = qs.order_by(order_by)
            else:
                qs = qs.order_by(order_by)
        
        return qs
    
    def resolve_all_products(self, info, filter=None, order_by=None, **kwargs):
        qs = Product.objects.all()
        
        # Apply custom filtering
        if filter:
            if filter.get('low_stock'):
                qs = qs.filter(stock__lt=10)
        
        # Apply ordering
        if order_by:
            if order_by.startswith('-'):
                qs = qs.order_by(order_by)
            else:
                qs = qs.order_by(order_by)
        
        return qs
    
    def resolve_all_orders(self, info, filter=None, order_by=None, **kwargs):
        qs = Order.objects.all().select_related('customer').prefetch_related('items__product')
        
        # Apply custom filtering for related fields
        if filter:
            if filter.get('customer_name'):
                qs = qs.filter(customer__name__icontains=filter['customer_name'])
            if filter.get('product_name'):
                qs = qs.filter(items__product__name__icontains=filter['product_name'])
            if filter.get('product_id'):
                qs = qs.filter(items__product__id=filter['product_id'])
        
        # Apply ordering
        if order_by:
            if order_by.startswith('-'):
                qs = qs.order_by(order_by)
            else:
                qs = qs.order_by(order_by)
        
        return qs.distinct()
    
    def resolve_customers_by_name(self, info, name=None, email=None, **kwargs):
        qs = Customer.objects.all()
        if name:
            qs = qs.filter(name__icontains=name)
        if email:
            qs = qs.filter(email__icontains=email)
        return qs
    
    def resolve_products_by_price_range(self, info, min_price=None, max_price=None, **kwargs):
        qs = Product.objects.all()
        if min_price is not None:
            qs = qs.filter(price__gte=min_price)
        if max_price is not None:
            qs = qs.filter(price__lte=max_price)
        return qs.order_by('price')
    
    def resolve_orders_by_customer(self, info, customer_name=None, customer_email=None, **kwargs):
        qs = Order.objects.all().select_related('customer')
        if customer_name:
            qs = qs.filter(customer__name__icontains=customer_name)
        if customer_email:
            qs = qs.filter(customer__email__icontains=customer_email)
        return qs.order_by('-order_date')

# ==================== INPUT TYPES (same as before) ====================

class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()

class BulkCustomerInput(graphene.InputObjectType):
    customers = graphene.List(graphene.NonNull(CustomerInput), required=True)

class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    description = graphene.String()
    price = graphene.Decimal(required=True)
    stock = graphene.Int()

class OrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True)
    product_ids = graphene.List(graphene.NonNull(graphene.ID), required=True)
    order_date = graphene.DateTime()

# ==================== MUTATION CLASS ====================

class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
    update_low_stock_products = UpdateLowStockProducts.Field()

class UpdateLowStockProducts(graphene.Mutation):
    """
    Mutation to update low-stock products (stock < 10)
    Increments stock by 10 for each low-stock product
    """
    class Arguments:
        increment_by = graphene.Int(required=False, default_value=10)
    
    updated_products = graphene.List(ProductType)
    message = graphene.String()
    
    @classmethod
    def mutate(cls, root, info, increment_by=10):
        try:
            # Find products with stock less than 10
            low_stock_products = Product.objects.filter(stock__lt=10)
            
            # Update stock for each product
            updated_products = []
            for product in low_stock_products:
                product.stock += increment_by
                product.save()
                updated_products.append(product)
            
            count = len(updated_products)
            
            return UpdateLowStockProducts(
                updated_products=updated_products,
                message=f"Updated {count} low-stock products. Stock increased by {increment_by} each."
            )
            
        except Exception as e:
            raise Exception(f"Error updating low-stock products: {str(e)}")
