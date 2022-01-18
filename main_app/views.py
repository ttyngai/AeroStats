from fileinput import close
from random import sample
from django.shortcuts import render
import json
import math


# Add the following import
from django.http import HttpResponse
import requests

class Flight:
  def __init__(self, callsign, time_position, longitude, latitude, baro_altitude, on_ground, velocity, true_track, vertical_rate):
    self.callsign = callsign
    self.time_position = time_position
    self.longitude = longitude
    self.latitude = latitude
    self.baro_altitude = baro_altitude
    self.on_ground = on_ground
    self.velocity = velocity
    self.true_track = true_track
    self.vertical_rate = vertical_rate
    # self.distance_from_self = distance_from_self

# Define the home view
def home(request):

  # need to get  request from that refresh
  request.latmin = 35
  request.latmax = 39
  request.longmin = -123
  request.longmax = -116
  # Fetch data and store in variable

  flight_data = requests.get(f'https://opensky-network.org/api/states/all?lamin={request.latmin}&lomin={request.longmin}&lamax={request.latmax}&lomax={request.longmax}').json()
  # Parsing data/Adding key to match sighting model
  flight_data_parsed=[]
  for flight in flight_data['states']:
    obj = Flight(flight[1], flight[3], flight[5], flight[6], flight[7], flight[8], flight[9], flight[10], flight[11])
    flight_data_parsed.append(obj)
  # Sort flight by distance from self
 

  # closest 100 flights
  # closest_flights = flight_data_parsed
  # print((closest_flights))
  # for idx, flight in enumerate(closest_flights):
  #   print(idx, flight.distance_from_self)
  # slice list to take top 100(closest) flights
  return render(request, 'home.html', {'flight_data_parsed': flight_data_parsed})



def home_update(request, latMax, latMin, longMax, longMin):
  # need to get request from that refresh

  convert_lat_long(latMax)
  latMin = convert_lat_long(latMin)
  latMax = convert_lat_long(latMax)
  longMin = convert_lat_long(longMin)
  longMax = convert_lat_long(longMax)

  # Fetch data and store in variable
  flight_data = requests.get(f'https://opensky-network.org/api/states/all?lamin={latMin}&lomin={longMin}&lamax={latMax}&lomax={longMax}').json()
  # Parsing data/Adding key to match sighting model
  # selfLong = (longMin + longMax)/2
  # selfLat = (latMin + latMax)/2
  # sample_self_coordinates = {
  #   'lat': selfLat,
  #   'long': selfLong,
  # }
  flight_data_parsed=[]
  if flight_data['states']:
    for flight in flight_data['states']:
      # Parsing data/including distance from self
      
      # long_delta = flight[5]-sample_self_coordinates['long']
      # lat_delta = flight[6]-sample_self_coordinates['lat']
      # distance_from_self = math.sqrt((long_delta*long_delta)+(lat_delta*lat_delta))

      # NEED TO DO: Should check if all data(at least the important ones) are present, or if in the sky
      if flight[8] == False or flight[1] == None:
        obj = Flight(flight[1], flight[3], flight[5], flight[6], flight[7], flight[8], flight[9], flight[10], flight[11])
        flight_data_parsed.append(obj)
  # Sort flight by distance from self

  # closest 100 flights
  # closest_flights = sort_flight_by_distance
  # print((closest_flights))
  # for idx, flight in enumerate(closest_flights):
  #   print(idx, flight.distance_from_self)
  # slice list to take top 100(closest) flights
  return render(request, 'home.html', {'flight_data_parsed': flight_data_parsed})


def convert_lat_long(coord):
  if coord[0] == 'p':
    return int(coord[1:])/10000000000000000
  else:
    return int(coord[1:])/-10000000000000000
   
