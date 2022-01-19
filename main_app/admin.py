from django.contrib import admin
from .models import Sighting, Plane

# Register your models here.
admin.site.register(Sighting)
admin.site.register(Plane)