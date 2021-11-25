from django.conf import settings
from django.db import models
from api.models import BaseModel
from transcriptions.models import Work
from transcriptions.models import Transcription
from transcriptions.models import Collection
from django.contrib.postgres.fields import ArrayField


def get_default_ceremonies():
    return ['Y', 'YiR', 'VrS', 'VS', 'VytS']


class Project (BaseModel):

    AVAILABILITY = 'public'

    SERIALIZER = 'CollationProjectSerializer'

    PREFETCH_KEYS = ['witnesses']

    REQUIRED_FIELDS = ['identifier', 'name', 'managing_editor']

    identifier = models.TextField('Project Identifier',
                                  max_length=30,
                                  unique=True)
    name = models.TextField('Project Name',
                            max_length=20)
    collection = models.ForeignKey(Collection, models.PROTECT)
    language_choices = [('ae', 'Avestan'),
                        ('gu', 'Gujarati'),
                        ('fa', 'Persian'),
                        ('sa', 'Sanskrit'),
                        ('ae-Avst', 'Avestan in Avesta Script'),
                        ('ae-Phlv', 'Avestan in Pahlavi Script'),
                        ('ae-Gujr', 'Avestan in Gujarati Script'),
                        ('gu-Gujr', 'Gujarati in Gujarati Script'),
                        ('gu-Arab', 'Gujarati in Arabic Script'),
                        ('pal-Avst', 'Zoroastrian Middle Persian in Avesta Script'),
                        ('pal-Phlv', 'Zoroastrian Middle Persian in Pahlavi Script'),
                        ('pal-Phli', 'Middle Persian in inscriptional Pahlavi Script'),
                        ('pal-Gujr', 'Zoroastrian Middle Persian in Gujarati Script'),
                        ('ar', 'Arabic')]
    language = models.CharField('Language', max_length=10, choices=language_choices)
    work = models.ForeignKey(Work, models.PROTECT, related_name="collation_project")
    managing_editor = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT, related_name='managing_editor')
    editors = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='projects_as_editor', blank=True)
    basetext = models.ForeignKey(Transcription, models.PROTECT, null=True, blank=True)
    witnesses = models.ManyToManyField(Transcription, related_name='witnesses', blank=True)
    ceremonies = ArrayField(models.TextField(),
                            null=True,
                            blank=True,
                            default=get_default_ceremonies,
                            help_text='''Add all ceremonies in desired display order separated with commas.''')
    ceremony_mapping = models.JSONField(blank=True,
                                        null=True,
                                        help_text='''This field is in JSON. Do not mess with this unless you are
                                                  absolutely sure you know what you are doing.''')
    supplement_range = models.JSONField(blank=True,
                                        null=True,
                                        help_text='''This field is in JSON. Do not mess with this unless you are
                                                  absolutely sure you know what you are doing.''')
    configuration = models.JSONField(blank=True,
                                     null=True,
                                     help_text='''This field is in JSON. Do not mess with this unless you are
                                               absolutely sure you know what you are doing.''')

    def __str__(self):
        return '{} ({})'.format(self.name, self.identifier)

    def get_serialization_fields():
        fields = '__all__'
        return fields

    def get_fields():
        data = {}
        fields = list(Project._meta.get_fields(include_hidden=True))
        for field in fields:
            data[field.name] = field.get_internal_type()
        return data

    def get_user_fields():
        user_fields = ['editors']
        data = {}
        fields = list(Project._meta.get_fields(include_hidden=True))
        for field in fields:
            if field.name in user_fields:
                data[field.name] = field.get_internal_type()
        return data


class Decision (BaseModel):

    AVAILABILITY = 'project'

    SERIALIZER = 'DecisionSerializer'

    REQUIRED_FIELDS = ['type', 'scope', 'classification', 't', 'n']

    type = models.TextField('Type')
    scope = models.TextField('Scope')
    classification = models.TextField('Class')
    context = models.JSONField(blank=True, null=True)
    conditions = models.JSONField(blank=True, null=True)
    exceptions = ArrayField(models.TextField(), null=True)
    t = models.TextField('t')
    n = models.TextField('n')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT, related_name='user_decisions', null=True)
    project = models.ForeignKey(Project, models.PROTECT, related_name='project_decisions', null=True)
    comments = models.TextField('comments', blank=True)

    def get_serialization_fields():
        fields = '__all__'
        return fields

    def get_fields():
        data = {}
        fields = list(Decision._meta.get_fields(include_hidden=True))
        for field in fields:
            data[field.name] = field.get_internal_type()
        return data


class Collation (BaseModel):

    AVAILABILITY = 'project'

    SERIALIZER = 'CollationSerializer'

    REQUIRED_FIELDS = ['work', 'identifier', 'context', 'structure',
                       'display_settings', 'data_settings', 'algorithm_settings',
                       'user', 'status']

    identifier = models.TextField('identifier', unique=True)
    work = models.ForeignKey(Work, models.PROTECT, related_name="collated_verse")
    chapter_number = models.IntegerField('chapter_number', null=True)
    stanza_number = models.IntegerField('verse_or_stanza_number', null=True)
    line_number = models.IntegerField('line_or_verseline_number', null=True)
    context = models.TextField('Context')
    structure = models.JSONField()
    display_settings = models.JSONField()
    data_settings = models.JSONField()
    algorithm_settings = models.JSONField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT, related_name='user_collation')
    project = models.ForeignKey(Project, models.PROTECT, related_name='project_collation', null=True)
    status = models.TextField('Status')

    class Meta:
        ordering = ['chapter_number', 'stanza_number', 'line_number']

    def get_serialization_fields():
        fields = '__all__'
        return fields

    def get_fields():
        data = {}
        fields = list(Collation._meta.get_fields(include_hidden=True))
        for field in fields:
            data[field.name] = field.get_internal_type()
        return data
