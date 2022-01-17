from fileinput import close
from random import sample
from django.shortcuts import render
import json
import math


# Add the following import
from django.http import HttpResponse
import requests

class Flight:
  def __init__(self, callsign, time_position, longitude, latitude, baro_altitude, on_ground, velocity, true_track, vertical_rate, distance_from_self):
    self.callsign = callsign
    self.time_position = time_position
    self.longitude = longitude
    self.latitude = latitude
    self.baro_altitude = baro_altitude
    self.on_ground = on_ground
    self.velocity = velocity
    self.true_track = true_track
    self.vertical_rate = vertical_rate
    self.distance_from_self = distance_from_self

# Define the home view
def home(request):
  # Fetch data and store in variable
  flight_data = requests.get('https://opensky-network.org/api/states/all?lamin=40&lomin=-80&lamax=48&lomax=-70').json()
  # Parsing data/Adding key to match sighting model
  sample_self_coordinates = {
    'long': -78,
    'lat': 44,
  }
  flight_data_parsed=[]
  for flight in flight_data['states']:
    # Parsing data/including distance from self
    long_delta = flight[5]-sample_self_coordinates['long']
    lat_delta = flight[6]-sample_self_coordinates['lat']
    distance_from_self = math.sqrt((long_delta*long_delta)+(lat_delta*lat_delta))

    # NEED TO DO: Should check if all data(at least the important ones) are present, or if in the sky

    obj = Flight(flight[1], flight[3], flight[5], flight[6], flight[7], flight[8], flight[9], flight[10], flight[11], distance_from_self)
    flight_data_parsed.append(obj)
  # Sort flight by distance from self
  sort_flight_by_distance = sorted(flight_data_parsed, key=lambda flight: flight.distance_from_self)

  # closest 100 flights
  closest_flights = sort_flight_by_distance[:100]
  # print((closest_flights))
  # for flight in closest_flights:
  #   print(flight.callsign)
  # slice list to take top 100(closest) flights
  return render(request, 'home.html', {'closest_flights': closest_flights})