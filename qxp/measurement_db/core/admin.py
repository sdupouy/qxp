from django.contrib import admin

from .models import Chip, OpticalTable, Cooldown, ChipElement, Parameter, Measurement


admin.site.register(Chip)
admin.site.register(OpticalTable)
admin.site.register(Cooldown)
admin.site.register(ChipElement)
admin.site.register(Parameter)
admin.site.register(Measurement)
