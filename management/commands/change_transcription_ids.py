import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings as django_settings
from collation.models import Project, Collation
from transcriptions.models import Transcription


class Command(BaseCommand):

    '''
    A script to change the ids in already saved collations if the transcription identifier changes later.
    '''

    save_data = False

    def add_arguments(self, parser):
        parser.add_argument('project_name', type=str)
        parser.add_argument('old_id', type=str)
        parser.add_argument('new_id', type=str)
        parser.add_argument('-s', '--save',
                            help='save rather than just test the script runs without error',
                            action='store_true', dest='save_data')

    def change_identifier(self, project, old_id, new_id):
        collations = Collation.objects.filter(project=project)
        for collation in collations:
            hand_id_map = collation.structure['hand_id_map']
            for entry in hand_id_map:
                if hand_id_map[entry] == old_id:
                    hand_id_map[entry] = new_id
            collation.structure['hand_id_map'] = hand_id_map
            collation.data_settings['witness_list'] = [new_id if x == old_id else x for x in collation.data_settings['witness_list']]
            if self.save_data:
                collation.save()

    def handle(self, *args, **options):

        project_name = options['project_name']
        old_id = options['old_id']
        new_id = options['new_id']
        if options['save_data']:
            self.save_data = True

        # check the data that can be checked
        projects = Project.objects.filter(name=project_name)
        if projects.count() == 1:
            project = projects[0]
        else:
            raise CommandError('The project specified could not be found.')
        transcriptions = Transcription.objects.filter(identifier=new_id)
        if transcriptions.count() != 1:
            raise CommandError('The new identifier specified does not correspond to a transcription in the database.')

        self.change_identifier(project, old_id, new_id)
