#!/usr/bin/env python3
"""
Order Reminder Script
Sends reminders for pending orders from the last 7 days
"""

import os
import sys
import datetime
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import django

# Add project to Python path
project_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_path)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_backend_graphql_crm.settings')
django.setup()

from django.utils import timezone

def send_order_reminders():
    """
    Query GraphQL for pending orders from the last 7 days and log reminders
    """
    # GraphQL endpoint
    endpoint = "http://localhost:8000/graphql"
    
    # Configure GraphQL client
    transport = RequestsHTTPTransport(url=endpoint)
    client = Client(transport=transport, fetch_schema_from_transport=True)
    
    # Calculate date 7 days ago
    seven_days_ago = timezone.now() - datetime.timedelta(days=7)
    
    # GraphQL query for pending orders
    query = gql("""
    query GetPendingOrders($fromDate: DateTime!) {
        allOrders(filter: { 
            orderDateGte: $fromDate,
            status: "pending"
        }) {
            edges {
                node {
                    id
                    customer {
                        name
                        email
                    }
                    orderDate
                    totalAmount
                }
            }
        }
    }
    """)
    
    try:
        # Execute GraphQL query
        result = client.execute(query, variable_values={
            "fromDate": seven_days_ago.isoformat()
        })
        
        # Process orders
        orders = result.get('allOrders', {}).get('edges', [])
        
        # Log file
        log_file = "/tmp/order_reminders_log.txt"
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(log_file, "a") as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"Order Reminders - {timestamp}\n")
            f.write(f"{'='*50}\n")
            
            if not orders:
                f.write("No pending orders found from the last 7 days.\n")
                print("No pending orders to process.")
            else:
                for order_edge in orders:
                    order = order_edge['node']
                    customer = order['customer']
                    
                    log_line = f"Order ID: {order['id']}, Customer: {customer['name']} ({customer['email']}), "
                    log_line += f"Date: {order['orderDate']}, Amount: ${order['totalAmount']}\n"
                    
                    f.write(log_line)
                    print(f"Reminder for: {customer['name']} - Order #{order['id']}")
        
        print("Order reminders processed!")
        
    except Exception as e:
        # Log error
        error_log = "/tmp/order_reminders_log.txt"
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(error_log, "a") as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"ERROR - {timestamp}\n")
            f.write(f"Error: {str(e)}\n")
        
        print(f"Error processing order reminders: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    send_order_reminders()
