from django.shortcuts import render,redirect,get_object_or_404
from django.http import JsonResponse
import json
import datetime
from .models import *  
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.views.generic.detail import DetailView
from .models import Product
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from .models import Customer, Product, Order, OrderItem, ShippingAddress
import datetime
import json
import random


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        redirect_authenticated_user = True
        if user is not None:
            # Ensure the customer object exists when a user logs in
            Customer.objects.get_or_create(user=user)
            login(request, user)
            return redirect('store')
        else:
            messages.error(request, 'Invalid username or password')
    return render(request, 'store/login.html')

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create a corresponding customer when a new user registers
            Customer.objects.create(user=user)
            login(request, user)

            messages.success(request, 'Account created successfully. You can now log in.')
            return redirect('store')
        else:
            messages.error(request, 'Error in form submission')
    else:
        form = UserCreationForm()
    return render(request, 'store/register.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('store')

def get_customer(user):
    """
    Helper function to get or create a Customer for the authenticated user.
    """
    if not hasattr(user, 'customer'):
        return Customer.objects.create(user=user)
    return user.customer

def store(request):
    if request.user.is_authenticated:
        customer = get_customer(request.user)
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
        cartItems = order.get_cart_items
    else:
        # Create empty cart for non-logged-in users
        items = []
        order = {'get_cart_total': 0, 'get_cart_items': 0}
        cartItems = order['get_cart_items']

    products = Product.objects.all()
    context = {'products': products, 'cartItems': cartItems}
    return render(request, 'store/store.html', context)

def product_detail(request, product_id):
    # Fetch the product based on the provided ID or return 404 if not found
    product = get_object_or_404(Product, id=product_id)
    
    # Handle cart logic for authenticated and non-authenticated users
    if request.user.is_authenticated:
        customer = get_customer(request.user)
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
        cartItems = order.get_cart_items
    else:
        # Create empty cart for non-logged-in users
        items = []
        order = {'get_cart_total': 0, 'get_cart_items': 0}
        cartItems = order['get_cart_items']
    
    # Pass the product and cart info to the context
    context = {
        'product': product,
        'cartItems': cartItems
    }

    return render(request, 'store/product_detail.html', context)

def cart(request):
    if request.user.is_authenticated:
        customer = get_customer(request.user)
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
        cartItems = order.get_cart_items
    else:
        # Handle non-logged-in users with cookies
        try:
            cart = json.loads(request.COOKIES['cart'])
        except KeyError:
            cart = {}

        items = []
        order = {'get_cart_total': 0, 'get_cart_items': 0, 'shipping': False}
        cartItems = order['get_cart_items']

        for i in cart:
            try:
                cartItems += cart[i]['quantity']
                product = Product.objects.get(id=i)
                total = product.price * cart[i]['quantity']
                order['get_cart_total'] += total
                order['get_cart_items'] += cart[i]['quantity']
                item = {
                    'id': product.id,
                    'product': {'id': product.id, 'name': product.name,'description': product.description, 'price': product.price, 'imageURL': product.imageURL},
                    'quantity': cart[i]['quantity'],
                    'digital': product.digital,
                    'get_total': total,
                }
                items.append(item)
                if not product.digital:
                    order['shipping'] = True
            except:
                pass

    context = {'items': items, 'order': order, 'cartItems': cartItems}
    return render(request, 'store/cart.html', context)

def checkout(request):
    if request.user.is_authenticated:
        customer = get_customer(request.user)
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
        cartItems = order.get_cart_items
    else:
        # Create empty cart for non-logged-in users
        items = []
        order = {'get_cart_total': 0, 'get_cart_items': 0, 'shipping': False}
        cartItems = order['get_cart_items']

    context = {'items': items, 'order': order, 'cartItems': cartItems}
    return render(request, 'store/checkout.html', context)

def updateItem(request):
	data = json.loads(request.body)
	productId = data['productId']
	action = data['action']
	print('Action:', action)
	print('Product:', productId)

	customer = request.user.customer
	product = Product.objects.get(id=productId)
	order, created = Order.objects.get_or_create(customer=customer, complete=False)

	orderItem, created = OrderItem.objects.get_or_create(order=order, product=product)

	if action == 'add':
		orderItem.quantity = (orderItem.quantity + 1)
	elif action == 'remove':
		orderItem.quantity = (orderItem.quantity - 1)

	orderItem.save()

	if orderItem.quantity <= 0:
		orderItem.delete()

	return JsonResponse('Item was added', safe=False)

def mock_payment_api(total_amount):
    """
    Simulate a mock payment API that randomly processes the payment.
    Returns 'success' if payment succeeds, 'failure' if it fails.
    """
    # Simulate a payment with a random outcome
    if random.choice([True, False]):
        return 'success'
    else:
        return 'failure'

def processOrder(request):
    transaction_id = datetime.datetime.now().timestamp()
    data = json.loads(request.body)

    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        total = float(data['form']['total'])
        order.transaction_id = transaction_id

        # Simulate payment
        payment_status = mock_payment_api(total)

        if payment_status == 'success':
            if total == order.get_cart_total:
                order.complete = True
                order.save()

                if order.shipping:
                    # Create a shipping address if the order requires shipping
                    ShippingAddress.objects.create(
                        customer=customer,
                        order=order,
                        address=data['shipping']['address'],
                        city=data['shipping']['city'],
                        state=data['shipping']['state'],
                        zipcode=data['shipping']['zipcode'],
                    )

                return JsonResponse({'status': 'success', 'message': 'Payment processed successfully!'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Order total does not match payment amount.'})
        else:
            # Simulate a failure in the payment processing
            return JsonResponse({'status': 'error', 'message': 'Payment failed. Please try again.'})

    else:
        return JsonResponse({'status': 'error', 'message': 'User not logged in.'})
