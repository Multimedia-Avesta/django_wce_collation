from django.core.management.base import BaseCommand, CommandError
from django.conf import settings as django_settings
import os


class Command(BaseCommand):

    def handle(self, *args, **options):

        os.system('java -jar {}/collation/collatex-tools-1.8-SNAPSHOT.jar -S'.format(django_settings.BASE_DIR))
