from django.utils import timezone
from django import forms
from .models import Timesheet
from django.utils.translation import gettext_lazy as _


class TimesheetForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control',
            'id': 'timesheet-date'
        }),
        initial=timezone.now().date()
    )

    class Meta:
        model = Timesheet
        # Explicitly excluded 'user' so the form doesn't fail validation 
        # when the user field is missing from the POST data
        fields = ['fundssource', 'date', 'start_time', 'end_time', 'activity', 'description']
        widgets = {
            'fundssource': forms.Select(attrs={'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'activity': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), 
        }

    def __init__(self, *args, **kwargs):
        selected_date = kwargs.pop('selected_date', None)
        super().__init__(*args, **kwargs)
        if selected_date:
            self.fields['date'].initial = selected_date