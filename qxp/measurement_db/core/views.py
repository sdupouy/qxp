from django.db.models import Window, F
from django.db.models.functions import RowNumber
from django.views.generic import TemplateView, ListView, DetailView, CreateView
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.utils import timezone
from django.urls import reverse_lazy
from django.views.generic.edit import ModelFormMixin

from .models import Cooldown, ExperimentRun, Measurement, Parameter, Chip, OpticalTable, Experiment


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
            if OpticalTable.objects.exists():
                context['optical_table'] = OpticalTable.objects.latest('datetime')
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
    success_url = reverse_lazy('index')


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


class ChipDetailView(DetailView, ModelFormMixin):
    model = Chip
    slug_field = 'identifier'
    slug_url_kwarg = 'identifier'
    fields = ['comment']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # This query gets the latest measurement for each parameter measured on the chip
        latest_measurements = Measurement.objects.filter(
            experiment_run__cooldown__chip=self.get_object(),
        ).annotate(
            row_number=Window(
                expression=RowNumber(),
                partition_by=[F('parameter')],
                order_by=F('experiment_run__datetime').desc()
            )
        ).filter(
            row_number=1
        ).select_related('parameter', 'experiment_run').order_by('parameter')
        context['latest_measurements'] = latest_measurements
        return context

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        form.fields['comment'].widget.attrs.update({'rows': 3, 'cols': 40})
        return form

    def post(self, request, *args, **kwargs):
        # Get the object being displayed
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class ChipCreateView(CreateView):
    model = Chip
    fields = '__all__'
    success_url = reverse_lazy('index')


class OpticalTableCreateView(CreateView):
    model = OpticalTable
    fields = '__all__'
    success_url = reverse_lazy('index')


class ExperimentListView(ListView):
    model = Experiment


class ExperimentDetailView(DetailView):
    model = Experiment
    slug_field = 'identifier'
    slug_url_kwarg = 'identifier'


class ExperimentRunListView(ListView):
    model = ExperimentRun


class ExperimentRunDetailView(DetailView, ModelFormMixin):
    model = ExperimentRun
    fields = ['comment']

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        form.fields['comment'].widget.attrs.update({'rows': 3, 'cols': 40})
        return form

    def post(self, request, *args, **kwargs):
        # Get the object being displayed
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class MeasurementListView(ListView):
    model = Measurement


class ParameterDetailView(DetailView):
    model = Parameter
    slug_field = 'identifier'
    slug_url_kwarg = 'identifier'
