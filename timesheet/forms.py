from django import forms
from .models import Timesheet
from django.utils.translation import gettext_lazy as _


class TimesheetForm(forms.ModelForm):
    HOURS_CHOICES = [(i, i) for i in range(0, 9)]  # Choices from 0 to 8

    hours_worked = forms.ChoiceField(choices=HOURS_CHOICES, widget=forms.Select(attrs={'class': 'form-select', 'placeholder': _('Select number of hours')}))

    class Meta:
        model = Timesheet
        # fields = '__all__'
        fields = ['user', 'fundssource', 'date', 'hours_worked', 'activity', 'description']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'datepicker', 'placeholder': 'Select date'}),
            'fundssource': forms.Select(attrs={'class': 'form-control', 'placeholder': _('Choose funding source')}),
            'activity': forms.Select(attrs={'class': 'form-control', 'placeholder': _('Choose activity')}),
            'description': forms.TextInput(attrs={'class': 'form-control timesheet-description', 'rows': 4, 'placeholder': _('Describe activity')}), }

    def __init__(self, *args, selected_date=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected_date = selected_date
