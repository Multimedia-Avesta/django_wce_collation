import datetime
from django.db import models
from django.contrib import admin
from django.forms import CheckboxSelectMultiple
from collation.models import Project
from collation.forms import CollationProjectForm


class ProjectAdmin(admin.ModelAdmin):

    form = CollationProjectForm
    formfield_overrides = {
        models.ManyToManyField: {'widget': CheckboxSelectMultiple, 'help_text': 'Select all users who need access.'}
    }

    def save_model(self, request, obj, form, change):
        if obj.version_number is None:
            obj.version_number = 1
        else:
            obj.version_number += 1
        if obj.id is not None:
            # then we are editing
            if hasattr(request.user, 'full_name') and request.user.full_name != '':
                obj.last_modified_by = request.user.full_name
            else:
                obj.last_modified_by = request.user.username
            obj.last_modified_time = datetime.datetime.now()
        else:
            # this is being created
            if hasattr(request.user, 'full_name') and request.user.full_name != '':
                obj.created_by = request.user.full_name
            else:
                obj.created_by = request.user.username
            obj.created_time = datetime.datetime.now()

        super().save_model(request, obj, form, change)


admin.site.register(Project, ProjectAdmin)
