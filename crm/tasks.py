from celery import shared_task
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from datetime import datetime
import logging
import requests

logger = logging.getLogger(__name__)

@shared_task
def generate_crm_report():
    """
    Celery task to generate weekly CRM report using GraphQL queries
    """
    try:
        # Setup GraphQL client
        transport = RequestsHTTPTransport(
            url="http://localhost:8000/graphql",
            use_json=True
        )
        client = Client(transport=transport, fetch_schema_from_transport=True)
        
        # GraphQL query to get CRM statistics
        query = gql("""
            query {
                totalCustomers: customers {
                    totalCount
                }
                totalOrders: orders {
                    totalCount
                }
                totalRevenue: orders {
                    edges {
                        node {
                            totalAmount
                        }
                    }
                }
            }
        """)
        
        # Execute the query
        result = client.execute(query)
        
        # Extract data
        total_customers = result.get('totalCustomers', {}).get('totalCount', 0)
        total_orders = result.get('totalOrders', {}).get('totalCount', 0)
        
        # Calculate total revenue
        total_revenue = 0
        revenue_edges = result.get('totalRevenue', {}).get('edges', [])
        for edge in revenue_edges:
            total_amount = edge.get('node', {}).get('totalAmount', 0)
            total_revenue += float(total_amount) if total_amount else 0
        
        # Format the report
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        report_message = f"{timestamp} - Report: {total_customers} customers, {total_orders} orders, {total_revenue:.2f} revenue"
        
        # Log to file
        with open('/tmp/crm_report_log.txt', 'a') as log_file:
            log_file.write(report_message + '\n')
        
        # Also log to Celery logger
        logger.info(f"CRM report generated: {report_message}")
        
        return {
            'status': 'success',
            'customers': total_customers,
            'orders': total_orders,
            'revenue': total_revenue,
            'message': report_message
        }
        
    except Exception as e:
        error_message = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error generating CRM report: {str(e)}"
        
        # Log error to file
        with open('/tmp/crm_report_log.txt', 'a') as log_file:
            log_file.write(error_message + '\n')
        
        logger.error(error_message)
        
        return {
            'status': 'error',
            'message': error_message
        }
