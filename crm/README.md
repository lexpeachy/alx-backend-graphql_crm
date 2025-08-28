markdown
# CRM Celery Setup Guide

This guide explains how to set up Celery with Celery Beat for generating weekly CRM reports.

## Prerequisites

- Python 3.8+
- Redis server
- Django project with GraphQL endpoint

## Installation Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
2. Install and Start Redis
On Ubuntu/Debian:

bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis
On macOS:

bash
brew install redis
brew services start redis
On Windows:
Download Redis from https://github.com/microsoftarchive/redis/releases

3. Run Django Migrations
bash
python manage.py migrate
4. Start Celery Worker
bash
celery -A crm worker -l info
5. Start Celery Beat (Scheduler)
bash
celery -A crm beat -l info
6. Start Django Development Server
bash
python manage.py runserver
Verification
Check that all services are running:

Django server (port 8000)

Redis server (port 6379)

Celery worker

Celery beat

Verify the report generation by checking the log file:

bash
tail -f /tmp/crm_report_log.txt
The report will be generated every Monday at 6:00 AM

Manual Testing
You can manually trigger the report task:

bash
python manage.py shell -c "
from crm.tasks import generate_crm_report
result = generate_crm_report.delay()
print('Task ID:', result.id)
"
Troubleshooting
Redis connection issues: Ensure Redis is running on localhost:6379

GraphQL connection issues: Ensure Django server is running on localhost:8000

Task not executing: Check Celery worker and beat logs for errors

Schedule
The report runs every Monday at 6:00 AM UTC

Logs are stored in /tmp/crm_report_log.txt

Task results are stored in Redis

text

## 7. Expected Log Output

The `/tmp/crm_report_log.txt` file will contain entries like:
2024-01-15 06:00:00 - Report: 150 customers, 325 orders, 12500.75 revenue
2024-01-22 06:00:00 - Report: 155 customers, 340 orders, 13200.50 revenue
2024-01-29 06:00:00 - Report: 160 customers, 360 orders, 14500.25 revenue

text

## Important Notes:

1. **Redis must be installed and running** on localhost:6379
2. **Django development server** must be running for GraphQL queries to work
3. **The task runs every Monday at 6:00 AM UTC** (adjust timezone in settings if needed)
4. **Make sure your GraphQL schema** has the required queries for customers, orders, and totalAmount field

This setup provides a robust weekly reporting system using Celery with automatic scheduling through Celery Beat.
