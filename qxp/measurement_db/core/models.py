from django.db import models
from django.utils import timezone


class Chip(models.Model):
    name = models.CharField(max_length=255, unique=True)
    picture = models.ImageField(upload_to='chip_pictures/', null=True, blank=True)
    comment = models.TextField(blank=True)

    def __str__(self):
        return self.name


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

    def __str__(self):
        return f'{self.chip.name} # {self.number} ({str(self.datetime)})'

    class Meta:
        unique_together = [['number', 'chip']]
        ordering = ['-datetime']


class Experiment(models.Model):
    identifier = models.CharField(max_length=255, unique=True)
    display_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    module_name = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.identifier


class ExperimentRun(models.Model):
    datetime = models.DateTimeField(default=timezone.now, unique=True)
    experiment = models.ForeignKey(Experiment, on_delete=models.PROTECT)
    cooldown = models.ForeignKey(Cooldown, on_delete=models.PROTECT)
    optical_table = models.ForeignKey(OpticalTable, on_delete=models.PROTECT)
    data_path = models.CharField(max_length=255)
    comment = models.TextField(blank=True)
    starred = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.experiment.identifier} of {self.cooldown.chip.name} ({str(self.datetime)})'

    class Meta:
        ordering = ['-datetime']


class Parameter(models.Model):
    identifier = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255, blank=True)
    unit = models.CharField(max_length=255, blank=True)
    latex_notation = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(blank=True)

    @property
    def display_name_or_identifier(self):
        return self.display_name or self.identifier

    def __str__(self):
        return self.identifier


class Measurement(models.Model):
    parameter = models.ForeignKey(Parameter, on_delete=models.PROTECT)
    value = models.FloatField()
    uncertainty = models.FloatField(null=True, blank=True)
    experiment_run = models.ForeignKey(ExperimentRun, on_delete=models.PROTECT)
    comment = models.TextField(blank=True)

    def __str__(self):
        return f"{self.parameter.identifier} @ {self.experiment_run.datetime}"

    class Meta:
        ordering = ['experiment_run']
