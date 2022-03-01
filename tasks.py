import os
import re
import base64
from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings as django_settings
from django.template.loader import get_template
from .core.exporter_factory import ExporterFactory
from collation.ritual_direction_extractor import RitualDirectionExtractor
from collation.note_extractor import NoteExtractor
from collation.transcription_to_latex import TranscriptionConverter


def send_email(output_dir, filename, addresses, name):
    template = get_template('collation/export_email_template.html')
    message = template.render({'name': name})
    msg = EmailMessage('MUYA-WCE note extraction results', message, django_settings.DEFAULT_FROM_EMAIL, addresses,
                       reply_to=tuple(django_settings.CONTACT_EMAIL))
    msg.content_subtype = 'html'
    msg.attach_file(os.path.join(output_dir, filename))
    msg.send()


@shared_task(track_started=True)
def get_apparatus(data, settings):

    recipient_email_addresses = settings['email_addresses']
    del settings['email_addresses']
    recipient_name = settings['name']
    del settings['name']

    exporter_settings = None
    if 'format' in settings:
        if settings['format'] == 'latex':
            file_ext = 'txt'
            exporter_settings = {'python_file': 'collation.latex_exporter',
                                 'class_name': 'LatexExporter',
                                 'function': 'export_data'
                                 }
        elif settings['format'] == 'positive_xml':
            file_ext = 'xml'
            exporter_settings = {'python_file': 'collation.yasna_exporter',
                                 'class_name': 'YasnaExporter',
                                 'function': 'export_data'
                                 }
        elif settings['format'] == 'cbgm_xml':
            file_ext = 'xml'
            exporter_settings = {'python_file': 'collation.cbgm_exporter',
                                 'class_name': 'CBGMExporter',
                                 'function': 'export_data'
                                 }

    output_dir = os.path.join(django_settings.APPARATUS_BASE_DIR, settings['path'])
    del settings['path']

    if exporter_settings is not None:
        exf = ExporterFactory(exporter_settings, options=settings)
    else:
        exf = ExporterFactory()

    app = exf.export_data(data)

    try:
        os.makedirs(output_dir)
    except FileExistsError:
        pass
    except PermissionError:
        raise PermissionError('Cannot access the required directory, permissions are incorrect.')
    filename = '{0}-apparatus.{1}'.format(settings['format'], file_ext)
    with open(os.path.join(output_dir, filename), 'w', encoding="utf-8") as output:
        output.write(app)
    send_email(output_dir, filename, recipient_email_addresses, recipient_name)
    return ('email', 'apparatus', filename, settings['format'], settings['project_id'])


@shared_task(track_started=True)
def extract_notes(data, settings):
    extractor = NoteExtractor()
    notes, sigla = extractor.extract_notes(data)

    output_dir = os.path.join(django_settings.EXPORT_BASE_DIR, settings['path'])
    try:
        os.makedirs(output_dir)
    except FileExistsError:
        pass
    except PermissionError:
        raise PermissionError('Cannot access the required directory, permissions are incorrect.')
    filename = 'notes.csv'
    with open(os.path.join(output_dir, filename), 'w', encoding='utf-8') as output:
        output.write('sigla\tcontaining unit\tnote text\n')
        for siglum in sigla:
            for entry in notes[siglum]:
                output.write('{}\t{}\t{}\n'.format(siglum, entry[0], entry[1]))
    send_email(output_dir, filename, settings['email_addresses'], settings['name'])
    return ('email', 'notes', filename, settings['project'])


@shared_task(track_started=True)
def extract_ritual_directions(data, settings):
    extractor = RitualDirectionExtractor()
    ritual_dirs, sigla, n_list, errors = extractor.extract_ritual_directions(data)
    n_list_counts = {}
    for n in n_list:
        most_rd = 0
        for siglum in ritual_dirs:
            if n in ritual_dirs[siglum] and len(ritual_dirs[siglum][n]) > most_rd:
                most_rd = len(ritual_dirs[siglum][n])
        n_list_counts[n] = most_rd

    output_dir = os.path.join(django_settings.EXPORT_BASE_DIR, settings['path'])
    try:
        os.makedirs(output_dir)
    except FileExistsError:
        pass
    except PermissionError:
        raise PermissionError('Cannot access the required directory, permissions are incorrect.')
    filename = 'ritual_directions.csv'
    with open(os.path.join(output_dir, filename), 'w', encoding='utf-8') as output:
        output.write('sigla\t')
        for n in n_list:
            output.write('%s\t' % n * n_list_counts[n])
        output.write('\n')

        for siglum in sigla:
            output.write('%s\t' % siglum)
            for n in n_list:
                if siglum in ritual_dirs and n in ritual_dirs[siglum]:
                    for text in ritual_dirs[siglum][n]:
                        output.write('%s\t' % text)
                    output.write('\t'*(n_list_counts[n]-len(ritual_dirs[siglum][n])))
                else:
                    output.write('\t'*n_list_counts[n])
            output.write('\n')
    send_email(output_dir, filename, settings['email_addresses'], settings['name'])
    return ('email', 'ritual-directions', filename, settings['project'], errors)


@shared_task(track_started=True)
def generate_transcription_latex(transcription_src, settings):

    meta, content = transcription_src.split(',', 1)
    ext_m = re.match("data:.*?/(.*?);base64", meta)
    if not ext_m:
        raise ValueError("Can't parse base64 file data ({})".format(meta))
    file_string = base64.b64decode(content)

    converter = TranscriptionConverter()
    latex, siglum = converter.convert_transcription(file_string)
    output_dir = os.path.join(django_settings.EXPORT_BASE_DIR, settings['path'])
    try:
        os.makedirs(output_dir)
    except FileExistsError:
        pass
    filename = 'latex-transcription-{}.txt'.format(siglum)
    with open(os.path.join(output_dir, filename), 'w', encoding="utf-8") as output:
        output.write(latex)
    send_email(output_dir, filename, settings['email_addresses'], settings['name'])
    return ('email', 'latex-transcription', filename, str(settings['project_id']))
