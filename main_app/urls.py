from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('update/<int:latMax>/<int:latMin>/<int:longMax>/<int:longMin>/', views.home_update, name='home_update'),

]