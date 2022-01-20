from django.urls import path
from . import views

urlpatterns = [
  path('', views.home, name='home'),
  path('planes/create/', views.add_plane, name='planes_create'),
  path('planes/<int:plane_id>/', views.planes_detail, name='detail'),
  path('planes/<int:pk>/update/', views.PlaneUpdate.as_view(), name='planes_update'),
  path('planes/<int:pk>/delete/', views.PlaneDelete.as_view(), name='planes_delete'),
  path('planes/<int:plane_id>/assoc_passenger/', views.assoc_passenger, name='assoc_passenger'),
  path('passengers/create/', views.create_passenger, name='passengers_create'),
  path('passengers/<int:pk>/update/', views.PassengerUpdate.as_view(), name='passengers_update'),
  path('passengers/<int:pk>/delete/', views.PassengerDelete.as_view(), name='passengers_delete'),
  path('comments/create/', views.add_comment, name='comments_create'),
  path('comments/<int:pk>/update/', views.CommentUpdate.as_view(), name='comments_update'),
  path('comments/<int:pk>/delete/', views.CommentDelete.as_view(), name='comments_delete'),
]