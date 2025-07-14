import django_filters
from django import forms

from .models import ExperimentRun, Measurement, Chip, Experiment


class ExperimentRunFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(
        field_name='datetime',
        lookup_expr='date',
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Date'
    )

    class Meta:
        model = ExperimentRun
        fields = ['date', 'experiment', 'cooldown', 'starred']


class MeasurementFilter(django_filters.FilterSet):
    chip = django_filters.ModelChoiceFilter(
        field_name='experiment_run__cooldown__chip',
        queryset=Chip.objects.all(),
        label='Chip'
    )

    class Meta:
        model = Measurement
        fields = ['parameter', 'chip']
