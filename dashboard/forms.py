from django import forms
from .models import ActivityProgram
from timesheet.models import Activity, FundsSource
import datetime
from django.utils import timezone
from .utils import get_week_choices
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.forms import formset_factory

User = get_user_model()

class PALActivitiesUploadForm(forms.Form):
    file = forms.FileField(
        label='Upload Excel file',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )


class PALActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['code', 'name']
        widgets = {
            'code': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': _('Insert activity code')}
            ),
            'name': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': _('Enter activity name')}
            ),
        }


class BulkActivityProgramForm(forms.ModelForm):
    ranger_id = forms.IntegerField(widget=forms.HiddenInput())
    ranger_name = forms.CharField(widget=forms.HiddenInput(), required=False)
    model = ActivityProgram
    registration_nr = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(
            attrs={'class': 'form-control form-control-sm'}
        ),
    )
    week = forms.ChoiceField(
        choices=get_week_choices(),
        widget=forms.NumberInput(
            attrs={'class': 'form-control form-control-sm'}
        )
    )

    activity = forms.ModelChoiceField(
        queryset=Activity.objects.all().order_by('code'),
        required=True,
        empty_label='-- Selectează Activitatea --',
        widget=forms.Select(
            attrs={
                'class': 'form-select form-select-sm activity-select',
                'onchange': 'autoFillTitle(this)',
            }
        ),
    )

    activity_title = forms.CharField(
        max_length=300,
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm activity-title-input',
                'placeholder': 'Titlu activitate',
            }
        ),
    )


BulkActivityProgramFormSet = forms.formset_factory(
    BulkActivityProgramForm, extra=0
)


class ActivityProgramUpdateForm(forms.ModelForm):
    class Meta:
        model = ActivityProgram
        fields = ['registration_nr', 'registration_date', 'year', 'week', 'chief_ranger', 'director', 'accountant']
        widgets = {
        'year': forms.NumberInput(
            attrs={'class': 'form-control', 'min': 2020, 'max': 2100}
        ),
        'week': forms.NumberInput(
            attrs={'class': 'form-control', 'min': 1, 'max': 53}
        ),
        'status': forms.Select(attrs={'class': 'form-select'}),
        'chief_ranger': forms.Select(attrs={'class': 'form-select'}),
        'director': forms.Select(attrs={'class': 'form-select'}),
        'accountant': forms.Select(attrs={'class': 'form-select'}),
    }


class FundsSourceForm(forms.ModelForm):
    """Form for creating and updating funds sources."""
    class Meta:
        model = FundsSource
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': _('Enter fund source name')}
            ),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Insert fund source description')}
            ),
            
        }