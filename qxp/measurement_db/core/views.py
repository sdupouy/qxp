from pathlib import Path

from django.db.models import Window, F
from django.db.models.functions import RowNumber
from django.views.generic import TemplateView, ListView, DetailView, CreateView, DeleteView
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse, FileResponse, Http404, HttpResponseForbidden
from django.utils import timezone
from django.urls import reverse_lazy
from django.views.generic.edit import ModelFormMixin
from django_filters.views import FilterView

from qxp.utils.save import load_dict_from_hdf5, make_json_serializable, figure_path_from_data_path, \
    debug_script_path_from_data_path, delete_file
from qxp.config import ALLOW_DELETE_EXPRUN, STORAGE_PATH
from .models import Cooldown, ExperimentRun, Measurement, Parameter, Chip, OpticalTable, Experiment
from .filters import ExperimentRunFilter, MeasurementFilter


class IndexView(TemplateView):
    template_name = "core/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if Cooldown.objects.exists():
            cooldown = Cooldown.objects.latest('datetime')
            context['cooldown'] = cooldown
            context['chip'] = cooldown.chip
            context['exp_runs'] = ExperimentRun.objects.filter(cooldown=context['cooldown']).order_by('-datetime')[:10]
            context['measurements'] = Measurement.objects.filter(is_valid=True)[:10]
            if OpticalTable.objects.exists():
                context['optical_table'] = OpticalTable.objects.latest('datetime')
        else:
            # if there is no cooldown yet, at least display the last chip
            context['chip'] = Chip.objects.last()
        return context


class CooldownDetailView(DetailView, ModelFormMixin):
    model = Cooldown
    fields = ['comment']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # This query gets the latest measurement for each parameter measured on the chip
        latest_measurements = Measurement.objects.filter(
            experiment_run__cooldown=self.get_object(),
            is_valid=True
        ).annotate(
            row_number=Window(
                expression=RowNumber(),
                partition_by=[F('parameter')],
                order_by=F('experiment_run__datetime').desc()
            )
        ).filter(
            row_number=1
        ).select_related('parameter', 'experiment_run').order_by('parameter')
        # Number of experiment runs
        exp_run_count = ExperimentRun.objects.filter(cooldown=self.get_object()).count()
        context['latest_measurements'] = latest_measurements
        context['exp_run_count'] = exp_run_count
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
            is_valid=True
        ).annotate(
            row_number=Window(
                expression=RowNumber(),
                partition_by=[F('parameter')],
                order_by=F('experiment_run__datetime').desc()
            )
        ).filter(
            row_number=1
        ).select_related('parameter', 'experiment_run').order_by('parameter')
        # Number of experiment runs
        exp_run_count = ExperimentRun.objects.filter(cooldown__chip=self.get_object()).count()
        context['latest_measurements'] = latest_measurements
        context['exp_run_count'] = exp_run_count
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


class ExperimentRunListView(FilterView):
    model = ExperimentRun
    filterset_class = ExperimentRunFilter

    def get_queryset(self):
        return super().get_queryset().select_related('experiment', 'cooldown__chip')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        view_mode = self.request.GET.get('view', 'standard')
        if view_mode not in {'standard', 'image'}:
            view_mode = 'standard'

        def query_string_for(mode):
            query = self.request.GET.copy()
            query['view'] = mode
            return query.urlencode()

        context.update({
            'view_mode': view_mode,
            'standard_view_query': query_string_for('standard'),
            'image_view_query': query_string_for('image'),
            'reset_query': f'view={view_mode}',
        })
        return context


class ExperimentRunDetailView(DetailView, ModelFormMixin):
    model = ExperimentRun
    fields = ['comment']

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        form.fields['comment'].widget.attrs.update({'rows': 2, 'cols': 60})
        return form

    def post(self, request, *args, **kwargs):
        # Get the object being displayed
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["allow_delete"] = ALLOW_DELETE_EXPRUN
        return context


def exp_run_config(request, pk):
    """ Fetch the configuration of an experiment run from the saved HDF5 file. """
    entry = get_object_or_404(ExperimentRun, id=pk)
    try:
        path = Path(STORAGE_PATH) / entry.data_path
        config_dict = load_dict_from_hdf5(
            path,
            keys=['exp_parameters', 'exp_config', 'instruments_config', 'qua_config']
        )
        config_dict = make_json_serializable(config_dict)  # convert numpy types to native python types
        return JsonResponse({"success": True, "config": config_dict})
    except FileNotFoundError as e:
        return JsonResponse({"success": False, "message": str(e)})


def exp_run_code(request, pk):
    """ Fetch the source code of an experiment run from the saved HDF5 file. """
    entry = get_object_or_404(ExperimentRun, id=pk)
    try:
        path = Path(STORAGE_PATH) / entry.data_path
        code = load_dict_from_hdf5(path, keys=['experiment_code'])['experiment_code']
        return JsonResponse({"success": True, "code": code})
    except FileNotFoundError as e:
        return JsonResponse({"success": False, "message": str(e)})


def exp_run_figure(request, pk):
    """ Fetch the saved figure of an experiment run. """
    entry = get_object_or_404(ExperimentRun, id=pk)
    rel_image_path = figure_path_from_data_path(entry.data_path)
    image_path = Path(STORAGE_PATH) / rel_image_path
    if not image_path.exists():
        raise Http404(f"Image not found at path {image_path}")
    return FileResponse(open(image_path, 'rb'), content_type='image/png')


def exp_run_toggle_star(request, pk):
    """ View to toggle the starred field of an ExperimentRun. """
    if request.method == "POST":
        entry = get_object_or_404(ExperimentRun, id=pk)
        entry.starred = not entry.starred
        entry.save()
        return JsonResponse({"success": True, "starred": entry.starred})
    return redirect("index")


class ExperimentRunDeleteView(DeleteView):
    """ View to delete an experiment run. """
    model = ExperimentRun
    success_url = reverse_lazy("index")

    def form_valid(self, form):
        if not ALLOW_DELETE_EXPRUN:
            return HttpResponseForbidden("This object cannot be deleted because ALLOW_DELETE_EXPRUN is set to False in the config.")

        # Delete the data, debug script and figure
        data_path = Path(STORAGE_PATH) / self.object.data_path
        debug_script_path = debug_script_path_from_data_path(data_path)
        figure_path = figure_path_from_data_path(data_path)
        delete_file(data_path)
        delete_file(debug_script_path)
        delete_file(figure_path)

        return super().form_valid(form)


class MeasurementListView(FilterView):
    model = Measurement
    filterset_class = MeasurementFilter

    def get_queryset(self):
        return Measurement.objects.filter(is_valid=True)


def measurement_toggle_is_valid(request, pk):
    """ View to toggle the starred field of an ExperimentRun. """
    if request.method == "POST":
        entry = get_object_or_404(Measurement, id=pk)
        entry.is_valid = not entry.is_valid
        entry.save()
        return JsonResponse({"success": True, "is_valid": entry.is_valid})
    return redirect("index")


class ParameterDetailView(DetailView):
    model = Parameter
    slug_field = 'identifier'
    slug_url_kwarg = 'identifier'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['valid_measurements'] = Measurement.objects.filter(parameter=self.get_object(), is_valid=True)
        return context
