from django.forms import ModelForm
from .models import Plane, Passenger

class PlaneForm(ModelForm):
  class Meta:
    model = Plane
    fields = ['icao24']

class PassengerForm(ModelForm):
  class Meta:
    model = Passenger
    fields = ['name']
