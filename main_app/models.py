from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse

# Create your models here.
class Passenger(models.Model):
  name = models.CharField(max_length=50)

  def __str__(self):
    return self.name


class Sighting(models.Model):
  icao24 = models.CharField(max_length = 8)
  callsign = models.CharField(max_length=8)
  time_position = models.IntegerField()
  longitude = models.FloatField()
  latitude = models.FloatField()
  baro_altitude = models.FloatField()
  on_ground = models.BooleanField()
  velocity = models.FloatField()
  true_track = models.FloatField()
  vertical_rate = models.FloatField()
  user = models.ForeignKey(User, on_delete=models.CASCADE)

  def __str__(self):
    return self.icao24

class Plane(models.Model):
  icao24 = models.CharField(max_length = 8)
  passengers = models.ManyToManyField(Passenger)
  user = models.ForeignKey(User, on_delete=models.CASCADE)

  def __str__(self):
    return self.icao24

