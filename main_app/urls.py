from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('update/<str:latMax>/<str:latMin>/<str:longMax>/<str:longMin>/', views.home_update, name='home_update'),

]