from django.utils import timezone
from django import forms
from users.auth_backend import User
from .models import Timesheet
from django.utils.translation import gettext_lazy as _


from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from .models import Timesheet
from datetime import datetime, timedelta

class TimesheetForm(forms.ModelForm):
    User = get_user_model()
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('last_name'),
        required=False,
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
        fields = ['fundssource', 'date', 'start_time', 'end_time', 'activity', 'description', 'user']
        widgets = {
            'fundssource': forms.Select(attrs={'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'activity': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), 
        }

    def __init__(self, *args, **kwargs):
        # 1. Capture the user passed from the view
        self.requesting_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # 2. UI Logic for Managers vs Employees
        if self.requesting_user and not self.requesting_user.is_superuser:
            self.fields['user'].widget = forms.HiddenInput()
            self.fields['user'].required = False
 
        if not self.initial.get('date'):
            self.initial['date'] = timezone.now().date().isoformat()

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        # Determine which user we are checking for (selected in form or current user)
        target_user = cleaned_data.get('user') or self.requesting_user

        if date and start_time and end_time and target_user:
            # 1. Calculate duration of the current input
            start_dt = datetime.combine(date, start_time)
            end_dt = datetime.combine(date, end_time)
            
            if end_dt <= start_dt:
                raise forms.ValidationError(_("End time must be after start time."))

            current_entry_hours = (end_dt - start_dt).total_seconds() / 3600
            day_of_week = date.weekday()

            # 2. Query other entries for this day to check the cumulative total
            existing_entries = Timesheet.objects.filter(user=target_user, date=date)
            
            # If editing, don't count the current record against the total
            if self.instance.pk:
                existing_entries = existing_entries.exclude(pk=self.instance.pk)

            existing_hours = 0
            for ts in existing_entries:
                # Basic duration calc for existing rows
                s = datetime.combine(date, ts.start_time)
                e = datetime.combine(date, ts.end_time)
                if e < s: e += timedelta(days=1)
                existing_hours += (e - s).total_seconds() / 3600

            total_day_hours = existing_hours + current_entry_hours

            # 3. Validation Rules
            if day_of_week <= 3:  # Mon-Thu
                limit = 8.5
                day_name = _("Monday-Thursday")
            elif day_of_week == 4:  # Friday
                limit = 6.0
                day_name = _("Friday")
                if end_time > datetime.strptime("14:00", "%H:%M").time():
                    raise forms.ValidationError(_("Friday work must end by 14:00."))
            else:
                limit = 0  # Assuming no weekend work, adjust if needed

            # 4. Final check against the cap
            if total_day_hours > limit:
                remaining = max(0, limit - existing_hours)
                rem_h = int(remaining)
                rem_m = int((remaining * 60) % 60)
                
                raise forms.ValidationError(
                    _("Limit exceeded for %(day)s. You have %(exist)s recorded. "
                      "You can only add %(rem_h)sh %(rem_m)sm more.") % {
                        'day': day_name,
                        'exist': self._format_hours(existing_hours),
                        'rem_h': rem_h,
                        'rem_m': rem_m
                    }
                )

        return cleaned_data

    def _format_hours(self, decimal_hours):
        h = int(decimal_hours)
        m = int((decimal_hours * 60) % 60)
        return f"{h}h {m:02d}m"