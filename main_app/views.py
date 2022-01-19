from fileinput import close
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from random import sample
from django.shortcuts import render, redirect

from .models import Plane
from .forms import PlaneForm

def home(request):
  return render(request, 'home.html')

class PlaneCreate(CreateView):
  model = Plane
  fields = ['callsign']
  success_url = '/www.google.com'

class PlaneUpdate(UpdateView):
  model = Plane
  fields = ['callsign']

class PlaneDelete(DeleteView):
  model = Plane
  success_url = '/planes/'

def add_plane(request):
  # create a ModelForm instance using the data in the posted form
  print('hello')
  print(request)

  form = PlaneForm(request.POST)
  # validate the data
  if form.is_valid():
    new_plane = form.save(commit=False)
    new_plane.save()
  return redirect('home')