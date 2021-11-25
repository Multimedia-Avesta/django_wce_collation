from django import forms
from collation.models import Project


class CollationProjectForm(forms.ModelForm):

    identifier = forms.CharField(widget=forms.TextInput,
                                 help_text='This must be unique within the database.')
    name = forms.CharField(widget=forms.TextInput,
                           help_text='This will be shown in the header when working in the project.')

    class Meta:
        model = Project
        # these are done automatically on save hook in api app or are set more easily in the project summary page
        exclude = ['version_number',
                   'created_time', 'created_by',
                   'last_modified_time', 'last_modified_by',
                   'witnesses', 'basetext']
