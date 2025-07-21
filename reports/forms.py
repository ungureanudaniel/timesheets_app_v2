from django import forms

class ReportPeriodForm(forms.Form):
    PERIOD_CHOICES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')
    ]
    REPORT_TYPE_CHOICES = [
        ('summary', 'Summary Report'),
        ('detailed', 'Detailed Report')
    ]
    
    period = forms.ChoiceField(
        choices=PERIOD_CHOICES,
        widget=forms.RadioSelect,
        initial='weekly'
    )
    report_type = forms.ChoiceField(
        choices=REPORT_TYPE_CHOICES,
        widget=forms.RadioSelect,
        initial='summary'
    )