from django.urls import path
from . import views

urlpatterns = [

    path('', views.home, name='home'),
    path('planes/create/', views.add_plane, name='planes_create'),
    path('planes/<int:pk>/update/', views.PlaneUpdate.as_view(), name='planes_update'),
    path('planes/<int:pk>/delete/', views.PlaneDelete.as_view(), name='planes_delete'),
]