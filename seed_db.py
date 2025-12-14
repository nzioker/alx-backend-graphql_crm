import os
import django
from decimal import Decimal
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_backend_graphql_crm.settings')
django.setup()

from crm.models import Customer, Product, Order, OrderItem

def clear_data():
    """Clear all existing data"""
    OrderItem.objects.all().delete()
    Order.objects.all().delete()
    Product.objects.all().delete()
    Customer.objects.all().delete()
    print(" Cleared existing data")

def seed_customers():
    """Seed customers"""
    customers_data = [
        {
            'id': uuid.UUID('11111111-1111-1111-1111-111111111111'),
            'name': 'Alice Johnson',
            'email': 'alice@example.com',
            'phone': '+1234567890'
        },
        {
            'id': uuid.UUID('22222222-2222-2222-2222-222222222222'),
            'name': 'Bob Smith',
            'email': 'bob@example.com',
            'phone': '123-456-7890'
        },
        {
            'id': uuid.UUID('33333333-3333-3333-3333-333333333333'),
            'name': 'Carol Williams',
            'email': 'carol@example.com',
            'phone': '+1987654321'
        },
        {
            'id': uuid.UUID('44444444-4444-4444-4444-444444444444'),
            'name': 'David Brown',
            'email': 'david@example.com',
            'phone': '987-654-3210'
        },
        {
            'id': uuid.UUID('55555555-5555-5555-5555-555555555555'),
            'name': 'Eva Davis',
            'email': 'eva@example.com',
            'phone': '+1122334455'
        }
    ]
    
    created_customers = []
    for customer_data in customers_data:
        customer = Customer.objects.create(**customer_data)
        created_customers.append(customer)
        print(f" Created customer: {customer.name} ({customer.email})")
    
    return created_customers

def seed_products():
    """Seed products"""
    products_data = [
        {
            'id': uuid.UUID('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
            'name': 'Laptop Pro',
            'description': 'High-performance laptop with 16GB RAM, 512GB SSD',
            'price': Decimal('1299.99'),
            'stock': 15
        },
        {
            'id': uuid.UUID('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'),
            'name': 'Smartphone X',
            'description': 'Latest smartphone with 128GB storage',
            'price': Decimal('899.99'),
            'stock': 30
        },
        {
            'id': uuid.UUID('cccccccc-cccc-cccc-cccc-cccccccccccc'),
            'name': 'Wireless Headphones',
            'description': 'Noise-cancelling wireless headphones',
            'price': Decimal('249.99'),
            'stock': 50
        },
        {
            'id': uuid.UUID('dddddddd-dddd-dddd-dddd-dddddddddddd'),
            'name': 'Smart Watch',
            'description': 'Fitness tracking smartwatch with GPS',
            'price': Decimal('299.99'),
            'stock': 25
        },
        {
            'id': uuid.UUID('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee'),
            'name': 'Tablet Air',
            'description': 'Lightweight tablet with 10-inch display',
            'price': Decimal('499.99'),
            'stock': 20
        }
    ]
    
    created_products = []
    for product_data in products_data:
        product = Product.objects.create(**product_data)
        created_products.append(product)
        print(f" Created product: {product.name} - ${product.price} (Stock: {product.stock})")
    
    return created_products

def seed_orders(customers, products):
    """Seed orders"""
    orders_data = [
        {
            'customer': customers[0],  # Alice
            'products_with_quantities': [
                (products[0], 1),  # Laptop Pro
                (products[2], 2),  # Wireless Headphones
            ]
        },
        {
            'customer': customers[1],  # Bob
            'products_with_quantities': [
                (products[1], 1),  # Smartphone X
                (products[3], 1),  # Smart Watch
            ]
        },
        {
            'customer': customers[2],  # Carol
            'products_with_quantities': [
                (products[4], 1),  # Tablet Air
                (products[2], 1),  # Wireless Headphones
                (products[3], 1),  # Smart Watch
            ]
        },
        {
            'customer': customers[3],  # David
            'products_with_quantities': [
                (products[0], 2),  # Laptop Pro (2 units)
                (products[1], 1),  # Smartphone X
            ]
        },
        {
            'customer': customers[4],  # Eva
            'products_with_quantities': [
                (products[2], 3),  # Wireless Headphones (3 units)
                (products[4], 1),  # Tablet Air
            ]
        }
    ]
    
    created_orders = []
    for order_data in orders_data:
        # Calculate total amount
        total_amount = Decimal('0.00')
        for product, quantity in order_data['products_with_quantities']:
            total_amount += product.price * quantity
        
        # Create order
        order = Order.objects.create(
            customer=order_data['customer'],
            total_amount=total_amount,
            status='delivered'
        )
        
        # Create order items
        for product, quantity in order_data['products_with_quantities']:
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price_at_purchase=product.price
            )
            
            # Update product stock
            product.stock -= quantity
            product.save()
        
        created_orders.append(order)
        print(f" Created order: {order.id} for {order.customer.name} - Total: ${order.total_amount}")
    
    return created_orders

def display_sample_data(customers, products, orders):
    """Display sample data for verification"""
    print("\n" + "="*60)
    print("SAMPLE DATA")
    print("="*60)
    
    print("\n Customers:")
    for customer in customers[:3]:
        print(f"  - {customer.name}: {customer.email} ({customer.phone})")
    
    print("\n Products:")
    for product in products[:3]:
        print(f"  - {product.name}: ${product.price} (Stock: {product.stock})")
    
    print("\n Orders:")
    for order in orders[:2]:
        print(f"  - Order {order.id}:")
        print(f"    Customer: {order.customer.name}")
        print(f"    Total: ${order.total_amount}")
        print(f"    Status: {order.status}")
        print(f"    Items:")
        for item in order.items.all()[:3]:
            print(f"      - {item.quantity}x {item.product.name} @ ${item.price_at_purchase}")

def run():
    """Main seeding function"""
    print("="*60)
    print("STARTING DATABASE SEEDING")
    print("="*60)
    
    try:
        # Clear existing data
        clear_data()
        
        # Seed data
        print("\n Seeding customers...")
        customers = seed_customers()
        
        print("\n Seeding products...")
        products = seed_products()
        
        print("\n Seeding orders...")
        orders = seed_orders(customers, products)
        
        # Display sample data
        display_sample_data(customers, products, orders)
        
        # Summary
        print("\n" + "="*60)
        print("SEEDING COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f" Created: {len(customers)} customers")
        print(f" Created: {len(products)} products")
        print(f" Created: {len(orders)} orders")
        print("\nYou can now test the GraphQL mutations at: http://localhost:8000/graphql")
        print("="*60)
        
    except Exception as e:
        print(f"\n Error during seeding: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run()
