import graphene
from graphene_django import DjangoObjectType, DjangoFilterConnectionField
from django.db.models import Q
from django.db import transaction
from .models import Customer, Product, Order
from .filters import CustomerFilter, ProductFilter, OrderFilter
from django.core.exceptions import ValidationError
from graphql import GraphQLError
from datetime import datetime
import re

# --------------------------
# TYPES
# --------------------------

class CustomerNode(DjangoObjectType):
    class Meta:
        model = Customer
        interfaces = (graphene.relay.Node,)
        filterset_class = CustomerFilter

class ProductNode(DjangoObjectType):
    class Meta:
        model = Product
        interfaces = (graphene.relay.Node,)
        filterset_class = ProductFilter

class OrderNode(DjangoObjectType):
    class Meta:
        model = Order
        interfaces = (graphene.relay.Node,)
        filterset_class = OrderFilter
    
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

class CustomerFilterInput(graphene.InputObjectType):
    name = graphene.String()
    name_icontains = graphene.String()
    email = graphene.String()
    email_icontains = graphene.String()
    created_at_gte = graphene.Date()
    created_at_lte = graphene.Date()
    phone_pattern = graphene.String()

class ProductFilterInput(graphene.InputObjectType):
    name = graphene.String()
    name_icontains = graphene.String()
    price_gte = graphene.Float()
    price_lte = graphene.Float()
    stock_gte = graphene.Int()
    stock_lte = graphene.Int()
    low_stock = graphene.Boolean()

class OrderFilterInput(graphene.InputObjectType):
    total_amount_gte = graphene.Float()
    total_amount_lte = graphene.Float()
    order_date_gte = graphene.Date()
    order_date_lte = graphene.Date()
    customer_name = graphene.String()
    customer_name_icontains = graphene.String()
    product_name = graphene.String()
    product_name_icontains = graphene.String()
    product_id = graphene.ID()

# --------------------------
# MUTATIONS
# --------------------------

class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)
    
    customer = graphene.Field(CustomerNode)
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
    
    customers = graphene.List(CustomerNode)
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
    
    product = graphene.Field(ProductNode)
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
    
    order = graphene.Field(OrderNode)
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
# QUERIES
# --------------------------

class Query(graphene.ObjectType):
    customer = graphene.relay.Node.Field(CustomerNode)
    all_customers = DjangoFilterConnectionField(
        CustomerNode,
        filters=CustomerFilterInput(),
        order_by=graphene.List(of_type=graphene.String)
    )
    
    product = graphene.relay.Node.Field(ProductNode)
    all_products = DjangoFilterConnectionField(
        ProductNode,
        filters=ProductFilterInput(),
        order_by=graphene.List(of_type=graphene.String)
    )
    
    order = graphene.relay.Node.Field(OrderNode)
    all_orders = DjangoFilterConnectionField(
        OrderNode,
        filters=OrderFilterInput(),
        order_by=graphene.List(of_type=graphene.String)
    )
    
    def resolve_all_customers(self, info, **kwargs):
        filter_args = kwargs.get('filters', {})
        order_by = kwargs.get('order_by', [])
        
        queryset = Customer.objects.all()
        
        # Apply filters
        if filter_args:
            filters = Q()
            if filter_args.get('name_icontains'):
                filters &= Q(name__icontains=filter_args['name_icontains'])
            if filter_args.get('email_icontains'):
                filters &= Q(email__icontains=filter_args['email_icontains'])
            if filter_args.get('created_at_gte'):
                filters &= Q(created_at__gte=filter_args['created_at_gte'])
            if filter_args.get('created_at_lte'):
                filters &= Q(created_at__lte=filter_args['created_at_lte'])
            if filter_args.get('phone_pattern'):
                filters &= Q(phone__startswith=filter_args['phone_pattern'])
            
            queryset = queryset.filter(filters)
        
        # Apply ordering
        if order_by:
            queryset = queryset.order_by(*order_by)
        
        return queryset
    
    def resolve_all_products(self, info, **kwargs):
        filter_args = kwargs.get('filters', {})
        order_by = kwargs.get('order_by', [])
        
        queryset = Product.objects.all()
        
        # Apply filters
        if filter_args:
            filters = Q()
            if filter_args.get('name_icontains'):
                filters &= Q(name__icontains=filter_args['name_icontains'])
            if filter_args.get('price_gte'):
                filters &= Q(price__gte=filter_args['price_gte'])
            if filter_args.get('price_lte'):
                filters &= Q(price__lte=filter_args['price_lte'])
            if filter_args.get('stock_gte'):
                filters &= Q(stock__gte=filter_args['stock_gte'])
            if filter_args.get('stock_lte'):
                filters &= Q(stock__lte=filter_args['stock_lte'])
            if filter_args.get('low_stock'):
                filters &= Q(stock__lt=10)
            
            queryset = queryset.filter(filters)
        
        # Apply ordering
        if order_by:
            queryset = queryset.order_by(*order_by)
        
        return queryset
    
    def resolve_all_orders(self, info, **kwargs):
        filter_args = kwargs.get('filters', {})
        order_by = kwargs.get('order_by', [])
        
        queryset = Order.objects.all()
        
        # Apply filters
        if filter_args:
            filters = Q()
            if filter_args.get('total_amount_gte'):
                filters &= Q(total_amount__gte=filter_args['total_amount_gte'])
            if filter_args.get('total_amount_lte'):
                filters &= Q(total_amount__lte=filter_args['total_amount_lte'])
            if filter_args.get('order_date_gte'):
                filters &= Q(order_date__gte=filter_args['order_date_gte'])
            if filter_args.get('order_date_lte'):
                filters &= Q(order_date__lte=filter_args['order_date_lte'])
            if filter_args.get('customer_name_icontains'):
                filters &= Q(customer__name__icontains=filter_args['customer_name_icontains'])
            if filter_args.get('product_name_icontains'):
                filters &= Q(products__name__icontains=filter_args['product_name_icontains'])
            if filter_args.get('product_id'):
                filters &= Q(products__id=filter_args['product_id'])
            
            queryset = queryset.filter(filters).distinct()
        
        # Apply ordering
        if order_by:
            queryset = queryset.order_by(*order_by)
        
        return queryset

# --------------------------
# SCHEMA DEFINITION
# --------------------------

class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)
import graphene
from graphene_django.types import DjangoObjectType
from products.models import Product  # Adjust import based on your app structure

class ProductType(DjangoObjectType):
    class Meta:
        model = Product

class UpdateLowStockProducts(graphene.Mutation):
    class Arguments:
        pass

    updated_products = graphene.List(ProductType)
    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info):
        try:
            # Query products with stock less than 10
            low_stock_products = Product.objects.filter(stock__lt=10)
            
            # Update stock by incrementing by 10
            updated_products = []
            for product in low_stock_products:
                product.stock += 10
                product.save()
                updated_products.append(product)
            
            return UpdateLowStockProducts(
                updated_products=updated_products,
                success=True,
                message=f"Updated {len(updated_products)} low-stock products"
            )
            
        except Exception as e:
            return UpdateLowStockProducts(
                updated_products=[],
                success=False,
                message=f"Error updating low-stock products: {str(e)}"
            )

class Mutation(graphene.ObjectType):
    update_low_stock_products = UpdateLowStockProducts.Field()

# Make sure to include this mutation in your main Mutation class
# If you already have a Mutation class, add: update_low_stock_products = UpdateLowStockProducts.Field()
