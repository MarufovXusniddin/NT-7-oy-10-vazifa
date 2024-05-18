from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg


# Create your models here.


class Category(models.Model):
    name = models.CharField(max_length=50, verbose_name="Kategoriya", unique=True)
    image = models.ImageField(upload_to='category/', null=True, blank=True)
    slug = models.SlugField(blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE,
                               null=True, blank=True,
                               related_name='subcategories')

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=150, verbose_name="Nomi")
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    price = models.FloatField()
    is_sale = models.IntegerField(default=0)
    image = models.ImageField(upload_to='products/')
    quantity = models.IntegerField(default=0)
    slug = models.SlugField(blank=True, null=True)

    def average_rating(self) -> float:
        return Rating.objects.filter(post=self).aggregate(Avg("rating"))["rating__avg"] or 0

    def __str__(self):
        return self.name

    @property
    def full_price(self):
        if self.is_sale > 0:
            price = self.price - (self.price * self.is_sale / 100)
        else:
            price = self.price
        return round(price, 2)

    @property
    def avg_rating(self):
        ratings = self.rating_set.all()
        if ratings:
            count = 0
            for rating in ratings:
                count += rating.rating
            return count / len(ratings)
        return 0

    @avg_rating.setter
    def avg_rating(self, value):
        # Bu metodni kerakmasa ham qoldiring
        pass


class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Product, on_delete=models.CASCADE)
    rating = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.post.header}: {self.rating}"


class Email(models.Model):
    email = models.EmailField(null=True, blank=True)


class Review(models.Model):
    text = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, blank=True)
    name = models.CharField(max_length=150, null=True)
    email = models.EmailField(null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=True)
    added = models.DateTimeField(auto_now_add=True)
    rating = models.IntegerField(default=0)


# ------------------------------------------------------------------------------------------------
class Customer(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    first_name = models.CharField(max_length=50, null=True, blank=True)
    last_name = models.CharField(max_length=50, null=True, blank=True)


class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True)
    created = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    @property
    def get_cart_total_price(self):
        order_products = self.orderproduct_set.all()
        total_price = [product.get_total_price for product in order_products]
        return sum(total_price)

    @property
    def get_cart_total_quantity(self):
        order_products = self.orderproduct_set.all()
        total_quantity = len(order_products)
        return total_quantity


class OrderProduct(models.Model):
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField(default=0)
    added = models.DateTimeField(auto_now_add=True, null=True)

    @property
    def get_total_price(self):
        total_price = self.quantity * self.product.price
        return total_price


class ShippingAddress(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True)
    address = models.CharField(max_length=255)
    region = models.CharField(max_length=150)
    city = models.CharField(max_length=255)
    zip_code = models.IntegerField()
    mobile = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)


class Region(models.Model):
    name = models.CharField(max_length=150)

    def __str__(self):
        return self.name


class City(models.Model):
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=150)