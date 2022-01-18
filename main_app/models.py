from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Sighting(models.Model):
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

class Plane(models.Model):
  callsign = models.CharField(max_length = 8)

