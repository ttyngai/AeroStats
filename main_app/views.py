from django.shortcuts import render

# Add the following import
from django.http import HttpResponse
import requests

# Define the home view
def home(request):
  r = requests.get('https://opensky-network.org/api/states/all?lamin=43&lomin=-74&lamax=44&lomax=-73')
  print(r.text)  
  return render(request, 'home.html')