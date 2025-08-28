from datetime import datetime
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

def log_crm_heartbeat():
    """
    Logs a heartbeat message every 5 minutes to confirm CRM application health.
    Also verifies GraphQL endpoint responsiveness.
    """
    # Get current timestamp in required format
    timestamp = datetime.now().strftime('%d/%m/%Y-%H:%M:%S')
    
    # Log basic heartbeat message
    heartbeat_message = f"{timestamp} CRM is alive"
    
    # Try to verify GraphQL endpoint
    graphql_status = "GraphQL endpoint: "
    try:
        # Setup GraphQL client
        transport = RequestsHTTPTransport(
            url="http://localhost:8000/graphql",
            use_json=True
        )
        client = Client(transport=transport, fetch_schema_from_transport=True)
        
        # Query hello field to verify endpoint
        query = gql("""
            query {
                hello
            }
        """)
        
        result = client.execute(query)
        if 'hello' in result:
            graphql_status += "responsive"
        else:
            graphql_status += "unexpected response"
            
    except Exception as e:
        graphql_status += f"error: {str(e)}"
    
    # Combine messages
    full_message = f"{heartbeat_message} - {graphql_status}"
    
    # Append to log file
    with open('/tmp/crm_heartbeat_log.txt', 'a') as log_file:
        log_file.write(full_message + '\n')
    
    return full_message

def update_low_stock():
    """
    Cron job that runs every 12 hours to update low-stock products
    and log the updates.
    """
    timestamp = datetime.now().strftime('%d/%m/%Y-%H:%M:%S')
    
    try:
        # Setup GraphQL client
        transport = RequestsHTTPTransport(
            url="http://localhost:8000/graphql",
            use_json=True
        )
        client = Client(transport=transport, fetch_schema_from_transport=True)
        
        # Define the mutation
        mutation = gql("""
            mutation {
                updateLowStockProducts {
                    success
                    message
                    updatedProducts {
                        id
                        name
                        stock
                    }
                }
            }
        """)
        
        # Execute the mutation
        result = client.execute(mutation)
        mutation_result = result.get('updateLowStockProducts', {})
        
        # Log the results
        if mutation_result.get('success'):
            updated_products = mutation_result.get('updatedProducts', [])
            message = mutation_result.get('message', '')
            
            # Log success message
            log_message = f"[{timestamp}] {message}\n"
            
            # Log details of each updated product
            for product in updated_products:
                log_message += f"  - {product['name']}: Stock updated to {product['stock']}\n"
            
            # Write to log file
            with open('/tmp/low_stock_updates_log.txt', 'a') as log_file:
                log_file.write(log_message + '\n')
            
            return f"Success: {message}"
            
        else:
            error_message = mutation_result.get('message', 'Unknown error')
            log_message = f"[{timestamp}] Failed to update low-stock products: {error_message}"
            
            with open('/tmp/low_stock_updates_log.txt', 'a') as log_file:
                log_file.write(log_message + '\n')
            
            return f"Error: {error_message}"
            
    except Exception as e:
        error_msg = f"[{timestamp}] GraphQL mutation failed: {str(e)}"
        
        with open('/tmp/low_stock_updates_log.txt', 'a') as log_file:
            log_file.write(error_msg + '\n')
        
        return f"Exception: {str(e)}"
