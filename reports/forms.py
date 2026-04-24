from django import forms
from django.utils.translation import gettext_lazy as _

from users.models import CustomUser

class ReportPeriodForm(forms.Form):
    PERIOD_CHOICES = [('weekly', _('Weekly')), ('monthly', _('Monthly')), ('custom', _('Custom'))]
    TYPE_CHOICES = [('summary', _('Summary')), ('detailed', _('Detailed'))]
    
    user = forms.ModelChoiceField(queryset=CustomUser.objects.all(), required=False, label=_("Employee"))
    period = forms.ChoiceField(choices=PERIOD_CHOICES)
    report_type = forms.ChoiceField(choices=TYPE_CHOICES)
    custom_start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    custom_end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # If not admin/manager, hide user field and default to self
        if user and not user.is_staff:
            self.fields['user'].widget = forms.HiddenInput()
            self.fields['user'].initial = user.id