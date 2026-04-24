from django.utils import timezone
from django import forms
from users.auth_backend import User
from .models import Timesheet
from django.utils.translation import gettext_lazy as _


class TimesheetForm(forms.ModelForm):
    
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('last_name'),
        required=False, # We handle the requirement in the view/clean
        label=_("Employee"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control',
            'id': 'timesheet-date'
        }),
        initial=timezone.now().date(),
        label=_("Date")
    )
    
    class Meta:
        model = Timesheet
        # Explicitly excluded 'user' so the form doesn't fail validation 
        # when the user field is missing from the POST data
        fields = ['fundssource', 'date', 'start_time', 'end_time', 'activity', 'description', 'user']
        widgets = {
            'fundssource': forms.Select(attrs={'class': 'form-control', 'placeholder': _('Funds Source')}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control', 'placeholder': _('Start time')}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control', 'placeholder': _('End time')}),
            'activity': forms.Select(attrs={'class': 'form-control', 'placeholder': _('Select activity')}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Enter description')}), 
        }

    def __init__(self, *args, **kwargs):
        requesting_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if requesting_user and not requesting_user.is_superuser:
            self.fields['user'].widget = forms.HiddenInput()
            self.fields['user'].required = False
 
        if not self.initial.get('date'):
            self.initial['date'] = timezone.now().date().isoformat()