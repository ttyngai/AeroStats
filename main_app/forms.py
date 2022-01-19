from django.forms import ModelForm
from .models import Plane

class PlaneForm(ModelForm):
  class Meta:
    model = Plane
    fields = ['callsign']
