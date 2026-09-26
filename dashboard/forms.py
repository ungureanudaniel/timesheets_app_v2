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
    week = forms.ChoiceField(
        choices=get_week_choices(),
        widget=forms.Select(
            attrs={'class': 'form-select form-select-sm week-select'}
        ),
        label="Săptămâna",
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
        label="Activitate",
    )

    class Meta:
        model = ActivityProgram
        fields = [
            'registration_nr',
            'week',
            'assigned_rangers',
        ]
        widgets = {
            'registration_nr': forms.TextInput(
                attrs={'class': 'form-control form-control-sm'}
            ),
            # 'activity_title': forms.TextInput(
            #     attrs={
            #         'class': 'form-control form-control-sm activity-title-input',
            #         'placeholder': 'Titlu activitate',
            #     }
            # ),
            # 'assigned_rangers': forms.CheckboxSelectMultiple(
            #     attrs={'class': 'form-check-input'}
            # ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Pre-select the activity instance matching the current activity_code
        if self.instance and self.instance.activity_code:
            current_activity = Activity.objects.filter(
                code=self.instance.activity_code
            ).first()
            if current_activity:
                self.fields['activity'].initial = current_activity.pk

    def save(self, commit=True):
        instance = super().save(commit=False)
        selected_activity = self.cleaned_data.get('activity')

        if selected_activity:
            instance.activity_code = selected_activity.code

        if commit:
            instance.save()
            self.save_m2m()

        return instance

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