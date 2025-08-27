#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Change to project directory (where manage.py is located)
cd "$PROJECT_DIR" || exit 1

# Execute Django command to delete inactive customers
DELETED_COUNT=$(python manage.py shell -c "
from django.utils import timezone
from datetime import timedelta
from customers.models import Customer
from orders.models import Order

# Calculate date one year ago from now
one_year_ago = timezone.now() - timedelta(days=365)

# Find customers to delete:
# 1. Customers with NO orders at all
# 2. Customers whose last order was more than 1 year ago
inactive_customers = Customer.objects.filter(
    orders__isnull=True  # No orders at all
) | Customer.objects.exclude(
    orders__order_date__gte=one_year_ago  # No recent orders
).distinct()  # Remove duplicates

# Count how many will be deleted, then delete them
count = inactive_customers.count()
inactive_customers.delete()
print(count)  # This output gets captured by DELETED_COUNT
")

# Get current date and time
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Log the result to file
echo "[$TIMESTAMP] Deleted $DELETED_COUNT inactive customers" >> /tmp/customer_cleanup_log.txt
