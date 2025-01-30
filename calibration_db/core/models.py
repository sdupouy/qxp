from django.db import models


class Chip(models.Model):
    name = models.CharField(max_length=255, unique=True)
    picture = models.ImageField(upload_to='chips/', null=True, blank=True)
    comment = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Run(models.Model):
    date = models.DateField()
    chip = models.ForeignKey(Chip, on_delete=models.PROTECT)
    cooldown = models.IntegerField()
    cabling = models.ImageField(upload_to='cablings/', null=True, blank=True)
    comment = models.TextField(blank=True)

    def __str__(self):
        return self.date

class Calibration(models.Model):
    name = models.CharField(max_length=255)
    run = models.ForeignKey(Run, on_delete=models.PROTECT)
    value = models.FloatField()
    unit = models.CharField(max_length=30, blank=True)
    comment = models.TextField(blank=True)
    datetime = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} @ {self.datetime}"
