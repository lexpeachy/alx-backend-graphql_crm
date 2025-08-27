#!/usr/bin/env python3

from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from datetime import datetime, timedelta

def send_order_reminders():
    # GraphQL endpoint configuration
    transport = RequestsHTTPTransport(
        url="http://localhost:8000/graphql",
        use_json=True
    )
    
    # Create GraphQL client
    client = Client(transport=transport, fetch_schema_from_transport=True)
    
    # Calculate date 7 days ago
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    # GraphQL query to get pending orders from the last 7 days
    query = gql("""
    query GetPendingOrders($sevenDaysAgo: String!) {
        orders(filter: {orderDate_Gte: $sevenDaysAgo}, status: "pending") {
            edges {
                node {
                    id
                    orderDate
                    customer {
                        email
                    }
                }
            }
        }
    }
    """)
    
    try:
        # Execute GraphQL query with variables
        result = client.execute(query, variable_values={"sevenDaysAgo": seven_days_ago})
        
        # Get current timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Extract orders from result
        orders = result.get('orders', {}).get('edges', [])
        
        # Log each order
        for order_edge in orders:
            order = order_edge['node']
            order_id = order.get('id', 'N/A')
            customer_email = order.get('customer', {}).get('email', 'N/A')
            order_date = order.get('orderDate', 'N/A')
            
            log_entry = f"[{timestamp}] Order ID: {order_id}, Customer Email: {customer_email}, Order Date: {order_date}"
            log_message(log_entry)
        
        # Print success message and log
        success_msg = f"[{timestamp}] Order reminders processed! Found {len(orders)} pending orders."
        log_message(success_msg)
        print("Order reminders processed!")
        
    except Exception as e:
        error_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error: {e}"
        log_message(error_msg)
        print(f"Error: {e}")

def log_message(message):
    """Append message to log file"""
    with open('/tmp/order_reminders_log.txt', 'a') as log_file:
        log_file.write(message + '\n')

if __name__ == "__main__":
    send_order_reminders()
