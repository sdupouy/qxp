import django_filters
from django import forms
from django_select2.forms import Select2Widget

from .models import Chip, Cooldown, Experiment, ExperimentRun, Measurement, Parameter


class ExperimentRunFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(
        field_name='datetime',
        lookup_expr='date',
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Date'
    )
    experiment = django_filters.ModelChoiceFilter(
        queryset=Experiment.objects.all(),
        widget=Select2Widget,
    )
    cooldown = django_filters.ModelChoiceFilter(
        queryset=Cooldown.objects.all(),
        widget=Select2Widget,
    )

    class Meta:
        model = ExperimentRun
        fields = ['date', 'experiment', 'cooldown', 'starred']


class MeasurementFilter(django_filters.FilterSet):
    parameter = django_filters.ModelChoiceFilter(
        queryset=Parameter.objects.all(),
        widget=Select2Widget,
    )
    chip = django_filters.ModelChoiceFilter(
        field_name='experiment_run__cooldown__chip',
        queryset=Chip.objects.all(),
        widget=Select2Widget,
        label='Chip'
    )

    class Meta:
        model = Measurement
        fields = ['parameter', 'chip']
