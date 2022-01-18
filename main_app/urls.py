from django.urls import path
from . import views

urlpatterns = [

    path('', views.home, name='home'),
    path('update/<str:latMax>/<str:latMin>/<str:longMax>/<str:longMin>/', views.home_update, name='home_update'),
    path('planes/create/', views.PlaneCreate.as_view(), name='planes_create'),
    path('planes/<int:pk>/update/', views.PlaneUpdate.as_view(), name='planes_update'),
    path('planes/<int:pk>/delete/', views.PlaneDelete.as_view(), name='planes_delete'),
]