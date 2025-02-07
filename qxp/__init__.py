import os
import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qxp.measurement_db.settings')
django.setup()
