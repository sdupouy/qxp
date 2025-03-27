from datetime import date

from django.db import models
from django.urls import reverse
from django.utils import timezone


class Chip(models.Model):
    identifier = models.SlugField(max_length=255, unique=True)
    fab_date = models.DateField(default=date.today)
    picture = models.ImageField(upload_to='chip_pictures/', null=True, blank=True)
    comment = models.TextField(blank=True)

    def get_absolute_url(self):
        return reverse('chip-detail', kwargs={'identifier': self.identifier})

    def __str__(self):
        return self.identifier

    class Meta:
        ordering = ['-fab_date', 'identifier']


class OpticalTable(models.Model):
    datetime = models.DateTimeField(default=timezone.now)
    rack_name = models.CharField(max_length=255, blank=True)
    cabling = models.ImageField(upload_to='optical_tables/', null=True, blank=True)
    comment = models.TextField(blank=True)

    def __str__(self):
        return f'{self.rack_name} ({str(self.datetime)})'

    class Meta:
        ordering = ['-datetime']


class Cooldown(models.Model):
    number = models.PositiveIntegerField()
    datetime = models.DateTimeField(default=timezone.now)
    warmup_datetime = models.DateTimeField(null=True, blank=True)
    chip = models.ForeignKey(Chip, on_delete=models.PROTECT)
    cabling = models.ImageField(upload_to='fridge_cablings/', null=True, blank=True)
    comment = models.TextField(blank=True)

    @property
    def is_cold(self):
        return self.warmup_datetime is None

    def get_absolute_url(self):
        return reverse('cooldown-detail', kwargs={'pk': self.pk})

    def __str__(self):
        return f'{self.chip.identifier} # {self.number} ({str(self.datetime)})'

    class Meta:
        unique_together = [['number', 'chip']]
        ordering = ['-datetime']


class Experiment(models.Model):
    identifier = models.SlugField(max_length=255, unique=True)
    display_name = models.CharField(max_length=255)
    module_name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    def get_absolute_url(self):
        return reverse('experiment-detail', kwargs={'identifier': self.identifier})

    def __str__(self):
        return self.identifier

    class Meta:
        ordering = ['identifier']


class ExperimentRun(models.Model):
    datetime = models.DateTimeField(default=timezone.now, unique=True)
    datetime_end = models.DateTimeField(default=timezone.now)
    experiment = models.ForeignKey(Experiment, on_delete=models.PROTECT)
    cooldown = models.ForeignKey(Cooldown, on_delete=models.PROTECT)
    optical_table = models.ForeignKey(OpticalTable, on_delete=models.PROTECT)
    data_path = models.CharField(max_length=255)
    comment = models.TextField(blank=True)
    starred = models.BooleanField(default=False)

    @property
    def duration(self):
        return self.datetime_end - self.datetime

    def get_absolute_url(self):
        return reverse('experiment-run-detail', kwargs={'pk': self.pk})

    def __str__(self):
        return f'{self.experiment.identifier} of {self.cooldown.chip.identifier} ({str(self.datetime)})'

    class Meta:
        ordering = ['-datetime']


class Parameter(models.Model):
    identifier = models.SlugField(max_length=255, unique=True)
    display_name = models.CharField(max_length=255, blank=True)
    unit = models.CharField(max_length=255, blank=True)
    latex_notation = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    @property
    def display_name_or_identifier(self):
        return self.display_name or self.identifier

    def get_absolute_url(self):
        return reverse('parameter-detail', kwargs={'identifier': self.identifier})

    def __str__(self):
        return self.identifier

    class Meta:
        ordering = ['identifier']


class Measurement(models.Model):
    parameter = models.ForeignKey(Parameter, on_delete=models.PROTECT)
    value = models.FloatField()
    uncertainty = models.FloatField(null=True, blank=True)
    experiment_run = models.ForeignKey(ExperimentRun, on_delete=models.PROTECT)

    @property
    def value_uncertainty_unit(self):
        stripped_value = f'{self.value:.3f}'.rstrip('0').rstrip('.')
        unit = ''
        if self.parameter.unit:
            unit = f' {self.parameter.unit}'
        if self.uncertainty:
            stripped_uncertainty = f'{self.uncertainty:.3f}'.rstrip('0').rstrip('.')
            return f'{stripped_value} ± {stripped_uncertainty}{unit}'
        else:
            return f'{stripped_value}{unit}'

    def __str__(self):
        return f"{self.parameter.identifier} ({self.experiment_run.datetime})"

    class Meta:
        unique_together = [['parameter', 'experiment_run']]
        ordering = ['experiment_run']
