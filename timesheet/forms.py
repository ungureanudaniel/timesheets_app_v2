from django.utils import timezone
from django import forms
from .models import Timesheet
from django.utils.translation import gettext_lazy as _


class TimesheetForm(forms.ModelForm):
    """Form for creating and updating timesheets."""

    # Add a date field with today as default
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
        fields = '__all__'
        # fields = ['fundssource', 'date', 'start_time', 'end_time', 'activity', 'description']
        widgets = {
            'fundssource': forms.Select(attrs={'class': 'form-control', 'placeholder': _('Choose funding source')}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'activity': forms.Select(attrs={'class': 'form-control', 'placeholder': _('Choose activity')}),
            'description': forms.TextInput(attrs={'class': 'form-control timesheet-description', 'rows': 4, 'placeholder': _('Describe activity')}), }

    def __init__(self, *args, selected_date=None, **kwargs):
        super().__init__(*args, **kwargs)
        if selected_date:
            # Set initial value for the date field
            self.fields['date'].initial = selected_date

        # If editing an existing timesheet, use its date
        if self.instance and self.instance.pk:
            self.fields['date'].initial = self.instance.date
