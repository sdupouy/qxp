from django.urls import path

from .views import IndexView, CooldownDetailView, ExperimentRunListView, MeasurementListView, \
    ParameterDetailView, CooldownCreateView, ChipListView, ChipDetailView, ChipCreateView, warmup, \
    OpticalTableCreateView, ExperimentListView, ExperimentDetailView, ExperimentRunDetailView, exp_run_toggle_star, \
    exp_run_config, exp_run_code, exp_run_figure, ExperimentRunDeleteView, measurement_toggle_is_valid

urlpatterns = [
    path('', IndexView.as_view(), name="index"),
    path('cooldown/<int:pk>', CooldownDetailView.as_view(), name="cooldown-detail"),
    path('cooldowns/create', CooldownCreateView.as_view(), name="cooldown-create"),
    path('warmup/<int:pk>', warmup, name="warmup"),
    path('chips', ChipListView.as_view(), name="chip-list"),
    path('chip/<slug:identifier>', ChipDetailView.as_view(), name="chip-detail"),
    path('chips/create', ChipCreateView.as_view(), name="chip-create"),
    path('optical-tables/create', OpticalTableCreateView.as_view(), name="optical-table-create"),
    path('experiments', ExperimentListView.as_view(), name="experiment-list"),
    path('experiment/<slug:identifier>', ExperimentDetailView.as_view(), name="experiment-detail"),
    path('experiment_runs', ExperimentRunListView.as_view(), name="experiment-run-list"),
    path('experiment_run/<int:pk>', ExperimentRunDetailView.as_view(), name="experiment-run-detail"),
    path('experiment_run/<int:pk>/config', exp_run_config, name="experiment-run-config"),
    path('experiment_run/<int:pk>/code', exp_run_code, name="experiment-run-code"),
    path('experiment_run/<int:pk>/figure.png', exp_run_figure, name="experiment-run-figure"),
    path('experiment_run/<int:pk>/toggle_star', exp_run_toggle_star, name="toggle-star-exp-run"),
    path('experiment_run/<int:pk>/delete', ExperimentRunDeleteView.as_view(), name="experiment-run-delete"),
    path('measurements', MeasurementListView.as_view(), name="measurement-list"),
    path('measurement/<int:pk>/toggle_is_valid', measurement_toggle_is_valid, name="toggle-is-valid-measurement"),
    path('parameter/<slug:identifier>', ParameterDetailView.as_view(), name="parameter-detail"),
]