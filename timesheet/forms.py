from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from .models import Timesheet, FundsSource
from dashboard.models import Activity  # Ensure this import matches your app structure
from datetime import date, datetime, timedelta

class TimesheetForm(forms.ModelForm):
    User = get_user_model()
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('last_name'),
        required=False,
        label=_("Employee"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    is_annual_holiday = forms.BooleanField(
        required=False, 
        label=_("Concediu de Odihnă"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    is_sick_leave = forms.BooleanField(
        required=False, 
        label=_("Concediu Medical"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    is_family_event = forms.BooleanField(
        required=False, 
        label=_("Eveniment Familial"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
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
    start_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        label=_("Start Time")
    )
    end_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        label=_("End Time")
    )

    class Meta:
        model = Timesheet
        fields = ['fundssource', 'date', 'start_time', 'end_time', 'activity', 'description', 'submitted_to_smart', 'user']
        widgets = {
            'fundssource': forms.Select(attrs={'class': 'form-control'}),
            'activity': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'submitted_to_smart': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.requesting_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk and self.instance.activity:
            activity_name = self.instance.activity.name.upper() if hasattr(self.instance.activity, 'name') else str(self.instance.activity).upper()
            is_special = any(x in activity_name for x in ['CONCEDIU', 'ANNUAL', 'SICK', 'EVENIMENT', 'FAMILY'])
            self.fields['activity'].required = not is_special
            self.fields['fundssource'].required = not is_special
        else:
            # For new entries, let the JavaScript handle the visual unlocking/locking. 
            # We keep them required=True here so Django's engine catches empty values natively!
            self.fields['activity'].required = True
            self.fields['fundssource'].required = True
        
        if self.instance and self.instance.date:
            self.fields['date'].initial = self.instance.date
            target_date = self.instance.date
        else:
            target_date = kwargs.get('initial', {}).get('date') or timezone.localtime(timezone.now()).date()
            self.fields['date'].initial = target_date

        if not self.instance or not self.instance.pk:
            day_of_week = target_date.weekday()
            self.fields['start_time'].initial = "08:00"
            if day_of_week == 4:  # Friday
                self.fields['end_time'].initial = "14:00"
            else:                 # Monday - Thursday
                self.fields['end_time'].initial = "16:30"

        # Active Switch Memory Checklist on Edit
        if self.instance and self.instance.pk and self.instance.activity:
            activity_name = self.instance.activity.name.upper() if hasattr(self.instance.activity, 'name') else str(self.instance.activity).upper()
            if 'CONCEDIU ANUAL' in activity_name or 'ANNUAL' in activity_name:
                self.fields['is_annual_holiday'].initial = True
            elif 'CONCEDIU MEDICAL' in activity_name or 'SICK' in activity_name:
                self.fields['is_sick_leave'].initial = True
            elif 'EVENIMENT FAMILIAL' in activity_name or 'FAMILY' in activity_name:
                self.fields['is_family_event'].initial = True

        if self.requesting_user and not self.requesting_user.is_superuser:
            self.fields['user'].widget = forms.HiddenInput()
            self.fields['user'].required = False
 
        if self.instance and self.instance.pk:
            self.fields['user'].initial = self.instance.user_id
        else:
            if self.requesting_user:
                self.fields['user'].initial = self.requesting_user.id

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        is_holiday = cleaned_data.get('is_annual_holiday')
        is_sick = cleaned_data.get('is_sick_leave')
        is_family_event = cleaned_data.get('is_family_event')
        
        is_special_leave = bool(is_holiday or is_sick or is_family_event)
        
        if is_special_leave:
            # 💡 FIX: Using the public self.errors dictionary clears the VS Code linter warnings completely
            if 'fundssource' in self.errors:
                del self.errors['fundssource']
            if 'activity' in self.errors:
                del self.errors['activity']
        else:
            # Standard work entry checks
            if not cleaned_data.get('fundssource'):
                self.add_error('fundssource', _("Vă rugăm să selectați o sursă de finanțare."))
            if not cleaned_data.get('activity'):
                self.add_error('activity', _("Vă rugăm să selectați tipul de activitate."))
                
            if self.errors:
                return cleaned_data

        checked_leaves_count = sum([bool(is_holiday), bool(is_sick), bool(is_family_event)])
        if checked_leaves_count > 1:
            raise forms.ValidationError(_("Nu puteți bifa mai multe tipuri de evenimente/concedii speciale în aceeași zi."))
        
        if (is_holiday or is_sick or is_family_event) and date:
            # 💡 FIX: Map exactly to EVENIMENT FAMILIAL if checked
            if is_holiday:
                target_activity_name = 'CONCEDIU ANUAL'
            elif is_sick:
                target_activity_name = 'CONCEDIU MEDICAL'
            else:
                target_activity_name = 'EVENIMENT FAMILIAL'

            activity_obj = Activity.objects.filter(name__icontains=target_activity_name).first()
            
            if not activity_obj:
                # Fallback search rule if precise text strings are missing inside DB model data
                activity_obj = Activity.objects.filter(name__icontains='EVENIMENT' if is_family_event else 'CONCEDIU').first()
                
            cleaned_data['activity'] = activity_obj
            
            # 2. Pull exact DB instance for FundsSource
            funds_obj = FundsSource.objects.filter(name__icontains='RNP ROMSILVA').first()
            cleaned_data['fundssource'] = funds_obj

            # 3. Handle standard holiday timetables allocations
            cleaned_data['start_time'] = datetime.strptime("08:00", "%H:%M").time()
            day_of_week = date.weekday()            
            if day_of_week <= 3:    # Monday-Thursday
                cleaned_data['end_time'] = datetime.strptime("16:30", "%H:%M").time()
            elif day_of_week == 4:  # Friday
                cleaned_data['end_time'] = datetime.strptime("14:00", "%H:%M").time()
            else:                   # Weekend fallback 
                cleaned_data['end_time'] = datetime.strptime("16:30", "%H:%M").time()
                
            return cleaned_data

        # Standard work hours fallbacks execution
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        target_user = cleaned_data.get('user') or self.requesting_user

        if not start_time or not end_time:
            raise forms.ValidationError(_("Ora de început și ora de final sunt obligatorii pentru activități standard."))

        if date and start_time and end_time and target_user:
            start_dt = datetime.combine(date, start_time)
            end_dt = datetime.combine(date, end_time)
            
            if end_dt <= start_dt:
                self.add_error('end_time', _("Ora de final trebuie să fie după ora început."))
                return cleaned_data

            current_entry_hours = (end_dt - start_dt).total_seconds() / 3600
            day_of_week = date.weekday()

            if day_of_week <= 3:
                limit = 8.5
                day_name = _("Luni-Joi")
            elif day_of_week == 4:
                limit = 6.0
                day_name = _("Vineri")
                if end_time > datetime.strptime("14:00", "%H:%M").time():
                    self.add_error('end_time', _("Programul de vineri se termină la ora 14:00."))
                    return cleaned_data
            else:
                limit = 8.5
                day_name = _("Weekend")

            existing_entries = Timesheet.objects.filter(
                user=target_user, 
                date=date
            )
            if self.instance.pk:
                existing_entries = existing_entries.exclude(pk=self.instance.pk)

            existing_hours = 0
            for ts in existing_entries:
                s = datetime.combine(date, ts.start_time)
                e = datetime.combine(date, ts.end_time)
                if e < s: e += timedelta(days=1)
                existing_hours += (e - s).total_seconds() / 3600

            total_day_hours = existing_hours + current_entry_hours

            if total_day_hours > limit:
                remaining = max(0, limit - existing_hours)
                rem_h = int(remaining)
                rem_m = int((remaining * 60) % 60)
                
                error_msg = _(f"Limită de ore lucrate depășită pentru {day_name}! Poți introduce maxim {rem_h}h și {rem_m:02d}m în această zi.")
                self.add_error('end_time', error_msg)
                    
        return cleaned_data