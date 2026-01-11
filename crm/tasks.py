"""
CRM Celery Tasks
"""
import os
import django
from celery import shared_task
from django.utils import timezone
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import requests
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_backend_graphql_crm.settings')
django.setup()

from crm.models import Customer, Order, Product

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_crm_report(self, report_type='weekly'):
    """
    Generate CRM report using GraphQL queries
    """
    timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    log_file = "/tmp/crm_report_log.txt"
    
    try:
        # GraphQL endpoint
        endpoint = "http://localhost:8000/graphql"
        transport = RequestsHTTPTransport(url=endpoint)
        client = Client(transport=transport, fetch_schema_from_transport=True)
        
        # GraphQL query for CRM statistics
        query = gql("""
        query GetCRMReport {
            # Customer statistics
            allCustomers {
                totalCount
            }
            
            # Order statistics
            allOrders {
                totalCount
                edges {
                    node {
                        totalAmount
                        status
                        orderDate
                    }
                }
            }
            
            # Product statistics
            allProducts {
                totalCount
                edges {
                    node {
                        name
                        stock
                        price
                    }
                }
            }
        }
        """)
        
        # Execute GraphQL query
        result = client.execute(query)
        
        # Extract data
        total_customers = result.get('allCustomers', {}).get('totalCount', 0)
        total_orders = result.get('allOrders', {}).get('totalCount', 0)
        orders = result.get('allOrders', {}).get('edges', [])
        products = result.get('allProducts', {}).get('edges', [])
        
        # Calculate total revenue
        total_revenue = 0
        status_counts = {}
        daily_orders = {}
        
        for order_edge in orders:
            order = order_edge['node']
            total_revenue += float(order['totalAmount'])
            
            # Count by status
            status = order['status']
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count by date (YYYY-MM-DD)
            order_date = order['orderDate'][:10] if order['orderDate'] else 'unknown'
            daily_orders[order_date] = daily_orders.get(order_date, 0) + 1
        
        # Calculate product statistics
        low_stock_products = 0
        total_product_value = 0
        
        for product_edge in products:
            product = product_edge['node']
            stock = int(product['stock'])
            price = float(product['price'])
            
            if stock < 10:
                low_stock_products += 1
            
            total_product_value += stock * price
        
        # Generate report content
        report_lines = [
            f"\n{'='*60}",
            f"CRM {report_type.capitalize()} Report - Generated: {timestamp}",
            f"{'='*60}",
            f"📊 SUMMARY",
            f"  • Total Customers: {total_customers}",
            f"  • Total Orders: {total_orders}",
            f"  • Total Revenue: ${total_revenue:,.2f}",
            f"  • Total Product Inventory Value: ${total_product_value:,.2f}",
            f"",
            f"📈 ORDER ANALYSIS",
            f"  • Order Status Distribution:",
        ]
        
        # Add status distribution
        for status, count in status_counts.items():
            percentage = (count / total_orders * 100) if total_orders > 0 else 0
            report_lines.append(f"    - {status.capitalize()}: {count} ({percentage:.1f}%)")
        
        report_lines.extend([
            f"",
            f"📦 PRODUCT ANALYSIS",
            f"  • Total Products: {len(products)}",
            f"  • Low Stock Products (< 10): {low_stock_products}",
            f"  • Average Product Price: ${total_product_value/sum(int(p['node']['stock']) for p in products):,.2f}" if products else "  • Average Product Price: $0.00",
        ])
        
        # Add recent daily orders (last 7 days)
        if daily_orders:
            report_lines.append(f"")
            report_lines.append(f"📅 RECENT DAILY ORDERS (Last 7 Days)")
            sorted_dates = sorted(daily_orders.keys(), reverse=True)[:7]
            for date in sorted_dates:
                report_lines.append(f"  • {date}: {daily_orders[date]} orders")
        
        report_lines.append(f"{'='*60}\n")
        
        # Log report to file
        with open(log_file, "a") as f:
            f.write("\n".join(report_lines))
        
        # Also log a concise version
        concise_log = f"{timestamp} - {report_type.capitalize()} Report: {total_customers} customers, {total_orders} orders, ${total_revenue:,.2f} revenue\n"
        with open("/tmp/crm_report_concise_log.txt", "a") as f:
            f.write(concise_log)
        
        # Return result for Celery monitoring
        return {
            'report_type': report_type,
            'timestamp': timestamp,
            'customers': total_customers,
            'orders': total_orders,
            'revenue': total_revenue,
            'status': 'success'
        }
        
    except Exception as e:
        # Log error
        error_msg = f"{timestamp} - Error generating CRM report: {str(e)}\n"
        with open(log_file, "a") as f:
            f.write(error_msg)
        
        # Retry the task
        raise self.retry(exc=e)

@shared_task
def generate_daily_report():
    """
    Generate daily CRM report (simpler version)
    """
    return generate_crm_report(report_type='daily')

@shared_task
def generate_monthly_report():
    """
    Generate monthly CRM report
    """
    return generate_crm_report(report_type='monthly')
