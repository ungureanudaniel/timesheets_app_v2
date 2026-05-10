from django import forms
from django.utils.translation import gettext_lazy as _

from users.models import CustomUser

class ReportPeriodForm(forms.Form):
    # 1. Expanded Period Choices
    PERIOD_CHOICES = [
        ('today', _('Today')),
        ('current_week', _('Current Week')),
        ('last_week', _('Last Week')),
        ('current_month', _('Current Month')),
        ('last_month', _('Last Month')),
        ('current_year', _('Current Year')),
        ('last_year', _('Last Year')),
        ('custom', _('Custom Range')),
    ]
    
    # Define the field with an empty queryset initially to prevent leaks
    user = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.none(), 
        required=False, 
        label=_("Employee"),
        widget=forms.CheckboxSelectMultiple()
    )
    period = forms.ChoiceField(choices=PERIOD_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    custom_start_date = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    custom_end_date = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        # Pop the requesting user passed from the View
        request_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if request_user:
            # 2. Check if the user is a Manager or Admin
            is_manager = request_user.is_staff or request_user.groups.filter(name='Managers').exists()
            
            if is_manager:
                # Fill the dropdown with all active employees for Managers
                self.fields['user'].queryset = CustomUser.objects.filter(is_active=True).order_by('last_name')
            else:
                # Regular users only see themselves
                self.fields['user'].queryset = CustomUser.objects.filter(id=request_user.id)
                self.fields['user'].initial = [request_user.id]
                self.fields['user'].widget = forms.HiddenInput()