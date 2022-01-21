from fileinput import close
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from random import sample
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Plane, Passenger, Comment
from .forms import PlaneForm, PassengerForm, CommentForm
import requests

def home(request):
  if(request.user.is_authenticated):
    watch_db = Plane.objects.filter(user = request.user)
  else:
    watch_db = None
# watch_db.passengers
  watchlist=[]
  login_form = AuthenticationForm()
  signup_form = UserCreationForm()
  passengers = Passenger.objects.all()
  comments = Comment.objects.all()

  if (watch_db and len(watch_db) != 0):
    query_url = f'https://opensky-network.org/api/states/all?icao24={watch_db[0].icao24}'

    for idx, plane in enumerate(watch_db):
      if (idx > 0):
        newString = f"&icao24={plane.icao24}"
        query_url += newString
    flight_data = requests.get(f'{query_url}').json()
    if(flight_data['states'] != None):
      for flight in flight_data['states']:
        for plane in watch_db:
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
    watchlist = sorted(watchlist, key=lambda flight: flight['icao24'])
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
  return render(request, 'home.html', {
    'watchlist': watch_db,
    # contains watch_db.passengers
    'login_form': login_form,
    'signup_form': signup_form,
    'watchlist_populated': watchlist,
    'passengers': passengers,
    'comments': comments,
  })


# class PlaneCreate(LoginRequiredMixin, CreateView):
#   model = Plane
#   fields = ['icao24']
#   def form_valid(self, form):
#     form.instance.user = self.request.user  # Add logged in user to form.
#     return super().form_valid(form)

class PlaneUpdate(LoginRequiredMixin, UpdateView):
  model = Plane
  fields = ['icao24']

class PlaneDelete(LoginRequiredMixin, DeleteView):
  model = Plane
  success_url = '/'

@login_required
def add_plane(request):
  # create a ModelForm instance using the data in the posted form
  planes = Plane.objects.filter(user = request.user)
  already_in_db = False
  for plane in planes:
    if plane.icao24 == request.POST['icao24']:
      already_in_db = True
  if already_in_db == False:
    form = PlaneForm(request.POST)
    form.instance.user = request.user  # Add logged in user to form.
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

@login_required
def add_comment(request):
  print(request.user)
  plane = Plane.objects.filter(icao24=request.POST['icao24']).filter(user=request.user)[0]
  form = CommentForm(request.POST)
  form.instance.user = request.user
  form.instance.plane_id = plane.id
  if form.is_valid():
    new_comment = form.save(commit=False)
    new_comment.save()
  return redirect('home')

class CommentUpdate(LoginRequiredMixin, UpdateView):
  model = Comment
  fields = ['content']
  success_url = "/"

class CommentDelete(LoginRequiredMixin, DeleteView):
  model = Comment

@login_required
def assoc_passenger(request, plane_id):
  Plane.objects.get(id=plane_id).passengers.add(request.POST['passenger_id'])
  # Well this is a poor user experiennce...
  return redirect('home')

@login_required
def create_passenger(request):
  plane = Plane.objects.get(icao24=request.POST['icao24'])
  print("Plane ID", plane.id)
  print("Passengers:", plane.passengers)
  form = PassengerForm(request.POST)
  #form.instance.user = request.user  # Add logged in user to form.
  print(form)
  if form.is_valid():
    print("Fom is valid!")
    new_passenger = form.save(commit=False)
    new_passenger.save()
    Plane.objects.get(id=plane.id).passengers.add(new_passenger.id)
  else:
    print("Form is not valid.")
  return redirect('home')

class PassengerCreate(LoginRequiredMixin, CreateView):
  model = Passenger
  fields = '__all__'

class PassengerUpdate(LoginRequiredMixin, UpdateView):
  model = Passenger
  fields = ['name']

class PassengerDelete(LoginRequiredMixin, DeleteView):
  model = Passenger

def signup(request):
  error_message = ''
  if request.method == 'POST':
    form = UserCreationForm(request.POST)
    if form.is_valid():
      # Handle good POSTs.
      user = form.save()  # Save user to DB.
      login(request, user)  # Log user in, FFS!
      return redirect('home')
    else:
      error_message = 'Invalid sign up - try again soon!'
  # Handle all GETs and bad POSTs.
  form = UserCreationForm()
  context = {'form': form, 'error_message': error_message}
  return redirect('home')
