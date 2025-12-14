import graphene
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
import re
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from .models import Customer, Product, Order, OrderItem

# ==================== TYPES ====================

class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            'name': ['exact', 'icontains', 'istartswith'],
            'email': ['exact', 'icontains'],
            'phone': ['exact', 'icontains'],
            'created_at': ['exact', 'gte', 'lte'],
        }

class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            'name': ['exact', 'icontains', 'istartswith'],
            'price': ['exact', 'gte', 'lte'],
            'stock': ['exact', 'gte', 'lte'],
            'created_at': ['exact', 'gte', 'lte'],
        }

class OrderItemType(DjangoObjectType):
    class Meta:
        model = OrderItem

class OrderType(DjangoObjectType):
    items = graphene.List(OrderItemType)
    
    class Meta:
        model = Order
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            'total_amount': ['exact', 'gte', 'lte'],
            'order_date': ['exact', 'gte', 'lte'],
            'status': ['exact'],
            'created_at': ['exact', 'gte', 'lte'],
        }
    
    def resolve_items(self, info):
        return self.items.all()

# ==================== INPUT TYPES ====================

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

# ==================== VALIDATION UTILITIES ====================

def validate_phone_number(phone):
    """Validate phone number format"""
    if not phone:
        return True
    
    # Allow formats: +1234567890 or 123-456-7890
    pattern = r'^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$'
    if not re.match(pattern, phone):
        raise ValidationError("Phone number must be in format: +1234567890 or 123-456-7890")
    return True

def validate_email_unique(email):
    """Validate email uniqueness"""
    if Customer.objects.filter(email=email).exists():
        raise ValidationError(f"Email '{email}' already exists")
    return True

# ==================== MUTATIONS ====================

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
            
            # Validate email format
            validate_email(input.email)
            
            # Validate email uniqueness
            validate_email_unique(input.email)
            
            # Validate phone format if provided
            if input.phone:
                validate_phone_number(input.phone)
            
            # Create customer
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
        
        # Use transaction to ensure atomicity
        with transaction.atomic():
            for idx, customer_data in enumerate(input.customers):
                try:
                    # Validate inputs
                    if not customer_data.name or not customer_data.email:
                        errors.append(f"Customer {idx+1}: Name and email are required")
                        continue
                    
                    # Validate email format
                    try:
                        validate_email(customer_data.email)
                    except ValidationError:
                        errors.append(f"Customer {idx+1}: Invalid email format")
                        continue
                    
                    # Validate email uniqueness (within this batch and existing DB)
                    existing_emails = [c.email for c in customers]
                    if customer_data.email in existing_emails:
                        errors.append(f"Customer {idx+1}: Email already in batch")
                        continue
                    
                    if Customer.objects.filter(email=customer_data.email).exists():
                        errors.append(f"Customer {idx+1}: Email already exists in database")
                        continue
                    
                    # Validate phone format if provided
                    if customer_data.phone:
                        try:
                            validate_phone_number(customer_data.phone)
                        except ValidationError as e:
                            errors.append(f"Customer {idx+1}: {e.message}")
                            continue
                    
                    # Create customer
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
            # Validate inputs
            if Decimal(str(input.price)) <= 0:
                raise ValidationError("Price must be positive")
            
            if input.stock is not None and input.stock < 0:
                raise ValidationError("Stock cannot be negative")
            
            # Create product
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
            # Validate inputs
            if not input.product_ids:
                raise ValidationError("At least one product is required")
            
            # Get customer
            try:
                customer = Customer.objects.get(id=input.customer_id)
            except Customer.DoesNotExist:
                raise ValidationError(f"Customer with ID {input.customer_id} not found")
            
            # Get products and validate existence
            products = []
            total_amount = Decimal('0.00')
            
            for product_id in input.product_ids:
                try:
                    product = Product.objects.get(id=product_id)
                    if product.stock <= 0:
                        raise ValidationError(f"Product '{product.name}' is out of stock")
                    products.append(product)
                    total_amount += product.price
                except Product.DoesNotExist:
                    raise ValidationError(f"Product with ID {product_id} not found")
            
            # Create order and order items in transaction
            with transaction.atomic():
                # Create order
                order = Order.objects.create(
                    customer=customer,
                    total_amount=total_amount,
                    order_date=input.order_date if input.order_date else None
                )
                
                # Create order items
                for product in products:
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=1,
                        price_at_purchase=product.price
                    )
                    
                    # Update product stock
                    product.stock -= 1
                    product.save()
            
            # Refresh order to get relationships
            order.refresh_from_db()
            
            return CreateOrder(order=order)
            
        except ValidationError as e:
            raise Exception(f"Validation error: {', '.join(e.messages)}")
        except Exception as e:
            raise Exception(f"Error creating order: {str(e)}")

# ==================== MUTATION CLASS ====================

class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()

# ==================== QUERY CLASS ====================

class Query(graphene.ObjectType):
    hello = graphene.String()
    customer = graphene.relay.Node.Field(CustomerType)
    all_customers = DjangoFilterConnectionField(CustomerType)
    product = graphene.relay.Node.Field(ProductType)
    all_products = DjangoFilterConnectionField(ProductType)
    order = graphene.relay.Node.Field(OrderType)
    all_orders = DjangoFilterConnectionField(OrderType)
    
    def resolve_hello(self, info):
        return "Hello, GraphQL!"
    
    def resolve_all_customers(self, info, **kwargs):
        return Customer.objects.all()
    
    def resolve_all_products(self, info, **kwargs):
        return Product.objects.all()
    
    def resolve_all_orders(self, info, **kwargs):
        return Order.objects.all().select_related('customer').prefetch_related('items__product')
