from django.contrib import admin
from django.contrib.auth.models import User

from .models import Chip, OpticalTable, Cooldown, ExperimentRun, Parameter, Measurement, Experiment


# Hack to make the admin site available without having to create a superuser and log in
class PublicAdminSite(admin.AdminSite):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fake_superuser = None

    def has_permission(self, request):
        # Lazily create or get the fake superuser on the first request
        if self._fake_superuser is None:
            self._fake_superuser, created = User.objects.get_or_create(
                username='qxp_user',
                defaults={
                    'is_active': True,
                    'is_staff': True,
                    'is_superuser': True,
                }
            )
            if created:
                self._fake_superuser.set_unusable_password()
                self._fake_superuser.save()

        # Assign the fake superuser to the request
        request.user = self._fake_superuser
        return True


class ChipAdmin(admin.ModelAdmin):
    list_display = ['identifier', 'fab_date']


class OpticalTableAdmin(admin.ModelAdmin):
    list_display = ['datetime', 'rack_name']


class CooldownAdmin(admin.ModelAdmin):
    list_display = ['datetime', 'warmup_datetime', 'chip', 'number']


class ExperimentRunAdmin(admin.ModelAdmin):
    list_display = ['datetime', 'experiment', 'cooldown__chip', 'cooldown__number', 'starred']


class ParameterAdmin(admin.ModelAdmin):
    list_display = ['identifier', 'display_name']


class MeasurementAdmin(admin.ModelAdmin):
    list_display = ['parameter', 'experiment_run__datetime', 'value_uncertainty_unit']


class ExperimentAdmin(admin.ModelAdmin):
    list_display = ['identifier', 'display_name', 'module_name']


public_admin_site = PublicAdminSite(name='admin')

public_admin_site.register(Chip, ChipAdmin)
public_admin_site.register(OpticalTable, OpticalTableAdmin)
public_admin_site.register(Cooldown, CooldownAdmin)
public_admin_site.register(ExperimentRun, ExperimentRunAdmin)
public_admin_site.register(Parameter, ParameterAdmin)
public_admin_site.register(Measurement, MeasurementAdmin)
public_admin_site.register(Experiment, ExperimentAdmin)

public_admin_site.site_header = 'qxp administration'
public_admin_site.site_title = 'qxp'
