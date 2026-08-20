from django.views.generic.edit import CreateView, UpdateView, DeleteView
from random import sample
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Plane, Passenger, Comment
from .forms import PlaneForm, PassengerForm, CommentForm
import math
import string
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

AIRCRAFT_HEADERS = {'User-Agent': 'AeroStats/1.0'}
ADSB_BASE_URL = 'https://api.adsb.lol/v2'
EARTH_RADIUS_NM = 3440.065
FT_TO_M = 0.3048
KT_TO_MS = 0.514444
FT_PER_MIN_TO_MS = 0.00508
HEX_CHARS = set(string.hexdigits)
ADSB_MAX_RADIUS_NM = 250
ADSB_MAX_TILES = 12
ADSB_CACHE_TTL_S = 8
_adsb_tile_cache = {}


def _normalize_icao24(value):
  icao24 = (value or '').strip().lower().lstrip('~')
  if not icao24 or len(icao24) > 8 or any(ch not in HEX_CHARS for ch in icao24):
    return None
  return icao24


def _haversine_nm(lat1, lon1, lat2, lon2):
  phi1, phi2 = math.radians(lat1), math.radians(lat2)
  dphi = math.radians(lat2 - lat1)
  dlambda = math.radians(lon2 - lon1)
  a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
  return 2 * EARTH_RADIUS_NM * math.atan2(math.sqrt(a), math.sqrt(max(0, 1 - a)))


def _normalize_lon(lon):
  while lon > 180:
    lon -= 360
  while lon < -180:
    lon += 360
  return lon


def _lon_span(lomin, lomax):
  span = lomax - lomin
  if span < 0:
    span += 360
  return span


def _bbox_center(lamin, lomin, lamax, lomax):
  lat = (lamin + lamax) / 2
  if lomax >= lomin:
    lon = (lomin + lomax) / 2
  else:
    lon = _normalize_lon(lomin + _lon_span(lomin, lomax) / 2)
  return lat, lon


def _bbox_width_nm(lat, lomin, lomax):
  span = _lon_span(lomin, lomax)
  # ±180 is the same meridian, so a full-world span cannot use haversine.
  if span >= 359.5:
    return max(1.0, 2 * math.pi * EARTH_RADIUS_NM * math.cos(math.radians(lat)))
  return _haversine_nm(lat, lomin, lat, _normalize_lon(lomin + span))


