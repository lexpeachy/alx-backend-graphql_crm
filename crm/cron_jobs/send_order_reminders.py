#!/usr/bin/env python3

import requests
from datetime import datetime, timedelta
import json

def send_order_reminders():
    # GraphQL endpoint
    url = "http://localhost:8000/graphql"
    
    # Calculate date 7 days ago
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    # GraphQL query to get pending orders from the last 7 days
    query = """
    query {
        orders(filter: {orderDate_Gte: "%s"}, status: "pending") {
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
    """ % seven_days_ago
    
    try:
        # Send GraphQL request
        response = requests.post(url, json={'query': query})
        response.raise_for_status()
        
        data = response.json()
        
        # Check for errors in GraphQL response
        if 'errors' in data:
            error_msg = f"GraphQL errors: {data['errors']}"
            log_message(error_msg)
            print(error_msg)
            return
        
        # Extract orders from response
        orders = data.get('data', {}).get('orders', {}).get('edges', [])
        
        # Get current timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Log each order
        for order_edge in orders:
            order = order_edge['node']
            order_id = order.get('id', 'N/A')
            customer_email = order.get('customer', {}).get('email', 'N/A')
            order_date = order.get('orderDate', 'N/A')
            
            log_entry = f"[{timestamp}] Order ID: {order_id}, Customer Email: {customer_email}, Order Date: {order_date}"
            log_message(log_entry)
        
        # Print success message
        success_msg = f"[{timestamp}] Order reminders processed! Found {len(orders)} pending orders."
        log_message(success_msg)
        print("Order reminders processed!")
        
    except requests.exceptions.RequestException as e:
        error_msg = f"HTTP request failed: {e}"
        log_message(error_msg)
        print(error_msg)
    except json.JSONDecodeError as e:
        error_msg = f"JSON decode error: {e}"
        log_message(error_msg)
        print(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        log_message(error_msg)
        print(error_msg)

def log_message(message):
    """Append message to log file"""
    with open('/tmp/order_reminders_log.txt', 'a') as log_file:
        log_file.write(message + '\n')

if __name__ == "__main__":
    send_order_reminders()
