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
    rack_name = models.CharField(max_length=255)
    cabling = models.ImageField(upload_to='optical_tables/', null=True, blank=True)
    comment = models.TextField(blank=True)

    def __str__(self):
        return f'{self.rack_name} ({str(self.datetime)})'


class Cooldown(models.Model):
    number = models.PositiveIntegerField()
    datetime = models.DateTimeField(default=timezone.now)
    chip = models.ForeignKey(Chip, on_delete=models.PROTECT)
    cabling = models.ImageField(upload_to='fridge_cablings/', null=True, blank=True)
    comment = models.TextField(blank=True)

    def __str__(self):
        return f'{self.chip.name} # {self.number} ({str(self.datetime)})'

    class Meta:
        unique_together = [['number', 'chip']]


class ChipElement(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class ExperimentRun(models.Model):
    name = models.CharField(max_length=255)
    datetime = models.DateTimeField(default=timezone.now)
    cooldown = models.ForeignKey(Cooldown, on_delete=models.PROTECT)
    optical_table = models.ForeignKey(OpticalTable, on_delete=models.PROTECT)
    data_path = models.CharField(max_length=255)
    comment = models.TextField(blank=True)

    def __str__(self):
        return f'{self.name} of {self.cooldown.chip.name} ({str(self.datetime)})'


class Parameter(models.Model):
    name = models.CharField(max_length=255, unique=True)
    unit = models.CharField(max_length=255, blank=True)
    chip_elements = models.ManyToManyField(ChipElement, blank=True)
    latex_notation = models.CharField(max_length=255, null=True, blank=True)
    comment = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Measurement(models.Model):
    parameter = models.ForeignKey(Parameter, on_delete=models.PROTECT)
    value = models.FloatField()
    uncertainty = models.FloatField(null=True, blank=True)
    experiment_run = models.ForeignKey(ExperimentRun, on_delete=models.PROTECT)
    comment = models.TextField(blank=True)

    def __str__(self):
        return f"{self.parameter.name} @ {self.experiment_run.datetime}"
