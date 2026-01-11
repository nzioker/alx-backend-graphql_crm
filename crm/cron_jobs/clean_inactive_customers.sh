#!/bin/bash



# Get the project directory (assuming script is in crm/cron_jobs)
PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_DIR"

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Create log file with timestamp
LOG_FILE="/tmp/customer_cleanup_log.txt"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "========================================" >> "$LOG_FILE"
echo "Customer Cleanup Started: $TIMESTAMP" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Execute Python command to delete inactive customers
python_output=$(python manage.py shell << 'EOF'
import datetime
from django.utils import timezone
from django.db.models import Q
from crm.models import Customer, Order

# Calculate date one year ago
one_year_ago = timezone.now() - datetime.timedelta(days=365)

try:
    # Find customers with no orders OR last order older than a year
    inactive_customers = Customer.objects.filter(
        Q(orders__isnull=True) |  # Customers with no orders
        Q(orders__order_date__lt=one_year_ago)  # Last order older than a year
    ).distinct()
    
    # Count before deletion
    count = inactive_customers.count()
    
    if count > 0:
        # Get customer details for logging
        customer_details = []
        for customer in inactive_customers:
            last_order = customer.orders.order_by('-order_date').first()
            last_order_date = last_order.order_date if last_order else "No orders"
            customer_details.append(f"  - {customer.name} ({customer.email}), Last Order: {last_order_date}")
        
        # Delete inactive customers
        inactive_customers.delete()
        
        # Prepare output
        result = f"Deleted {count} inactive customers:\n" + "\n".join(customer_details)
    else:
        result = "No inactive customers found to delete."
    
    print(result)
    
except Exception as e:
    print(f"Error during customer cleanup: {str(e)}")

EOF
)

# Log the results
echo "$python_output" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
echo "Customer Cleanup Completed: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "Cleanup completed. Check $LOG_FILE for details."
