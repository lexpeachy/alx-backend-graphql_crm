import os
import django
from faker import Faker
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'graphql_crm.settings')
django.setup()

from crm.models import Customer, Product, Order

fake = Faker()

def seed_customers(count=10):
    for _ in range(count):
        Customer.objects.create(
            name=fake.name(),
            email=fake.unique.email(),
            phone=fake.phone_number()[:15]
        )

def seed_products(count=5):
    for i in range(count):
        Product.objects.create(
            name=f"Product {i+1}",
            price=Decimal(fake.random_number(digits=3)) + Decimal('0.99'),
            stock=fake.random_int(min=0, max=100)
        )

def seed_orders(count=5):
    customers = list(Customer.objects.all())
    products = list(Product.objects.all())
    
    for _ in range(count):
        customer = fake.random_element(customers)
        order = Order.objects.create(customer=customer)
        
        # Add 1-3 random products to each order
        selected_products = fake.random_elements(
            elements=products,
            unique=True,
            length=fake.random_int(min=1, max=3)
        )
        order.products.set(selected_products)
        order.save()  # This will trigger total_amount calculation

if __name__ == '__main__':
    print("Seeding data...")
    Customer.objects.all().delete()
    Product.objects.all().delete()
    Order.objects.all().delete()
    
    seed_customers()
    seed_products()
    seed_orders()
    
    print("Seeding completed!")