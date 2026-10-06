from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Chip, Cooldown, Experiment, ExperimentRun, OpticalTable


class ExperimentRunListViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        chip = Chip.objects.create(identifier='test-chip')
        cooldown = Cooldown.objects.create(number=1, chip=chip)
        optical_table = OpticalTable.objects.create(rack_name='test-rack')
        experiment = Experiment.objects.create(
            identifier='test-experiment',
            display_name='Test experiment',
        )
        started_at = timezone.now()
        cls.experiment_run = ExperimentRun.objects.create(
            datetime=started_at,
            datetime_end=started_at + timedelta(minutes=2),
            experiment=experiment,
            cooldown=cooldown,
            optical_table=optical_table,
            data_path='test.hdf5',
            comment='First line\nSecond line',
        )

    def test_standard_view_is_the_default(self):
        response = self.client.get(reverse('experiment-run-list'))

        self.assertEqual(response.context['view_mode'], 'standard')
        self.assertContains(response, '<th scope="col">Chip</th>', html=True)
        self.assertNotContains(response, 'class="experiment-run-thumbnail"')

    def test_image_view_displays_figure_and_comment(self):
        response = self.client.get(reverse('experiment-run-list'), {'view': 'image'})

        self.assertEqual(response.context['view_mode'], 'image')
        self.assertContains(response, 'class="experiment-run-thumbnail"')
        self.assertContains(response, 'First line<br>Second line', html=True)
        self.assertContains(response, '?view=image', count=2)

    def test_toggle_preserves_filters(self):
        response = self.client.get(
            reverse('experiment-run-list'),
            {'experiment': self.experiment_run.experiment_id, 'view': 'image'},
        )

        expected_query = (
            f'?experiment={self.experiment_run.experiment_id}&amp;view=standard'
        )
        self.assertContains(response, expected_query)

    def test_invalid_view_falls_back_to_standard(self):
        response = self.client.get(
            reverse('experiment-run-list'),
            {'view': 'unsupported'},
        )

        self.assertEqual(response.context['view_mode'], 'standard')
        self.assertNotContains(response, 'class="experiment-run-thumbnail"')
        self.assertContains(response, 'name="view" value="standard"')
