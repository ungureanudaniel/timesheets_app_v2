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
        ('custom', _('Custom Range')),
    ]
    TYPE_CHOICES = [('summary', _('Summary')), ('detailed', _('Detailed'))]
    
    # Define the field with an empty queryset initially to prevent leaks
    user = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(), 
        required=False, 
        label=_("Employee"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    period = forms.ChoiceField(choices=PERIOD_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    report_type = forms.ChoiceField(choices=TYPE_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
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
                self.fields['user'].empty_label = _("Select an employee")
            else:
                # Regular users only see themselves
                self.fields['user'].queryset = CustomUser.objects.filter(id=request_user.id)
                self.fields['user'].initial = request_user.id
                self.fields['user'].widget = forms.HiddenInput()