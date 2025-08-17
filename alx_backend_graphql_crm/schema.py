import graphene
from crm.schema import Query as CRMQuery, Mutation as CRMMutation
class Query(graphene.ObjectType):
    hello = graphene.String(default_value="Hello, GraphQL!")

schema = graphene.Schema(query=Query)
class Query(CRMQuery, graphene.ObjectType):
    pass

class Mutation(CRMMutation, graphene.ObjectType):
    pass

schema = graphene.Schema(query=Query, mutation=Mutation)

import graphene
from graphene_django import DjangoObjectType
from django.db import transaction
from .models import Customer, Product, Order
from django.core.exceptions import ValidationError
from graphql import GraphQLError
from datetime import datetime
import re

# --------------------------
# TYPES
# --------------------------

class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer

class ProductType(DjangoObjectType):
    class Meta:
        model = Product

class OrderType(DjangoObjectType):
    class Meta:
        model = Order
    
    total_amount = graphene.Float()
    
    def resolve_total_amount(self, info):
        return float(self.total_amount)

# --------------------------
# INPUT TYPES
# --------------------------

class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()

class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Decimal(required=True)
    stock = graphene.Int()

class OrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True)
    product_ids = graphene.List(graphene.ID, required=True)
    order_date = graphene.DateTime()

# --------------------------
# MUTATIONS
# --------------------------

class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)
    
    customer = graphene.Field(CustomerType)
    message = graphene.String()
    success = graphene.Boolean()
    
    @classmethod
    def mutate(cls, root, info, input):
        try:
            # Validate phone format if provided
            if input.phone and not re.match(r'^\+?\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}$', input.phone):
                raise GraphQLError("Invalid phone format. Use '+1234567890' or '123-456-7890'")
            
            customer = Customer(
                name=input.name,
                email=input.email,
                phone=input.phone
            )
            customer.full_clean()
            customer.save()
            return CreateCustomer(
                customer=customer,
                message="Customer created successfully",
                success=True
            )
        except ValidationError as e:
            if 'email' in e.message_dict:
                raise GraphQLError("A customer with this email already exists.")
            raise GraphQLError(str(e))
        except Exception as e:
            raise GraphQLError(f"Error creating customer: {str(e)}")

class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        inputs = graphene.List(CustomerInput, required=True)
    
    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)
    success = graphene.Boolean()
    
    @classmethod
    @transaction.atomic
    def mutate(cls, root, info, inputs):
        customers = []
        errors = []
        
        for idx, input_data in enumerate(inputs):
            try:
                # Validate phone format if provided
                if input_data.phone and not re.match(r'^\+?\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}$', input_data.phone):
                    raise ValidationError("Invalid phone format")
                
                customer = Customer(
                    name=input_data.name,
                    email=input_data.email,
                    phone=input_data.phone
                )
                customer.full_clean()
                customer.save()
                customers.append(customer)
            except ValidationError as e:
                error_msg = f"Row {idx + 1}: "
                if 'email' in e.message_dict:
                    error_msg += "Email already exists"
                elif 'phone' in e.message_dict:
                    error_msg += "Invalid phone format"
                else:
                    error_msg += str(e)
                errors.append(error_msg)
            except Exception as e:
                errors.append(f"Row {idx + 1}: {str(e)}")
        
        return BulkCreateCustomers(
            customers=customers,
            errors=errors,
            success=len(errors) == 0
        )

class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)
    
    product = graphene.Field(ProductType)
    success = graphene.Boolean()
    
    @classmethod
    def mutate(cls, root, info, input):
        try:
            if float(input.price) <= 0:
                raise ValidationError("Price must be positive")
            
            stock = input.stock if input.stock is not None else 0
            if stock < 0:
                raise ValidationError("Stock cannot be negative")
            
            product = Product(
                name=input.name,
                price=input.price,
                stock=stock
            )
            product.full_clean()
            product.save()
            return CreateProduct(product=product, success=True)
        except ValidationError as e:
            raise GraphQLError(str(e))
        except Exception as e:
            raise GraphQLError(f"Error creating product: {str(e)}")

class CreateOrder(graphene.Mutation):
    class Arguments:
        input = OrderInput(required=True)
    
    order = graphene.Field(OrderType)
    success = graphene.Boolean()
    
    @classmethod
    def mutate(cls, root, info, input):
        try:
            # Validate customer exists
            try:
                customer = Customer.objects.get(pk=input.customer_id)
            except Customer.DoesNotExist:
                raise GraphQLError(f"Customer with ID {input.customer_id} does not exist")
            
            # Validate products exist
            products = []
            for product_id in input.product_ids:
                try:
                    product = Product.objects.get(pk=product_id)
                    products.append(product)
                except Product.DoesNotExist:
                    raise GraphQLError(f"Product with ID {product_id} does not exist")
            
            if not products:
                raise GraphQLError("At least one product is required")
            
            # Create order
            order = Order(
                customer=customer,
                order_date=input.order_date if input.order_date else datetime.now()
            )
            order.save()
            order.products.set(products)
            
            # Calculate and save total amount
            order.total_amount = sum(product.price for product in products)
            order.save()
            
            return CreateOrder(order=order, success=True)
        except Exception as e:
            raise GraphQLError(f"Error creating order: {str(e)}")

# --------------------------
# SCHEMA DEFINITION
# --------------------------

class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()

class Query(graphene.ObjectType):
    customers = graphene.List(CustomerType)
    products = graphene.List(ProductType)
    orders = graphene.List(OrderType)
    
    def resolve_customers(root, info):
        return Customer.objects.all()
    
    def resolve_products(root, info):
        return Product.objects.all()
    
    def resolve_orders(root, info):
        return Order.objects.all()