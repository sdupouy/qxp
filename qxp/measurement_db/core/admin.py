from django.contrib import admin
from django.contrib.auth.models import User, Group

from .models import Chip, OpticalTable, Cooldown, ChipElement, ExperimentRun, Parameter, Measurement


admin.site.unregister(User)
admin.site.unregister(Group)

admin.site.register(Chip)
admin.site.register(OpticalTable)
admin.site.register(Cooldown)
admin.site.register(ChipElement)
admin.site.register(ExperimentRun)
admin.site.register(Parameter)
admin.site.register(Measurement)
