from django import forms
from .models import ActivityProgram
import datetime
from django.utils.translation import gettext_lazy as _


class ActivityProgramForm(forms.ModelForm):
    week_choices = [(i, i) for i in range(datetime.date.today().isocalendar()[1] - 3, datetime.date.today().isocalendar()[1] + 3)]  # Choices from 0 to 8

    week = forms.ChoiceField(choices=week_choices, widget=forms.Select(attrs={'class': 'form-select', 'placeholder': _('Select week number')}))

    class Meta:
        model = ActivityProgram
        fields = ['user', 'registration_nr', 'registration_date', 'week', 'activity_title']
        widgets = {
            # 'week': forms.Select(attrs={'class': 'form-control', 'placeholder': _('Choose funding source')}),
            'registration_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'placeholder': 'Select date'}),
            'activity_title': forms.Select(attrs={'class': 'form-control', 'placeholder': _('Choose funding source')}),
            'registration_nr': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Describe activity')}), }
