import os
import re
import pickle
import json
from urllib.parse import urlencode, urlparse, parse_qs
from django.conf import settings as django_settings
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse, Http404
from django.urls import reverse
from django.contrib.auth.decorators import login_required,  permission_required
from django.db.models import Q
from celery.result import AsyncResult
from accounts.models import User
from transcriptions import models as transcription_models
from transcriptions.serializers import TranscriptionSerializer, CollationUnitSerializer
from .serializers import CollationSerializer
from .models import Project, Collation
from collation.core.exceptions import DataInputException
from collation.core.preprocessor import PreProcessor
from collation.core.settings_applier import SettingsApplier
from collation.core.exporter_factory import ExporterFactory
from collation import tasks


def get_login_status(request):
    if request.user.is_authenticated:
        return request.user.username
    else:
        return None


@login_required
@permission_required(['collation.delete_collation',
                      'collation.add_collation',
                      'collation.change_collation'
                      ], raise_exception=True)
def collate(request):
    params = json.loads(request.POST.get('options'))
    p = PreProcessor(params['configs'])
    try:
        output = p.process_witness_list(params['data'])
    except DataInputException as e:
        return JsonResponse({'message': str(e)}, status=500)
    return JsonResponse(output)


def apply_settings(request):
    data = json.loads(request.POST.get('data'))

    sa = SettingsApplier(data['options'])
    tokens = sa.apply_settings_to_token_list(data['tokens'])
    return JsonResponse({'tokens': tokens})


@login_required
def project_select(request):
    # if we have selected a project to use (posting back from the form)
    if request.method == 'POST':
        request.session['project'] = int(request.POST.get('project'))
        parsed_url = urlparse(request.META.get('HTTP_REFERER'))
        url_query = parse_qs(parsed_url[4])
        if 'next' in url_query:
            return HttpResponseRedirect('{}://{}{}'.format(parsed_url[0], parsed_url[1], url_query['next'][0]))
        return HttpResponseRedirect(reverse('collation:index'))

    # if we have asked to switch projects
    login_details = get_login_status(request)
    projects = Project.objects.filter(editors=request.user.id)

    data = {'projects': projects,
            'login_status': login_details,
            'post_logout_url': '/collation',
            'post_login_url': '/collation',
            'page_title': 'Collation Project Select',
            }
    if 'project' in request.session:
        data['current_project'] = request.session['project']
    return render(request, 'collation/project_select.html', data)


@login_required
@permission_required(['collation.change_project',
                      ], raise_exception=True)
def transcription_management(request):

    post_login_url = request.path + '?' + request.GET.urlencode()
    login_details = get_login_status(request)
    project = None
    manging_editor_projects = Project.objects.filter(managing_editor=request.user.id).values_list('id', flat=True)
    project_count = Project.objects.filter(editors=request.user.id).count()

    if 'project' in request.session:
        try:
            project = Project.objects.filter(editors=request.user.id).get(pk=request.session['project'])
        except Project.DoesNotExist:
            del request.session['project']
            return HttpResponseRedirect(reverse('collation:index'))

    elif project_count == 1 and 'project' not in request.session:
        project = Project.objects.filter(editors=request.user.id)[0]
        request.session['project'] = project.id

    if not project:
        return HttpResponseRedirect(reverse('collation:projectselect'))

    if project.id in manging_editor_projects:
        managing_editor = True
    else:
        managing_editor = False

    data = {'login_status': login_details,
            'post_logout_url': '/collation',
            'post_login_url': '/collation/transcriptionmanagement',
            'page_title': 'Transcription Management Page',
            'project_name': project.name,
            'project': project,
            'managing_editor': managing_editor
            }

    return render(request, 'collation/transcription_management.html', data)


@login_required
def project_summary(request):

    post_login_url = request.path + '?' + request.GET.urlencode()
    login_details = get_login_status(request)

    manging_editor_projects = Project.objects.filter(managing_editor=request.user.id).values_list('id', flat=True)
    project_count = Project.objects.filter(editors=request.user.id).count()

    # If we are not logged in or have no project permissions for the summary
    # then you get sent back to the index page
    if login_details is None or project_count == 0:
        data = {'page_title': 'Collation Home',
                'login_status': login_details,
                'post_logout_url': '/collation',
                'post_login_url': post_login_url,
                'post_select_url': post_login_url
                }
        return render(request, 'collation/index.html', data)

    # check to see if we need a switch project button
    switch_button_required = False
    if project_count > 1:
        switch_button_required = True

    # If we haven't got a session project and there are multiple project options
    # then you get sent off to choose a project
    if 'project' not in request.session and project_count > 1:
        url = reverse('collation:projectselect')
        query_string = urlencode({'next': '/collation/projectsummary'})
        return HttpResponseRedirect('{}?{}'.format(url, query_string))

    if 'project' in request.session:
        try:
            project = Project.objects.filter(editors=request.user.id).get(pk=request.session['project'])
        except Project.DoesNotExist:
            del request.session['project']
            return HttpResponseRedirect(reverse('collation:index'))

    elif project_count == 1 and 'project' not in request.session:
        project = Project.objects.filter(editors=request.user.id)[0]
        request.session['project'] = project.id

    if project.id in manging_editor_projects:
        managing_editor = True
    else:
        managing_editor = False

    supplements = []
    for witness in project.witnesses.all():
        if re.match(r'^\d+S\d?$', witness.siglum):
            supplements.append(witness.siglum)
    delete_supplements = False
    if len(supplements) > 0:
        has_supplements = True
    else:
        has_supplements = False
        if project.supplement_range is not None and len(project.supplement_range) > 0:
            delete_supplements = True

    chapters = []
    basetext_units = None
    if project.basetext is not None:
        basetext_units = transcription_models.CollationUnit.objects.filter(transcription__id=project.basetext.id)
        for unit in basetext_units:
            if unit.chapter_number not in chapters:
                chapters.append(unit.chapter_number)

    collations = Collation.objects.filter(project__id=request.session['project'],
                                          status='approved')
    units = []
    for collation in collations:
        units.append(collation.context)

    data = {'login_status': login_details,
            'post_logout_url': '/collation',
            'post_login_url': '/collation/projectsummary',
            'page_title': 'Project Page',
            'project_name': project.name,
            'project': project,
            'switch_button': switch_button_required,
            'switch_url': '/collation/projectselect',
            'managing_editor': managing_editor,
            'chapters': chapters,
            'units': units,
            'basetext_units': basetext_units,
            'has_supplements': has_supplements,
            'delete_supplements': delete_supplements
            }

    return render(request, 'collation/project_summary.html', data)


