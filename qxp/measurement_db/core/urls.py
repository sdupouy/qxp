from django.urls import path

from .views import IndexView, CooldownListView, CooldownDetailView, ExperimentRunListView, MeasurementListView, \
    ParameterDetailView

urlpatterns = [
    path('', IndexView.as_view(), name="index"),
    path('cooldowns', CooldownListView.as_view(), name="cooldown-list"),
    path('cooldown/<int:pk>', CooldownDetailView.as_view(), name="cooldown-detail"),
    path('experiment_runs', ExperimentRunListView.as_view(), name="experiment-run-list"),
    path('measurements', MeasurementListView.as_view(), name="measurement-list"),
    path('parameter/<int:pk>', ParameterDetailView.as_view(), name="parameter-detail"),
]