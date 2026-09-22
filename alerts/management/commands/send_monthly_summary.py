from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Sum
from timesheet.models import Timesheet

User = get_user_model()

class Command(BaseCommand):
    help = "Send monthly summary emails to all users with their total hours worked in the past month."
    def add_arguments(self, parser):
        parser.add_argument(
            '--previous-month',
            action='store_true',
            help='Generate summary for the previous month instead of the current month.',
        )
    def handle(self, *args, **options):
        Timesheet = apps.get_model('timesheet', 'Timesheet')
        today = timezone.localtime(timezone.now()).date()

        if options.get('previous_month'):
            # First day of current month minus 1 day gives the last day of previous month
            first_of_this_month = today.replace(day=1)
            target_date = first_of_this_month - timezone.timedelta(days=1)
        else:
            target_date = today

        
        target_year = target_date.year
        target_month = target_date.month
        month_name = target_date.strftime('%B %Y')
        users = User.objects.filter(is_active=True).order_by('last_name', 'first_name')

        summary_lines = [
            f"Sumar Ore Lucrate - Parcul Natural Bucegi ({month_name})\n",
            f"Total Utilizatori Procesați: {users.count()}",
            "=" * 60,
        ]
            
        for user in users:
            timesheets = Timesheet.objects.filter(user=user,
                                               date__year=target_year,
                                               date__month=target_month,
                                               )
            total_minutes = 0
            entry_count = timesheets.count()

            for entry in timesheets:
                if entry.start_time and entry.end_time:
                    # Combine date with start and end times to calculate total duration, assuming you have a method to calculate duration in minutes
                    start_dt = timezone.datetime.combine(entry.date, entry.start_time) # Combine date with start time
                    end_dt = timezone.datetime.combine(entry.date, entry.end_time) # Combine date with end time

                    if end_dt < start_dt:
                        # If end time is less than start time, it means the entry spans midnight
                        end_dt += timezone.timedelta(days=1)  # Add one day to end time

                    diff = end_dt - start_dt
                    total_minutes += int(diff.total_seconds()//60)  # Convert seconds to minutes

            hours = total_minutes // 60
            minutes = total_minutes % 60
            user_name = user.get_full_name() or user.username

            if entry_count > 0:
                summary_lines.append(f" {user_name} - Total Hours: {hours}h {minutes}m")

            else:
                summary_lines.append(f"• {user_name}: 0h 0m (Fără pontaj înregistrat)")
        
        summary_lines.append("\n" + "=" * 60)
        summary_lines.append("\nGenerat automat de sistem - rapoarteactivitate.bucegipark.ro")
        subject = f"Sumar Ore Lucrate - Parcul Natural Bucegi ({month_name})"
        email_body = "\n".join(summary_lines)


        send_mail(
            subject=subject,
            message=email_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[getattr(settings, "ACCOUNTANT_EMAIL", "bucegipark@gmail.ro")],  # Replace with the actual accounting email address
            fail_silently=False,
        )
        self.stdout.write(self.style.SUCCESS(f"Emailul privind rezumatul lunar al orelor lucrate a fost trimis la adresa {settings.ACCOUNTANT_EMAIL}")) 