def index(request):
    post_login_url = request.path + '?' + request.GET.urlencode()
    login_details = get_login_status(request)
    project_count = Project.objects.filter(editors=request.user.id).count()

    # If we are not logged in or have no project permissions for collating
    # then you get sent back to the index page
    if login_details is None or project_count == 0:
        data = {'page_title': 'Collation Home',
                'login_status': login_details,
                'post_logout_url': '/collation',
                'post_login_url': post_login_url
                }
        return render(request, 'collation/index.html', data)

    # check to see if we need a switch project button
    switch_button_required = False
    if project_count > 1:
        switch_button_required = True

    # If we haven't got a session project and there are multiple project options
    # then you get sent off to choose a project
    if 'project' not in request.session and project_count > 1:
        return HttpResponseRedirect(reverse('collation:projectselect'))

    # otherwise we either have a project in the session id and/or there is only one project
    data = {'page_title': 'Collation Home',
            'login_status': login_details,
            'post_logout_url': '/collation',
            'post_login_url': post_login_url,
            'switch_button': switch_button_required,
            'switch_url': '/collation/projectselect?' + 'next=' + post_login_url,
            'user': request.user,
            }

    if 'project' in request.session:
        try:
            project = Project.objects.filter(editors=request.user.id).get(pk=request.session['project'])
        except Project.DoesNotExist:
            del request.session['project']
            return HttpResponseRedirect(reverse('collation:index'))

    elif project_count == 1 and 'project' not in request.session:
        project = Project.objects.filter(editors=request.user.id)[0]
        request.session['project'] = project.id

    data['project_name'] = project.name
    data['project'] = project
    # TODO: consider moving to pipes rather than comma as divider?
    witnesses = project.witnesses.all()
    if len(witnesses) == 0:
        return HttpResponseRedirect(reverse('collation:transcriptionmanagement'))
    if project.basetext is None:
        data['missing_basetext'] = True
    data['preselected_witnesses'] = ','.join([str(x.identifier) for x in witnesses])
    return render(request, 'collation/collation_menu.html', data)


@login_required
def resolve_editor_names(request):
    if 'project' not in request.session:
        # TODO: more appropriate error needed here
        raise Http404
    ids = request.GET.get('ids')
    user_names = {}
    ids = ids.split(',')
    if len(ids) > 0:
        # TODO: test this next line when you have multiple users in multiple projects to check it still works
        users = User.objects.filter(projects_as_editor__id=request.session['project']).filter(id__in=ids)
        for user in users:
            user_names[user.id] = {}
            user_names[user.id]['id'] = user.id
            if user.full_name != '':
                user_names[user.id]['name'] = user.full_name
    return JsonResponse(user_names)


def _get_work_mapped_query(work_abbreviation, contexts, transcription_ids, language):
    main_query = query = Q()
    for i, context in enumerate(contexts.split(';')):
        query = Q()
        query &= Q(('work__abbreviation', work_abbreviation))
        query &= Q(('context', context.strip()))
        query &= Q(('language', language))
        query &= Q(('transcription__identifier__in', transcription_ids.split(',')))
        main_query |= query
    return main_query


def get_filter_field_value(field):
    filter_string = None
    try:
        filter_string = field['search']
    except (KeyError, TypeError):
        try:
            filter_string = field['id']
        except (KeyError, TypeError):
            filter_string = field
    return filter_string


def get_filter_details(query_dict, fields):
    if '_show' in query_dict:
        del query_dict['_show']
    query_dict['offset'] = 0

    remove_filter_required = False
    for field in fields:
        filter_string = get_filter_field_value(field)
        if filter_string:
            if filter_string in query_dict:
                remove_filter_required = True
                del query_dict[filter_string]

    # remove filter button label code
    remove_filter_button_label = 'Remove filter'
    return (query_dict, remove_filter_button_label, remove_filter_required)


@login_required
def get_collation_data(request):
    """
    special get collation data for MUYA which deals with the mapping. Returns unpaginated
    results so just need to use them as raw json.
    """
    project = Project.objects.filter(editors=request.user.id).get(pk=request.session['project'])
    basetext = request.GET.get('basetext')
    context = request.GET.get('context')
    transcription_ids = request.GET.get('transcription__identifier')
    first_context_per_work = {}
    unmapped = []
    fields = tuple(request.GET.get('_fields').split(','))

    try:
        mapping_object = project.ceremony_mapping[context]
        mappings = mapping_object['details']
    except (TypeError, KeyError, IndexError):
        query = Q()
        query &= Q(('context', context))
        query &= Q(('transcription__identifier__in', transcription_ids.split(',')))
        query &= Q(('language', project.language))
    else:
        query = Q()
        for key in mappings:
            if mappings[key] is not None and mappings[key] != '':  # we need both checks
                first_context_per_work[key] = mappings[key].split(';')[0]
                query |= Q(_get_work_mapped_query(key, mappings[key], transcription_ids, project.language))
            else:
                # this collects all the witnesses which are not expected for this unit
                # they are actually marked just before the return statement from this function
                transcriptions = transcription_models.Transcription.objects.filter(
                        work__abbreviation=key,
                        identifier__in=transcription_ids.split(',')
                        ).values_list('siglum')
                unmapped.extend([x[0] for x in transcriptions])
    results = transcription_models.CollationUnit.objects.filter(query).exclude(~Q(context=context),
                                                                               transcription__identifier=basetext)
    for result in results:
        if (result.work.abbreviation in first_context_per_work
                and result.context != first_context_per_work[result.work.abbreviation]):
            if result.witnesses and result.witnesses is not None:
                for entry in result.witnesses:
                    entry['id'] = '{0} ({1})'.format(entry['id'], result.context)
                    for token in entry['tokens']:
                        token['reading'] = '{0} ({1})'.format(token['reading'], result.context)
                        token['siglum'] = '{0} ({1})'.format(token['siglum'], result.context)

            result.siglum = '{0} ({1})'.format(result.siglum, result.context)

    serializer = CollationUnitSerializer(results, fields=fields, many=True)
    data = serializer.data
    response = {}
    response['results'] = data
    special_categories = []
    if len(unmapped) > 0:
        special_categories.append({'witnesses': unmapped, 'label': 'not expected'})  # 'type': 'om',
        response['special_categories'] = special_categories
    return JsonResponse(response)


