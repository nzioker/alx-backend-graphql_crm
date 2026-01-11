import os
import django
from django.utils import timezone
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_backend_graphql_crm.settings')
django.setup()

def log_crm_heartbeat():
    """
    Log heartbeat message every 5 minutes
    """
    timestamp = timezone.now().strftime("%d/%m/%Y-%H:%M:%S")
    
    # Log to file
    log_file = "/tmp/crm_heartbeat_log.txt"
    
    with open(log_file, "a") as f:
        f.write(f"{timestamp} CRM is alive\n")
    

    try:
        endpoint = "http://localhost:8000/graphql"
        transport = RequestsHTTPTransport(url=endpoint)
        client = Client(transport=transport, fetch_schema_from_transport=True)
        
        query = gql("""
        query {
            hello
        }
        """)
        
        result = client.execute(query)
        
        with open(log_file, "a") as f:
            f.write(f"{timestamp} GraphQL endpoint response: {result['hello']}\n")
        
        print(f"Heartbeat logged at {timestamp} - GraphQL responsive")
    except Exception as e:
        with open(log_file, "a") as f:
            f.write(f"{timestamp} GraphQL check failed: {str(e)}\n")
        
        print(f"Heartbeat logged at {timestamp} - GraphQL check failed")
