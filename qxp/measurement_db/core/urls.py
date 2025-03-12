from django.urls import path

from .views import IndexView, CooldownListView, CooldownDetailView, ExperimentRunListView, MeasurementListView, \
    ParameterDetailView, CooldownCreateView, ChipListView, ChipDetailView, ChipCreateView, warmup, \
    OpticalTableCreateView, ExperimentListView, ExperimentDetailView, ExperimentRunDetailView

urlpatterns = [
    path('', IndexView.as_view(), name="index"),
    path('cooldowns', CooldownListView.as_view(), name="cooldown-list"),
    path('cooldown/<int:pk>', CooldownDetailView.as_view(), name="cooldown-detail"),
    path('cooldown/create', CooldownCreateView.as_view(), name="cooldown-create"),
    path('warmup/<int:pk>', warmup, name="warmup"),
    path('chips', ChipListView.as_view(), name="chip-list"),
    path('chip/<int:pk>', ChipDetailView.as_view(), name="chip-detail"),
    path('chip/create', ChipCreateView.as_view(), name="chip-create"),
    path('optical-table/create', OpticalTableCreateView.as_view(), name="optical-table-create"),
    path('experiments', ExperimentListView.as_view(), name="experiment-list"),
    path('experiment/<slug:identifier>', ExperimentDetailView.as_view(), name="experiment-detail"),
    path('experiment_runs', ExperimentRunListView.as_view(), name="experiment-run-list"),
    path('experiment_run/<int:pk>', ExperimentRunDetailView.as_view(), name="experiment-run-detail"),
    path('measurements', MeasurementListView.as_view(), name="measurement-list"),
    path('parameter/<slug:identifier>', ParameterDetailView.as_view(), name="parameter-detail"),
]