def _bbox_tiles(lamin, lomin, lamax, lomax):
  """Cover a map bbox with adsb.lol point queries (max 250nm each)."""
  lat_c, lon_c = _bbox_center(lamin, lomin, lamax, lomax)
  corner_r = max(
    _haversine_nm(lat_c, lon_c, lamin, lomin),
    _haversine_nm(lat_c, lon_c, lamin, lomax),
    _haversine_nm(lat_c, lon_c, lamax, lomin),
    _haversine_nm(lat_c, lon_c, lamax, lomax),
  )
  if corner_r <= ADSB_MAX_RADIUS_NM:
    return [(lat_c, lon_c, max(1, int(math.ceil(corner_r))))]

  width_nm = _bbox_width_nm(lat_c, lomin, lomax)
  height_nm = _haversine_nm(lamin, lon_c, lamax, lon_c)
  spacing = ADSB_MAX_RADIUS_NM * 1.2
  nx = max(1, math.ceil(width_nm / spacing))
  ny = max(1, math.ceil(height_nm / spacing))
  if nx * ny > ADSB_MAX_TILES:
    aspect = width_nm / max(height_nm, 1)
    nx = max(1, min(ADSB_MAX_TILES, round(math.sqrt(ADSB_MAX_TILES * aspect))))
    ny = max(1, ADSB_MAX_TILES // nx)

  lat_step = (lamax - lamin) / ny
  lon_step = _lon_span(lomin, lomax) / nx
  tiles = []
  for j in range(ny):
    lat = lamin + (j + 0.5) * lat_step
    for i in range(nx):
      lon = _normalize_lon(lomin + (i + 0.5) * lon_step)
      tiles.append((lat, lon, ADSB_MAX_RADIUS_NM))
  return tiles


def _adsb_to_state(ac):
  icao24 = _normalize_icao24(ac.get('hex'))
  lat = ac.get('lat')
  lon = ac.get('lon')
  if not icao24 or lat is None or lon is None:
    return None

  alt = ac.get('alt_baro')
  on_ground = alt == 'ground'
  if on_ground:
    alt_m = 0
  else:
    if alt is None:
      alt = ac.get('alt_geom')
    try:
      alt_m = float(alt) * FT_TO_M if alt is not None else None
    except (TypeError, ValueError):
      alt_m = None

  gs = ac.get('gs')
  try:
    velocity = float(gs) * KT_TO_MS if gs is not None else None
  except (TypeError, ValueError):
    velocity = None

  vertical = ac.get('baro_rate')
  if vertical is None:
    vertical = ac.get('geom_rate')
  try:
    vertical_rate = float(vertical) * FT_PER_MIN_TO_MS if vertical is not None else 0
  except (TypeError, ValueError):
    vertical_rate = 0

  callsign = (ac.get('flight') or '').strip() or icao24
  origin = (ac.get('r') or 'n/a').strip() or 'n/a'
  track = ac.get('track') or 0
  return [
    icao24,
    callsign,
    origin,
    None,
    None,
    lon,
    lat,
    alt_m,
    on_ground,
    velocity,
    track,
    vertical_rate,
    None,
    None,
    ac.get('squawk'),
    False,
    0,
  ]


def _in_bbox(lat, lon, params):
  if not (params['lamin'] <= lat <= params['lamax']):
    return False
  lon = _normalize_lon(lon)
  lomin, lomax = params['lomin'], params['lomax']
  if lomin <= lomax:
    return lomin <= lon <= lomax
  return lon >= lomin or lon <= lomax


def _fetch_adsb_url(url):
  now = time.time()
  cached = _adsb_tile_cache.get(url)
  if cached and now - cached[0] < ADSB_CACHE_TTL_S:
    return cached[1]
  response = requests.get(url, timeout=8, headers=AIRCRAFT_HEADERS)
  response.raise_for_status()
  aircraft = response.json().get('ac') or []
  _adsb_tile_cache[url] = (now, aircraft)
  if len(_adsb_tile_cache) > 64:
    expired = [key for key, (ts, _) in _adsb_tile_cache.items() if now - ts >= ADSB_CACHE_TTL_S]
    for key in expired:
      _adsb_tile_cache.pop(key, None)
  return aircraft


def fetch_aircraft_states(params):
  """Return OpenSky-shaped state vectors from adsb.lol (OpenSky blocks AWS IPs)."""
  if 'icao24' in params:
    icaos = params['icao24'] if isinstance(params['icao24'], (list, tuple)) else [params['icao24']]
    urls = [f"{ADSB_BASE_URL}/icao/{','.join(icaos)}"]
    use_bbox = False
  else:
    tiles = _bbox_tiles(params['lamin'], params['lomin'], params['lamax'], params['lomax'])
    urls = [f"{ADSB_BASE_URL}/lat/{lat}/lon/{lon}/dist/{radius}" for lat, lon, radius in tiles]
    use_bbox = True

  aircraft = []
  errors = []
  if len(urls) == 1:
    try:
      aircraft = list(_fetch_adsb_url(urls[0]))
    except (requests.RequestException, ValueError) as exc:
      errors.append(exc)
  else:
    with ThreadPoolExecutor(max_workers=min(6, len(urls))) as pool:
      futures = {pool.submit(_fetch_adsb_url, url): url for url in urls}
      for future in as_completed(futures):
        try:
          aircraft.extend(future.result())
        except (requests.RequestException, ValueError) as exc:
          errors.append(exc)
  if not aircraft and errors:
    raise errors[0]

  states_by_icao = {}
  for ac in aircraft:
    state = _adsb_to_state(ac)
    if not state:
      continue
    if use_bbox and not _in_bbox(state[6], state[5], params):
      continue
    states_by_icao[state[0]] = state
  states = list(states_by_icao.values())
  return {'time': int(time.time()), 'states': states or None}


def opensky_states(request):
  """Proxy live aircraft so the browser is not blocked by CORS."""
  params = {}
  bbox_keys = ('lamin', 'lomin', 'lamax', 'lomax')
  if all(key in request.GET for key in bbox_keys):
    try:
      params = {key: float(request.GET[key]) for key in bbox_keys}
    except ValueError:
      return HttpResponseBadRequest('Invalid bounding box')
  elif 'icao24' in request.GET:
    icao24 = _normalize_icao24(request.GET.get('icao24'))
    if not icao24:
      return HttpResponseBadRequest('Invalid icao24')
    params = {'icao24': icao24}
  else:
    return HttpResponseBadRequest('Missing query parameters')

  try:
    return JsonResponse(fetch_aircraft_states(params))
  except (requests.RequestException, ValueError):
    return JsonResponse({'time': None, 'states': None, 'error': 'Unable to fetch aircraft data'}, status=502)

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
    icaos = [icao for icao in (_normalize_icao24(plane.icao24) for plane in watch_db) if icao]
    try:
      flight_data = fetch_aircraft_states({'icao24': icaos}) if icaos else {'states': None}
    except (requests.RequestException, ValueError):
      flight_data = {'states': None}
    if(flight_data['states'] != None):
      for flight in flight_data['states']:
        for plane in watch_db:
          if plane.icao24.lower() == flight[0]:
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
        if plane.icao24.lower() == f['icao24']:
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
    'mapbox_access_token': settings.MAPBOX_ACCESS_TOKEN,
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
  print('Plane user req',request.user.id)
  # plane = Plane.objects.get(icao24=request.POST['icao24'])
  plane = Plane.objects.filter(icao24=request.POST['icao24']).filter(user=request.user)[0]
  print('plane user plane',plane.user_id)

  form = PassengerForm(request.POST)
  #form.instance.user = request.user  # Add logged in user to form.

  if form.is_valid():

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
