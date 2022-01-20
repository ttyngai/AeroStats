from fileinput import close
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from random import sample
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from .models import Plane
from .forms import PlaneForm
import requests

def home(request):
  watch_db = Plane.objects.all()
  flight_data = requests.get('https://opensky-network.org/api/states/all').json()
  watchlist=[]
  for flight in flight_data['states']:
    # print(flight[0])
    for plane in watch_db:
      # print('db', plane.icao24)
      if plane.icao24 == flight[0]:  
        f = {
        'icao24': flight[0],
        'callsign': flight[1],
        'origin_country': flight[2],
        'longitude': flight[5],
        'latitude': flight[6],
        'altitude': flight[7],
        'on_ground': flight[8],
        'velocity': flight[9],
        'true_track': flight[10],
        'vertical_rate': flight[11]
        }
        watchlist.append(f)
  for plane in watch_db:
    not_online = True
    for f in watchlist:
      if plane.icao24 == f['icao24']:
        not_online = False
    if not_online:

      f = {
        'icao24': plane.icao24,
        'callsign': 'n/a',
        'origin_country': 'n/a',
        'longitude': 'n/a',
        'latitude': 'n/a',
        'altitude': 'n/a',
        'on_ground': 'n/a',
        'velocity': 'n/a',
        'true_track': 'n/a',
        'vertical_rate': 'n/a',
        }
      watchlist.append(f)

  login_form = AuthenticationForm()
  return render(request, 'home.html', { 'watchlist': watch_db, 'login_form': login_form ,'watchlist_populated': watchlist}, )
  

class PlaneCreate(CreateView):
  model = Plane
  fields = ['icao24']
  success_url = '/www.google.com'

class PlaneUpdate(UpdateView):
  model = Plane
  fields = ['icao24']

class PlaneDelete(DeleteView):
  model = Plane
  success_url = '/'

def add_plane(request):
  # create a ModelForm instance using the data in the posted form
  planes = Plane.objects.all()
  already_in_db = False
  for plane in planes:
    if plane.icao24 == request.POST['icao24']:
      print('Exists, Not adding')
      already_in_db = True
  if already_in_db == False:
    print('New, Adding')
    form = PlaneForm(request.POST)
    # validate the data
    if form.is_valid():
      new_plane = form.save(commit=False)
      new_plane.save()
  return redirect('home')

def planes_detail(request, plane_id):
  plane = Plane.objects.get(id=plane_id)
  return render(request, 'planes/detail.html', {
    'plane': plane
  })
