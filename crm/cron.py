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
