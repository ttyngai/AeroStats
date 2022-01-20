from django.forms import ModelForm
from .models import Comment, Plane, Passenger

class PlaneForm(ModelForm):
  class Meta:
    model = Plane
    fields = ['icao24']

class PassengerForm(ModelForm):
  class Meta:
    model = Passenger
    fields = ['name']

class CommentForm(ModelForm):
  class Meta:
    model = Comment
    fields = ['content']