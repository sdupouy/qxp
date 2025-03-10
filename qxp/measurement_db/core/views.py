from django.views.generic import TemplateView, ListView, DetailView

from .models import Cooldown, ExperimentRun, Measurement, Parameter


class IndexView(TemplateView):
    template_name = "core/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if Cooldown.objects.exists():
            context['cooldown'] = Cooldown.objects.latest('datetime')
            context['exp_runs'] = ExperimentRun.objects.filter(cooldown=context['cooldown']).order_by('-datetime')[:10]
            context['measurements'] = Measurement.objects.all()[:10]
        return context


class CooldownListView(ListView):
    model = Cooldown


class CooldownDetailView(DetailView):
    model = Cooldown


class ExperimentRunListView(ListView):
    model = ExperimentRun


class MeasurementListView(ListView):
    model = Measurement


class ParameterDetailView(DetailView):
    model = Parameter
