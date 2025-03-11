from django import forms
from django_select2 import forms as s2forms

from . import models


class ChipWidget(s2forms.ModelSelect2Widget):
    search_fields = ["name__icontains"]


class CooldownForm(forms.ModelForm):
    class Meta:
        model = models.Cooldown
        fields = "__all__"
        widgets = {
            "chip": ChipWidget,
        }
