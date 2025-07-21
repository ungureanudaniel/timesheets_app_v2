from django import forms
from django.utils.translation import gettext_lazy as _

class ReportPeriodForm(forms.Form):
    PERIOD_CHOICES = [
        ('weekly', _('Weekly')),
        ('monthly', _('Monthly'))
    ]
    REPORT_TYPE_CHOICES = [
        ('summary', _('Summary Report')),
        ('detailed', _('Detailed Report'))
    ]
    
    period = forms.ChoiceField(
        choices=PERIOD_CHOICES,
        widget=forms.RadioSelect,
        initial='weekly',
        label=_('Report Period')
    )
    report_type = forms.ChoiceField(
        choices=REPORT_TYPE_CHOICES,
        widget=forms.RadioSelect,
        initial='summary',
        label=_('Report Type')
    )