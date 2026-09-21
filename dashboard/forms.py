from django import forms
from .models import ActivityProgram
from timesheet.models import Activity, FundsSource
import datetime
from django.utils import timezone
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


class BulkActivityProgramForm(forms.Form):
    ranger_id = forms.IntegerField(widget=forms.HiddenInput())
    ranger_name = forms.CharField(widget=forms.HiddenInput(), required=False)
    
    registration_nr = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm'}))
    week = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm'}))
    activity_code = forms.CharField(max_length=6, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'}))
    activity_title = forms.CharField(max_length=300, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'}))

BulkActivityProgramFormSet = formset_factory(BulkActivityProgramForm, extra=0)


class BulkAssignActivityForm(forms.Form):
    # Select directly from the existing Activity model
    preset_activity = forms.ModelChoiceField(
        queryset=Activity.objects.all(),
        required=False,
        empty_label="-- Selectează din listă sau adaugă manual mai jos --",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_preset_activity'})
    )

    registration_nr = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    week = forms.IntegerField(
        initial=timezone.now().isocalendar()[1],
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    activity_code = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_activity_code'})
    )
    activity_title = forms.CharField(
        max_length=300,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_activity_title'})
    )

    assigned_rangers = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('username'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label="Selectează Rangerii"
    )
# class ActivityProgramForm(forms.ModelForm):
#     """Form for creating and updating activity programs."""
#     week = forms.ChoiceField(
#         widget=forms.Select(attrs={'class': 'form-select'}),
#         label=_('Week Number')
#     )

#     class Meta:
#         model = ActivityProgram
#         fields = ['user', 'registration_nr', 'registration_date', 'week', 'activity_title']
#         widgets = {
#             'registration_date': forms.DateInput(
#                 attrs={'type': 'date', 'class': 'form-control', 'placeholder': _('Select date')}
#             ),
#             'activity_title': forms.Textarea(
#                 attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Insert activity title')}
#             ),
#             'registration_nr': forms.TextInput(
#                 attrs={'class': 'form-control', 'placeholder': _('Enter registration number')}
#             ),
#             'user': forms.TextInput(
#                 attrs={'class': 'form-control', 'placeholder': _('Enter user name')}
#             ),
#         }

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         current_week = datetime.date.today().isocalendar()[1]
#         year_weeks = range(
#             max(1, current_week - 3),  # Prevent week number < 1
#             min(53, current_week + 4)  # Prevent week number > 52
#         )
#         self.fields['week'].choices = [
#             (i, f"Week {i}") for i in year_weeks
#         ]


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