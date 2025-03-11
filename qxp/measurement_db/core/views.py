from django.views.generic import TemplateView, ListView, DetailView, CreateView
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.utils import timezone

from .models import Cooldown, ExperimentRun, Measurement, Parameter, Chip


class IndexView(TemplateView):
    template_name = "core/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if Cooldown.objects.exists():
            cooldown = Cooldown.objects.latest('datetime')
            context['cooldown'] = cooldown
            context['chip'] = cooldown.chip
            context['exp_runs'] = ExperimentRun.objects.filter(cooldown=context['cooldown']).order_by('-datetime')[:10]
            context['measurements'] = Measurement.objects.all()[:10]
        else:
            # if there is no cooldown yet, at least display the last chip
            context['chip'] = Chip.objects.last()
        return context


class CooldownListView(ListView):
    model = Cooldown


class CooldownDetailView(DetailView):
    model = Cooldown


class CooldownCreateView(CreateView):
    model = Cooldown
    fields = '__all__'


def warmup(request, pk):
    """ View to enable the warmup button. """
    if request.method == "POST":
        entry = get_object_or_404(Cooldown, id=pk)
        if not entry.warmup_datetime:
            entry.warmup_datetime = timezone.now()
            entry.save()
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False, "message": "Already warm"})
    return redirect("index")


class ChipListView(ListView):
    model = Chip


class ChipDetailView(DetailView):
    model = Chip


class ChipCreateView(CreateView):
    model = Chip
    fields = '__all__'


class ExperimentRunListView(ListView):
    model = ExperimentRun


class MeasurementListView(ListView):
    model = Measurement


class ParameterDetailView(DetailView):
    model = Parameter
