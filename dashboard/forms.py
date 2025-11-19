from django import forms
from .models import ActivityProgram
from timesheet.models import Activity, FundsSource
import datetime
from django.utils.translation import gettext_lazy as _


class PALActivitiesUploadForm(forms.Form):
    file = forms.FileField(
        label='Upload Excel file',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

class ActivityProgramForm(forms.ModelForm):
    """Form for creating and updating activity programs."""
    week = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Week Number')
    )

    class Meta:
        model = ActivityProgram
        fields = ['user', 'registration_nr', 'registration_date', 'week', 'activity_title']
        widgets = {
            'registration_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control', 'placeholder': _('Select date')}
            ),
            'activity_title': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Insert activity title')}
            ),
            'registration_nr': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': _('Enter registration number')}
            ),
            'user': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': _('Enter user name')}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_week = datetime.date.today().isocalendar()[1]
        year_weeks = range(
            max(1, current_week - 3),  # Prevent week number < 1
            min(53, current_week + 4)  # Prevent week number > 52
        )
        self.fields['week'].choices = [
            (i, f"Week {i}") for i in year_weeks
        ]


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