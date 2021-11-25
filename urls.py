from django.conf.urls import re_path
from . import views


app_name = 'collation'
urlpatterns = [
    re_path(r'^$', views.index, name='index'),
    re_path(r'projectselect', views.project_select, name='projectselect'),
    re_path(r'projectsummary/supplements', views.set_supplement_range, name='supplementrange'),
    re_path(r'projectsummary/ceremonymapping/add', views.add_ceremony_mapping, name='editceremonymapping'),
    re_path(r'projectsummary/ceremonymapping/delete', views.delete_ceremony_mapping, name='deleteceremonymapping'),
    re_path(r'projectsummary/ceremonymapping', views.show_ceremony_mapping, name='ceremonymapping'),
    re_path(r'projectsummary/ceremonies/add', views.save_ceremonies, name='saveceremonies'),
    re_path(r'projectsummary', views.project_summary, name='projectsummary'),
    re_path(r'latex/?', views.get_latex, name="latex"),
    re_path(r'transcriptionmanagement', views.transcription_management, name='transcriptionmanagement'),
    re_path(r'collationserver', views.collate, name="collate"),
    re_path(r'whoarethey', views.resolve_editor_names, name="resolveeditornames"),
    re_path(r'apparatus', views.get_apparatus, name="getapparatus"),
    re_path(r'collationdata', views.get_collation_data, name="getdata"),
    re_path(r'applysettings', views.apply_settings, name="applysettings"),
    re_path(r'edit', views.select_editorial_text, name="selecteditorialtext"),
    re_path(r'ritualdirections', views.extract_ritual_directions, name="extractritualdirections"),
    re_path(r'notes', views.extract_notes, name="extractnotes"),
]
