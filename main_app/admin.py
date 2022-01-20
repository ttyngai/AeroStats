from django.contrib import admin
from .models import Sighting, Plane, Passenger, Comment

# Register your models here.
admin.site.register(Sighting)
admin.site.register(Plane)
admin.site.register(Passenger)
admin.site.register(Comment)