@login_required
def get_apparatus(request):
    if 'task' in request.GET:
        post_login_url = request.path + '?' + request.GET.urlencode()
        login_details = get_login_status(request)
        task = AsyncResult(request.GET.get('task'))
        project = Project.objects.get(pk=request.GET.get('project'))
        data = {'page_title': 'Apparatus Generator',
                'project_name': project.name,
                'login_status': login_details,
                'post_logout_url': '/collation',
                'post_login_url': post_login_url,
                'result': task.result,
                'state': task.state,
                'task_id': task.task_id
                }
        if task.state == 'FAILURE':
            print(repr(task.result))
            message_string = '{}: {}'.format(task.result.__class__.__name__, ', '.join(list(task.result.args)))
            data['result'] = {'message': message_string, 'state': task.state}
            print(data)
        return JsonResponse(data)

    # elif 'file' in request.GET:
    #     """
    #     If we have a GET request and 'file' in the request then download the file
    #     """
    #     post_login_url = request.path + '?' + request.GET.urlencode()
    #     login_details = get_login_status(request)
    #     task_id = request.GET.get('file')
    #     task = AsyncResult(task_id)
    #     data = data = {'page_title': 'Apparatus Generator',
    #                    'login_status': login_details,
    #                    'post_logout_url': '/collation',
    #                    'post_login_url': post_login_url,
    #                    'back_url': '/collation/projectsummary',
    #                    'back_text': 'Return to Project Summary'}
    #     if task.result:
    #         url = task.result[1]
    #         path = task.result[2]
    #         format = task.result[3]
    #         project = task.result[4]
    #         # reconstruct the path here to make sure we are who we were when we created it!
    #         filepath = os.path.join(django_settings.APPARATUS_BASE_DIR, project, str(request.user.id), format, path)
    #         if ('/' not in task.result) and os.path.isfile(filepath):
    #             if 'xml' in format:
    #                 response = HttpResponse(content_type='text/xml')
    #             else:
    #                 response = HttpResponse(content_type='text/plain')
    #             response['Content-Disposition'] = 'attachment; filename=' + path
    #             response.write(open(filepath, 'rb').read())
    #             return response
    #         else:
    #             data['message'] = 'There was a problem with locating the file download.'
    #     else:
    #         data['message'] = 'The task id was not recognised.'
    #     return render(request, 'collation/download_problem.html', data)

    # this is the one from each unit
    if 'data' in request.POST:
        data = json.loads(request.POST.get('data'))
        format = request.POST.get('format')
        project = Project.objects.get(pk=request.session['project'])
        exporter_settings = json.loads(request.POST.get('settings'))
        if format is None:
            if 'format' in exporter_settings:
                format = exporter_settings['format']
            else:
                format = 'text'
        # other options for easy testing
        # format = 'positive_xml'
        # exporter_settings = {'python_file': 'collation.yasna_exporter',
        #                      'class_name': 'YasnaExporter',
        #                      'function': 'export_data',
        #                      'ignore_basetext': True}

        # format = 'positive_xml'
        # exporter_settings = {'python_file': 'collation.cbgm_exporter',
        #                      'class_name': 'CBGMExporter',
        #                      'function': 'export_data',
        #                      'ignore_basetext': True}

        if 'xml' in format:
            file_ext = 'xml'
        else:
            file_ext = 'txt'

        options = {'format': format,
                   'ignore_basetext': True,
                   'settings': {}}
        options['project_id'] = project.id
        options['settings']['main_language'] = project.language
        if project.language == 'sa':
            options['settings']['book_prefix'] = 'S'
        exf = ExporterFactory(exporter_settings, options=options)
        app = exf.export_data(data)
        response = HttpResponse(app, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="{}-apparatus.{}"'.format(format, file_ext)
        return response

    # this send the details to the Celery task
    project = Project.objects.get(pk=request.session['project'])
    query = Q()
    query &= Q(('status', request.POST.get('status', 'edited')))
    query &= Q(('project__id', request.POST.get('project__id')))
    chapter = request.POST.get('chapter')
    if chapter != 'all':
        query &= Q(('chapter_number', chapter))
    excluded_units = request.POST.getlist('excluded[]')
    exclude_query = Q()
    if len(excluded_units) > 0:
        exclude_query &= Q(('context__in', excluded_units))
    results = Collation.objects.filter(query).exclude(exclude_query)

    serializer = CollationSerializer(results, many=True)
    data = serializer.data
    settings = {'format': request.POST.get('format'),
                'ignore_basetext': True,
                'settings': {}
                }
    add_raised_plus = request.POST.get('add_raised_plus', False)
    if add_raised_plus == 'True':
        settings['settings']['add_raised_plus'] = True
    else:
        settings['settings']['add_raised_plus'] = False

    apparatus = request.POST.get('apparatus', None)
    if apparatus and apparatus == 'include':
        settings['settings']['include_apparatus'] = True
        settings['settings']['omit_apparatus'] = request.POST.getlist('omit_apparatus[]')
    else:
        settings['settings']['include_apparatus'] = False
        settings['settings']['omit_apparatus'] = []
    ritual_directions = request.POST.get('ritual_directions', None)
    if ritual_directions and ritual_directions != 'none':
        settings['settings']['ritual_directions'] = ritual_directions
    path = os.path.join(request.POST.get('project__id'), str(request.user.id), request.POST.get('format'))
    settings['path'] = path
    settings['settings']['user_id'] = str(request.user.id)
    settings['project_id'] = request.POST.get('project__id')
    settings['settings']['main_language'] = project.language
    settings['email_addresses'] = [request.user.email]
    if project.language == 'sa':
        settings['settings']['book_prefix'] = 'S'
    task = tasks.get_apparatus.delay(data, settings)
    return HttpResponseRedirect('?task=' + task.task_id + '&project=' + request.POST.get('project__id'))


def get_details_from_id(id):
    temp = id.split('_')
    words = temp[3].split('-')
    return int(temp[1]), int(words[0]), int(words[1])


def get_details_from_rd_id(id):
    temp = id.split('_')
    words = temp[4].split('-')
    return int(temp[2]), int(words[0]), int(words[1])


def make_rd_lookup(ritual_directions, new_data):
    rd_lookup = {}
    for id in ritual_directions:
        if id.find('before') != -1:
            rd_position = 'before'
            if 'before' not in rd_lookup:
                rd_lookup['before'] = {}
        if id.find('after') != -1:
            rd_position = 'after'
            if 'after' not in rd_lookup:
                rd_lookup['after'] = {}
        unit_pos, start, end = get_details_from_rd_id(id)
        if unit_pos not in rd_lookup[rd_position]:
            rd_lookup[rd_position][unit_pos] = {}
        if rd_position == 'before':
            if start not in rd_lookup[rd_position][unit_pos]:
                rd_lookup[rd_position][unit_pos][start] = {}
            if id.find('rdt') == 0:
                rd_lookup[rd_position][unit_pos][start]['rdt'] = new_data[id]
            elif id.find('rd') == 0:
                rd_lookup[rd_position][unit_pos][start]['rd'] = new_data[id]
        if rd_position == 'after':
            if end not in rd_lookup[rd_position][unit_pos]:
                rd_lookup[rd_position][unit_pos][end] = {}
            if id.find('rdt') == 0:
                rd_lookup[rd_position][unit_pos][end]['rdt'] = new_data[id]
            elif id.find('rd') == 0:
                rd_lookup[rd_position][unit_pos][end]['rd'] = new_data[id]
    return rd_lookup


# TODO: probably can't trust that users will do the right thing with spaces and pc and
#       line breaks so best do checks for that when splitting the word list
# TODO: get full list of pc for basetext from SOAS for above

def construct_new_apparatus(collation_structure, new_data, linebreak_units,
                            no_linebreak_before_rd_units, languages, types):
    waiting_for_word = None
    all_keys = [*new_data.keys()]
    ordered_new_data = [x for x in all_keys if x.find('variantunit_') == 0]
    ordered_new_data.sort(key=lambda x: int(x.split('_')[1]))
    ordered_new_ritual_directions = [x for x in all_keys if x.find('rd') == 0]
    rd_lookup = make_rd_lookup(ordered_new_ritual_directions, new_data)
    current_index = 0
    overtext_index = 2

    sample_token = collation_structure['overtext'][0]['tokens'][0]
    new_overtext_tokens = []
    for id in ordered_new_data:
        rds = None
        unit_pos, start, end = get_details_from_id(id)
        language = languages['language_select_{}'.format(unit_pos)]
        try:
            type = types['type_select_{}'.format(unit_pos)]
        except KeyError:
            type = None
        orig_start = start
        orig_end = end
        overtext_section = [x for x in new_data[id].strip().split(' ') if x != '']

        # set start
        if len(overtext_section) == 0:
            if current_index % 2 == 1:
                start = current_index
            else:
                start = current_index + 1
        elif current_index % 2 == 1:
            start = current_index + 1
        else:
            start = current_index + 2
        # set end
        if len(overtext_section) == 0:
            end = start
        else:
            end = start + (2*(len(overtext_section)-1))
        current_index = end

        collation_structure['apparatus'][unit_pos]['start'] = start
        collation_structure['apparatus'][unit_pos]['end'] = end
        if unit_pos in linebreak_units:
            collation_structure['apparatus'][unit_pos]['linebreak_after'] = True
        else:
            collation_structure['apparatus'][unit_pos]['linebreak_after'] = False

        if len(overtext_section) == 0:
            rds = None
            if 'before' in rd_lookup:
                try:
                    rds = rd_lookup['before'][unit_pos][orig_start]
                except KeyError:
                    pass
                if rds:
                    waiting_for_word = rds
            rds = None
            if 'after' in rd_lookup:
                try:
                    rds = rd_lookup['after'][unit_pos][orig_end]
                except KeyError:
                    pass
                if rds:
                    for key in rds:
                        new_overtext_tokens[-1]['{}_after'.format(key)] = rds[key]
                    if unit_pos in no_linebreak_before_rd_units['before']:
                        new_overtext_tokens[-1]['no_linebreak_before_rd_before'] = True
        else:
            for word in overtext_section:
                # could actually just leave pc in the word string as we don't need to support show/hide options anymore
                pc_before, token, pc_after = strip_pc(word)
                new_token = {'t': token, 'index': overtext_index, 'verse': sample_token['verse'],
                             'siglum': sample_token['siglum'], 'reading': sample_token['reading'],
                             'original': token, 'language': language}
                if type is not None:
                    new_token['type'] = type
                if pc_before:
                    new_token['pc_before'] = pc_before
                if pc_after:
                    new_token['pc_after'] = pc_after
                rds = None
                if 'before' in rd_lookup:
                    if waiting_for_word:
                        for key in waiting_for_word:
                            new_token['{}_before'.format(key)] = waiting_for_word[key]
                        waiting_for_word = None
                    try:
                        rds = rd_lookup['before'][unit_pos][orig_start]
                    except KeyError:
                        pass
                    if rds:
                        for key in rds:
                            new_token['{}_before'.format(key)] = rds[key]
                        if unit_pos in no_linebreak_before_rd_units['before']:
                            new_token['no_linebreak_before_rd_before'] = True
                rds = None
                if 'after' in rd_lookup:
                    try:
                        rds = rd_lookup['after'][unit_pos][orig_end]
                    except KeyError:
                        pass
                    if rds:
                        for key in rds:
                            new_token['{}_after'.format(key)] = rds[key]
                        if unit_pos in no_linebreak_before_rd_units['after']:
                            new_token['no_linebreak_before_rd_after'] = True

                new_overtext_tokens.append(new_token)
                overtext_index += 2
    collation_structure['overtext'][0]['tokens'] = new_overtext_tokens
    collation_structure = fix_plus_readings(collation_structure)
    return fix_overlap_unit_indexes(collation_structure)


def fix_plus_readings(collation_structure):
    for unit in collation_structure['apparatus']:
        if int(unit['start']) % 2 == 1:
            overtext = None
        else:
            real_start = int(unit['start']/2)-1
            real_end = int(unit['end']/2)-1
            overtext = collation_structure['overtext'][0]['tokens'][real_start:real_end+1]
            overtext = ' '.join([x['original'] for x in overtext])
        if overtext is not None:
            if '⁺' in overtext:
                for reading in unit['readings']:
                    if 'text_string' in reading and reading['text_string'] == overtext.replace('⁺', ''):
                        reading['text_string'] = overtext
            else:
                for reading in unit['readings']:
                    if 'text_string' in reading and reading['text_string'].replace('⁺', '') == overtext:
                        reading['text_string'] = overtext
    return collation_structure


def fix_overlap_unit_indexes(collation_structure):
    app_lines = []
    for key in collation_structure.keys():
        if re.match(r'^apparatus\d+$', key):
            app_lines.append(key)
    if len(app_lines) == 0:
        # then there is nothing to do and we can return the original
        return collation_structure
    for line in app_lines:
        for unit in collation_structure[line]:
            id = unit['_id']
            start, end = get_new_start_end_for_overlap(id, collation_structure['apparatus'])
            if start is not None:
                unit['start'] = start
            if end is not None:
                unit['end'] = end
    return collation_structure


def get_new_start_end_for_overlap(overlap_id, main_units):
    start = None
    end = None
    for unit in main_units:
        if 'overlap_units' in unit:
            if overlap_id in unit['overlap_units'].keys():
                if start is None or unit['start'] < start:
                    start = unit['start']
                if end is None or unit['end'] > end:
                    end = unit['end']
    return start, end


def strip_pc(word):
    pc_list = ['P+.']
    # TODO: write this if it is required - full list of pc characters needed which is not straight forward
    return None, word, None


def unit_sort(unit):
    temp = unit.split('.')
    return temp[0], int(temp[1]), int(temp[2]), int(temp[3])


def get_languages():
    languages = [
        {'value': 'ae', 'name': 'Avestan'},
        {'value': 'gu', 'name': 'Gujarati'},
        {'value': 'fa', 'name': 'Persian'},
        {'value': 'fa-Phlv', 'name': 'New Persian in Pahlavi Script'},
        {'value': 'sa', 'name': 'Sanskrit'},
        {'value': 'sa-Jaina', 'name': 'Sanskrit in Jaina Nagari Script'},
        {'value': 'sa-Deva', 'name': 'Sanskrit in Devanagari Script'},
        {'value': 'ae-Avst', 'name': 'Avestan in Avestan Script'},
        {'value': 'ae-Phlv', 'name': 'Avestan in Pahlavi Script'},
        {'value': 'ae-fa', 'name': 'Avestan in New Persian Script'},
        {'value': 'ae-Gujr', 'name': 'Avestan in Gujarati Script'},
        {'value': 'pal-Avst"', 'name': 'Zoroastrian Middle Persian in Avestan Script'},
        {'value': 'pal-Phlv', 'name': 'Zoroastrian Middle Persian in Pahlavi Script'},
        {'value': 'pal-Gujr', 'name': 'Zoroastrian Middle Persian in Gujarati Script'},
        {'value': 'pal-Phli', 'name': 'Middle Persian in inscriptional Pahlavi Script'},
        {'value': 'pal-fa', 'name': 'Zoroastrian Middle Persian in New Persian Script'},
        {'value': 'gu-Arab', 'name': 'Gujarati in Arabic Script'},
        {'value': 'gu-Gujr', 'name': 'Gujarati in Gujarati Script'},
        {'value': 'gu-Jaina', 'name': 'Gujarati in Jaina Nagari Script'},
        {'value': 'gu-Deva', 'name': 'Gujarati in Devanagari Script'},
        {'value': 'gu-Avst', 'name': 'Gujarati in Avestan Script'},
        {'value': 'ar', 'name': 'Arabic'}
    ]
    return languages


@login_required
def select_editorial_text(request):

    login_details = get_login_status(request)
    post_login_url = request.path + '?' + request.GET.urlencode()

    data = {'page_title': 'Editorial Text Selection',
            'login_status': login_details,
            'post_logout_url': '/collation',
            'post_login_url': post_login_url,
            }

    if 'project' in request.session:
        try:
            project = Project.objects.filter(managing_editor=request.user.id).get(pk=request.session['project'])
        except Project.DoesNotExist:
            del request.session['project']
            return HttpResponseRedirect(reverse('collation:index'))
    else:
        return HttpResponseRedirect(reverse('collation:index'))

    if request.method == 'POST':

        context = request.POST.get('context', None)

        if context:
            query = Q()
            query &= Q(('status__in', ['approved', 'edited']))
            query &= Q(('project__id', request.session['project']))
            query &= Q(('context', context))
            results = Collation.objects.filter(query)

            if results.count() == 1:
                collation_unit = results[0]
            if results.count() == 2:
                if results[0].status == 'edited':
                    collation_unit = results[0]
                else:
                    collation_unit = results[1]
            new_data = {}
            linebreak_units = []
            no_linebreak_before_rd_units = {'before': [], 'after': []}
            languages = {}
            types = {}
            for key in request.POST:
                if key.find('variantunit') == 0 or key.find('rd') == 0:
                    new_data[key] = request.POST.get(key)
                if key.find('language_select_') == 0:
                    languages[key] = request.POST.get(key)
                if key.find('type_select_') == 0:
                    types[key] = request.POST.get(key)
                if key.find('linebreak_after_') == 0:
                    if request.POST.get(key) == 'true':
                        linebreak_units.append(int(key.replace('linebreak_after_', '')))
                if key.find('no_linebreak_before_rdafter_variantunit_') == 0:
                    if request.POST.get(key) == 'on':
                        unit_num = int(key.replace('no_linebreak_before_rdafter_variantunit_', ''))
                        no_linebreak_before_rd_units['after'].append(unit_num)
                if key.find('no_linebreak_before_rdbefore_variantunit_') == 0:
                    if request.POST.get(key) == 'on':
                        unit_num = int(key.replace('no_linebreak_before_rdbefore_variantunit_', ''))
                        no_linebreak_before_rd_units['before'].append(unit_num)

            collation_unit.structure = construct_new_apparatus(collation_unit.structure, new_data,
                                                               linebreak_units, no_linebreak_before_rd_units,
                                                               languages, types)
            if collation_unit.status != 'edited':
                collation_unit.status = 'edited'
                collation_unit.identifier = '{}_{}_{}'.format(collation_unit.context,
                                                              collation_unit.status,
                                                              collation_unit.project_id)
                collation_unit.id = None

            collation_unit.save()
            return redirect('/collation/edit?unit={}'.format(context))

    visible_context = 1
    basetext_units = transcription_models.CollationUnit.objects.filter(transcription__id=project.basetext.id)

    all_contexts = []
    for collation in basetext_units:
        all_contexts.append(collation.context)

    starting_unit = request.GET.get('unit', all_contexts[0])
    index_of_start = all_contexts.index(starting_unit)
    slice_start = max(0, index_of_start-visible_context)
    slice_end = min(index_of_start+1+visible_context, len(all_contexts))

    contexts = all_contexts[slice_start:slice_end]

    if index_of_start != 0:
        data['previous_url'] = '/collation/edit?unit={}'.format(all_contexts[index_of_start-1])
    if index_of_start < len(all_contexts) - 2:
        data['next_url'] = '/collation/edit?unit={}'.format(all_contexts[index_of_start+1])

    query = Q()
    query &= Q(('status__in', ['approved', 'edited']))
    query &= Q(('context__in', contexts))
    query &= Q(('project__id', request.session['project']))

    results = Collation.objects.filter(query)
    filtered = {}
    for result in results:
        if result.context in filtered and result.status == 'edited':
            filtered[result.context] = result
        elif result.context not in filtered:
            filtered[result.context] = result
    hits = []
    add_save = False
    for context in contexts:
        if context in filtered:
            add_save = True
            hits.append(filtered[context])
        else:
            hits.append({'context': context, 'structure': None})

    data['project_name'] = project.name
    data['save'] = add_save
    data['units'] = hits
    data['contexts'] = contexts
    data['target'] = starting_unit
    data['languages'] = get_languages()
    data['project_language'] = project.language
    if project.language != 'ae':
        data['types_required'] = True
        data['types'] = ['translation', 'commentary']
    else:
        data['types_required'] = False

    return render(request, 'collation/editorial.html', data)


@login_required
@permission_required(['collation.change_project',
                      ], raise_exception=True)
def set_supplement_range(request):

    login_details = get_login_status(request)
    post_login_url = request.path + '?' + request.GET.urlencode()

    data = {'page_title': 'Supplement Ranges',
            'login_status': login_details,
            'post_logout_url': '/collation',
            'post_login_url': post_login_url,
            }

    if 'project' in request.session:
        try:
            project = Project.objects.filter(managing_editor=request.user.id).get(pk=request.session['project'])
        except Project.DoesNotExist:
            del request.session['project']
            return HttpResponseRedirect(reverse('collation:index'))
    else:
        return HttpResponseRedirect(reverse('collation:index'))

    if request.method == 'POST':
        # save the data
        data = {}
        for key in request.POST:
            if key.find('siglum_') == 0:
                siglum = request.POST.get(key)
                unit_key = 'units_' + key.replace('siglum_', '')
                units = request.POST.getlist(unit_key)
                if len(units) > 0:
                    units.sort(key=unit_sort)
                    data[siglum] = units

        project.supplement_range = data
        project.save()
        return redirect('/collation/projectsummary/supplements')

    supplements = []
    for witness in project.witnesses.all():
        if re.match(r'^\d+S\d?$', witness.siglum):
            supplements.append(witness.siglum)

    basetext_units = []
    units = transcription_models.CollationUnit.objects.filter(transcription__id=project.basetext.id)
    for unit in units:
        basetext_units.append(unit.context)

    if project.supplement_range is None:
        supplement_range = {}
    else:
        supplement_range = project.supplement_range
    to_delete = []
    for key in supplement_range:
        if key not in supplements:
            to_delete.append(key)

    data['supplements'] = supplements
    for entry in supplements:
        if entry not in supplement_range:
            supplement_range[entry] = []
    data['data_to_delete'] = to_delete
    data['basetext_units'] = basetext_units
    data['supplement_range'] = supplement_range
    data['unit_length'] = len(basetext_units)
    data['project_name'] = project.name

    return render(request, 'collation/supplements.html', data)


def get_ceremony_list(data):
    ceremony_list = []
    if 'ceremony_mapping' not in data:
        return []
    for context in data['ceremony_mapping']:
        if data['ceremony_mapping'][context] is not None:
            for ceremony in data['ceremony_mapping'][context]['details']:
                if ceremony not in ceremony_list:
                    ceremony_list.append(ceremony)
    ceremony_list.sort(key=lambda x: (x[1:]))
    ceremony_list.sort(key=lambda x: (x[0]), reverse=True)
    return ceremony_list


def filter_mappings(mappings, search_field, search_text):
    new_mappings = {}
    search_regex_string = '^{}$'.format(search_text.replace('.', '\\.').replace('*', '.*?'))
    for context in mappings:
        if search_field == 'context':
            if re.match(search_regex_string, context):
                try:
                    new_mappings[context] = mappings[context]
                except KeyError:
                    pass
        else:
            for ceremony in mappings[context]['details']:
                if search_field == ceremony:
                    if mappings[context]['details'][ceremony] is not None:
                        if re.match(search_regex_string, mappings[context]['details'][ceremony]):
                            try:
                                new_mappings[context] = mappings[context]
                            except KeyError:
                                pass
    return new_mappings


@login_required
@permission_required(['collation.change_project',
                      ], raise_exception=True)
def delete_ceremony_mapping(request):
    if 'project' in request.session:
        try:
            project = Project.objects.filter(managing_editor=request.user.id).get(pk=request.session['project'])
        except Project.DoesNotExist:
            del request.session['project']
            return HttpResponseRedirect(reverse('collation:index'))
    else:
        return HttpResponseRedirect(reverse('collation:index'))

    context = request.POST.get('context')

    if project.ceremony_mapping is not None:
        try:
            del project.ceremony_mapping[context]
        except KeyError:
            pass
        project.save()

    return HttpResponseRedirect(reverse('collation:ceremonymapping'))


@login_required
@permission_required(['collation.change_project',
                      ], raise_exception=True)
def add_ceremony_mapping(request):
    if 'project' in request.session:
        try:
            project = Project.objects.filter(managing_editor=request.user.id).get(pk=request.session['project'])
        except Project.DoesNotExist:
            del request.session['project']
            return HttpResponseRedirect(reverse('collation:index'))
    else:
        return HttpResponseRedirect(reverse('collation:index'))

    if project.ceremony_mapping is None:
        mappings = {}
    else:
        mappings = project.ceremony_mapping

    context = request.POST.get('context')
    mappings[context] = {}
    book, chapter, stanza, line = context.split('.')
    mappings[context]['chapter_number'] = int(chapter)
    mappings[context]['stanza_number'] = int(stanza)
    mappings[context]['line_number'] = int(line)
    mappings[context]['details'] = {}
    for key in request.POST:
        if key.find('ceremony_') == 0:
            mappings[context]['details'][key.replace('ceremony_', '')] = request.POST.get(key)

    project.ceremony_mapping = mappings
    project.save()

    return HttpResponseRedirect(reverse('collation:ceremonymapping'))


@login_required
@permission_required(['collation.change_project',
                      ], raise_exception=True)
def save_ceremonies(request):
    if 'project' in request.session:
        try:
            project = Project.objects.filter(managing_editor=request.user.id).get(pk=request.session['project'])
        except Project.DoesNotExist:
            del request.session['project']
            return HttpResponseRedirect(reverse('collation:index'))
    else:
        return HttpResponseRedirect(reverse('collation:index'))
    ceremonies = []
    for key in request.POST:
        if key not in ['csrfmiddlewaretoken']:
            ceremonies.append(key)
    to_delete = []
    if project.ceremonies is not None:
        to_delete = [x for x in project.ceremonies if x not in ceremonies]
    project.ceremonies = ceremonies
    if len(to_delete) > 0:
        ceremony_mapping = project.ceremony_mapping
        if project.ceremony_mapping is not None:
            for entry in ceremony_mapping:
                for ceremony in to_delete:
                    ceremony_mapping[entry]['details']
                    try:
                        del ceremony_mapping[entry]['details'][ceremony]
                    except KeyError:
                        pass
        project.ceremony_mapping = ceremony_mapping
    project.save()
    return HttpResponseRedirect(reverse('collation:ceremonymapping'))


@login_required
def show_ceremony_mapping(request):
    login_details = get_login_status(request)
    post_login_url = request.path + '?' + request.GET.urlencode()

    if 'project' in request.session:
        try:
            project = Project.objects.filter(managing_editor=request.user.id).get(pk=request.session['project'])
        except Project.DoesNotExist:
            del request.session['project']
            return HttpResponseRedirect(reverse('collation:index'))
    else:
        return HttpResponseRedirect(reverse('collation:index'))

    ceremony_list = project.ceremonies
    if ceremony_list is None:
        ceremony_list = ['Y']

    fields = ['context']
    fields.extend([ceremony for ceremony in ceremony_list])

    search_field = None
    search_text = ''
    for key in request.GET:
        if key in fields and search_field is None:
            search_field = key
    if search_field is not None:
        search_text = request.GET.get(search_field)

    no_filter_link, remove_filter_button_label, remove_filter_required = get_filter_details(request.GET.copy(), fields)

    data = {'page_title': 'Ceremony Mapping',
            'login_status': login_details,
            'post_logout_url': '/collation',
            'post_login_url': post_login_url,
            'project_name': project.name,
            'project': project,
            'ceremony_list': ceremony_list,
            'ceremony_list_string': '|'.join(ceremony_list),
            'no_filter_link': '?{}'.format(no_filter_link.urlencode()),
            'remove_filter_required': remove_filter_required,
            'remove_filter_button_label': remove_filter_button_label,
            'search_field': search_field,
            'search_text': search_text
            }

    if project.ceremony_mapping is None:
        ceremony_mapping = {}
    else:
        ceremony_mapping = project.ceremony_mapping

    if search_field is not None and search_text is not None:
        ceremony_mapping = filter_mappings(ceremony_mapping, search_field, search_text)

    sorted_keys = list(ceremony_mapping.keys())
    sorted_keys.sort(key=unit_sort)
    sorted_mapping = {}
    for key in sorted_keys:
        sorted_mapping[key] = ceremony_mapping[key]
    data['data'] = sorted_mapping

    return render(request, 'collation/ceremony_mapping.html', data)


@login_required
def extract_notes(request):

    if 'task' in request.GET:
        post_login_url = request.path + '?' + request.GET.urlencode()
        login_details = get_login_status(request)
        task = AsyncResult(request.GET.get('task'))
        project = Project.objects.get(pk=request.GET.get('project'))
        data = {'page_title': 'Note Extractor',
                'project_name': project.name,
                'login_status': login_details,
                'post_logout_url': '/collation',
                'post_login_url': post_login_url,
                'result': task.result,
                'state': task.state,
                'task_id': task.task_id
                }
        return JsonResponse(data)

    # elif 'file' in request.GET:
    #     """
    #     If we have a GET request and 'file' in the request then we return the file to the user
    #     """
    #     post_login_url = request.path + '?' + request.GET.urlencode()
    #     login_details = get_login_status(request)
    #     task_id = request.GET.get('file')
    #     task = AsyncResult(task_id)
    #     data = data = {'page_title': 'Apparatus Generator',
    #                    'login_status': login_details,
    #                    'post_logout_url': '/collation',
    #                    'post_login_url': post_login_url,
    #                    'back_url': '/collation/transcriptionmanagement',
    #                    'back_text': 'Return to Transcription Management'}
    #     if task.result:
    #         path = task.result[2]
    #         project = task.result[3]
    #         # reconstruct the path here to make sure we are who we were when we created it!
    #         filepath = os.path.join(django_settings.EXPORT_BASE_DIR, project,
    #                                 str(request.user.id), 'notes', path)
    #         if ('/' not in task.result) and os.path.isfile(filepath):
    #             response = HttpResponse(content_type='text/plain')
    #             response['Content-Disposition'] = 'attachment; filename=' + path
    #             response.write(open(filepath, 'rb').read())
    #
    #             return response
    #         else:
    #             data['message'] = 'There was a problem with locating the file download.'
    #     else:
    #         data['message'] = 'The task id was not recognised.'
    #     return render(request, 'collation/download_problem.html', data)

    query = Q()
    transcription_id = request.POST.get('transcription-for-note-extraction')
    if transcription_id == 'All project transcriptions':
        project = Project.objects.get(pk=request.POST.get('project_id'))
        query &= Q(('identifier__in', project.witnesses.all().values_list('identifier', flat=True)))
    else:
        query &= Q(('identifier', transcription_id))
    transcriptions = transcription_models.Transcription.objects.filter(query)
    serializer = TranscriptionSerializer(transcriptions, many=True)
    data = serializer.data
    settings = {}
    path = os.path.join(request.POST.get('project_id'), str(request.user.id), 'notes')
    settings['path'] = path
    settings['project'] = request.POST.get('project_id')
    settings['email_addresses'] = [request.user.email]
    task = tasks.extract_notes.delay(data, settings)
    return HttpResponseRedirect('?task=' + task.task_id + '&project=' + request.POST.get('project_id'))


@login_required
def extract_ritual_directions(request):

    if 'task' in request.GET:
        post_login_url = request.path + '?' + request.GET.urlencode()
        login_details = get_login_status(request)
        task = AsyncResult(request.GET.get('task'))
        project = Project.objects.get(pk=request.GET.get('project'))
        data = {'page_title': 'Ritual Directions Extractor',
                'project_name': project.name,
                'login_status': login_details,
                'post_logout_url': '/collation',
                'post_login_url': post_login_url,
                'result': task.result,
                'state': task.state,
                'task_id': task.task_id
                }
        return JsonResponse(data)

    # elif 'file' in request.GET:
    #     """
    #     If we have a GET request and 'file' in the request then we return the file to the user
    #     """
    #     post_login_url = request.path + '?' + request.GET.urlencode()
    #     login_details = get_login_status(request)
    #     task_id = request.GET.get('file')
    #     task = AsyncResult(task_id)
    #     data = data = {'page_title': 'Ritual Directions Extractor',
    #                    'login_status': login_details,
    #                    'post_logout_url': '/collation',
    #                    'post_login_url': post_login_url,
    #                    'back_url': '/collation/transcriptionmanagement',
    #                    'back_text': 'Return to Transcription Management'}
    #     if task.result:
    #         path = task.result[2]
    #         project = task.result[3]
    #         # reconstruct the path here to make sure we are who we were when we created it!
    #         filepath = os.path.join(django_settings.EXPORT_BASE_DIR, project,
    #                                 str(request.user.id), 'ritual_directions', path)
    #         if ('/' not in task.result) and os.path.isfile(filepath):
    #             response = HttpResponse(content_type='text/plain')
    #             response['Content-Disposition'] = 'attachment; filename=' + path
    #             response.write(open(filepath, 'rb').read())
    #
    #             return response
    #         else:
    #             data['message'] = 'There was a problem with locating the file download.'
    #     else:
    #         data['message'] = 'The task id was not recognised.'
    #     return render(request, 'collation/download_problem.html', data)

    query = Q()
    transcription_id = request.POST.get('transcription-for-rd-extraction')
    if transcription_id == 'All project transcriptions':
        project = Project.objects.get(pk=request.POST.get('project_id'))
        query &= Q(('identifier__in', project.witnesses.all().values_list('identifier', flat=True)))
    else:
        query &= Q(('identifier', transcription_id))
    transcriptions = transcription_models.Transcription.objects.filter(query)
    serializer = TranscriptionSerializer(transcriptions, many=True)
    data = serializer.data
    settings = {}
    path = os.path.join(request.POST.get('project_id'), str(request.user.id), 'ritual_directions')
    settings['path'] = path
    settings['project'] = request.POST.get('project_id')
    settings['email_addresses'] = [request.user.email]
    task = tasks.extract_ritual_directions.delay(data, settings)
    return HttpResponseRedirect('?task=' + task.task_id + '&project=' + request.POST.get('project_id'))


@login_required
def get_latex(request):

    if 'task' in request.GET:
        post_login_url = request.path + '?' + request.GET.urlencode()
        login_details = get_login_status(request)
        task = AsyncResult(request.GET.get('task'))
        project = Project.objects.get(pk=request.GET.get('project'))
        data = {'page_title': 'Latex Transcription Generator',
                'project_name': project.name,
                'login_status': login_details,
                'post_logout_url': '/collation',
                'post_login_url': post_login_url,
                'result': task.result,
                'state': task.state,
                'task_id': task.task_id
                }
        return JsonResponse(data)

    # elif 'file' in request.GET:
    #     """
    #     If we have a GET request and 'file' in the request then we return the file to the user
    #     """
    #     post_login_url = request.path + '?' + request.GET.urlencode()
    #     login_details = get_login_status(request)
    #     task_id = request.GET.get('file')
    #     task = AsyncResult(task_id)
    #     data = {'page_title': 'Latex Transcription Generator',
    #             'login_status': login_details,
    #             'post_logout_url': '/collation',
    #             'post_login_url': post_login_url,
    #             'back_url': '/collation/transcriptionmanagement',
    #             'back_text': 'Return to Transcription Management'}
    #     if task.result:
    #         path = task.result[2]
    #         project = task.result[3]
    #         # reconstruct the path here to make sure we are who we were when we created it!
    #         filepath = os.path.join(django_settings.EXPORT_BASE_DIR, project,
    #                                 str(request.user.id), 'latex-transcription', path)
    #         if ('/' not in task.result) and os.path.isfile(filepath):
    #             response = HttpResponse(content_type='text/plain')
    #             response['Content-Disposition'] = 'attachment; filename=' + path
    #             response.write(open(filepath, 'rb').read())
    #
    #             return response
    #         else:
    #             data['message'] = 'There was a problem with locating the file download.'
    #     else:
    #         data['message'] = 'The task id was not recognised.'
    #     return render(request, 'collation/download_problem.html', data)

    settings = {}
    transcription_src = request.POST.get('latex_src', None)
    path = os.path.join(request.POST.get('project_id'), str(request.user.id), 'latex-transcription')
    settings['path'] = path
    settings['project_id'] = request.POST.get('project_id')
    settings['email_addresses'] = [request.user.email]
    task = tasks.generate_transcription_latex.delay(transcription_src, settings)
    return HttpResponseRedirect('?task=' + task.task_id + '&project=' + request.POST.get('project_id'))
