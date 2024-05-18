from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import ListView
from .models import Category, Product, Rating, Email, Review
from .forms import LoginForm, RegisterForm, EmailForm, ReviewForm
from django.contrib.auth import login, logout
from django.contrib import messages
from django.db.models import Avg
import stripe
from django.urls import reverse

from .utils import CartAuthenticatedUser
from fruitable import settings


# Create your views here.


class ProductList(ListView):
    model = Product
    template_name = 'shop/index.html'
    context_object_name = 'products'
    extra_context = {
        'categories': Category.objects.filter(parent=None),
        'title': "Barcha Produclar",
        'all_products': Product.objects.all(),
        'form': EmailForm()

    }

    def get_queryset(self):
        return Product.objects.filter(is_sale=0)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request  # Request obyektini oling
        if request.user.is_authenticated:
            context['order_count'] = CartAuthenticatedUser(request).get_cart_info()['cart_total_quantity']
        return context


class AllProductList(ProductList):
    template_name = 'shop/all_products.html'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        products = Product.objects.exclude(is_sale=0)

        context['sale_products'] = products.order_by('-is_sale')[:3]
        high_avg_rating_product = Product.objects.annotate(avg_rating=Avg('rating__rating')).order_by(
            '-avg_rating').first()
        context['high_avg_rating'] = high_avg_rating_product
        request = self.request  # Request obyektini oling
        if request.user.is_authenticated:
            context['order_count'] = CartAuthenticatedUser(request).get_cart_info()['cart_total_quantity']
        return context


class ByIsSale(AllProductList):
    def get_queryset(self):
        return Product.objects.exclude(is_sale=0)


def detail(request, product_id):
    if request.user.is_authenticated:
        product = Product.objects.get(pk=product_id)
        context = {
            'categories': Category.objects.filter(parent=None),
            'product': product,
            'products': Product.objects.filter(category=product.category),
            'form': EmailForm(),
            'reviews': Review.objects.filter(product=product),
            'is_sale_products': Product.objects.exclude(is_sale=0).order_by('-is_sale')[:6],
            'order_count': CartAuthenticatedUser(request).get_cart_info()['cart_total_quantity']
        }
        rating = Rating.objects.filter(post=product, user=request.user.id).first()  # Requestdan foydalanish
        product.user_rating = rating.rating if rating else 0
        return render(request, 'shop/detail.html', context=context)
    else:
        return redirect('login')


def product_by_category(request, pk):
    category = Category.objects.get(pk=pk)
    products = Product.objects.filter(category=category)
    context = {
        'categories': Category.objects.filter(parent=None),
        'products': products,
        'all_products': Product.objects.all()
    }
    return render(request, 'shop/all_products.html', context=context)


def rate(request: HttpRequest, post_id: int, rating: int) -> HttpResponse:
    post = Product.objects.get(id=post_id)
    Rating.objects.filter(post=post, user=request.user).delete()
    post.rating_set.create(user=request.user, rating=rating)
    return detail(request, post_id)


def user_logout(request):
    """This is for logout"""

    logout(request)
    return redirect('login')


def user_login(request):
    """This is for login"""

    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "Login successfully!")
            return redirect('index')

        if form.errors:
            messages.error(request, "Check that the fields are correct!")

    form = LoginForm()
    context = {
        'form': form,
        'title': 'Sign in'
    }
    return render(request, 'shop/login.html', context=context)


def user_register(request):
    """This is for sing up"""

    if request.method == 'POST':
        form = RegisterForm(data=request.POST)
        if form.is_valid():
            form.save()
            messages.info(request, "You can log in by entering your username and password.")
            return redirect('login')

        if form.errors:
            messages.error(request, "Check that the fields are correct!")

    form = RegisterForm()
    context = {
        'form': form,
        'title': 'Sign up'
    }
    return render(request, 'shop/register.html', context=context)


def user_email(request):
    form = EmailForm(data=request.POST)
    form.save()
    return redirect('index')


def save_review(request, product_pk):
    if request.user.is_authenticated:
        print(request.POST, "*" * 300)
        form = ReviewForm(data=request.POST)
        if form.is_valid():
            print(request.POST, "+" * 300)
            product = Product.objects.get(pk=product_pk)
            review = form.save(commit=False)
            review.product = product
            review.author = request.user
            print(review, "-" * 300)
            review.save()
            messages.success(request, "Feedback has been sent!")
            return redirect('detail', product_id=product_pk)

        messages.error(request, "Fields are invalid!")
        return redirect('detail', product_id=product_pk)
    else:
        messages.warning(request, "Please login first to comment!")
        return redirect('login')


def cart(request):
    if request.user.is_authenticated:
        cart_info = CartAuthenticatedUser(request).get_cart_info()

        context = {
            'order_products': cart_info['order_products'],
            'cart_total_price': cart_info['cart_total_price'],
            'order_count': cart_info['cart_total_quantity'],

        }
        return render(request, 'shop/cart.html', context=context)
    else:
        return redirect('login')


def to_cart(request: HttpRequest, product_id, action):
    if request.user.is_authenticated:
        CartAuthenticatedUser(request, product_id=product_id, action=action)
        page = request.META.get('HTTP_REFERER')
        return redirect(page)

    else:
        return redirect('login')


def create_checkout_sessions(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    user_cart = CartAuthenticatedUser(request)
    cart_info = user_cart.get_cart_info()
    total_price = cart_info['cart_total_price']
    total_quantity = cart_info['cart_total_quantity']
    session = stripe.checkout.Session.create(
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': 'Online shop products'
                },
                'unit_amount': int(total_price * 100)
            },
            'quantity': total_quantity
        }],
        mode='payment',
        success_uri=request.build_absolute_uri(reverse("Borish url")),
        cancel_uri=request.build_absolute_uri(reverse("Borish url"))
    )
    return redirect(session.url, 303)
