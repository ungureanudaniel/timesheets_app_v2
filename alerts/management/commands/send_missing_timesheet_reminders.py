from datetime import timedelta
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.apps import apps

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from timesheet.models import Timesheet  # Adjust path to your Timesheet model

User = get_user_model()


class Command(BaseCommand):
    help = "Send bi-monthly alert emails to every user with their total hours worked in the past month."
    def add_arguments(self, parser):
        parser.add_argument(
            '--previous-month',
            action='store_true',
            help='Generate summary for the previous month instead of the current month.',
        )
    def handle(self, *args, **options):
        Timesheet = apps.get_model('timesheet', 'Timesheet')
        today = timezone.localtime(timezone.now()).date()
        first_of_month = today.replace(day=1)
        reminders_sent = 0
        users = User.objects.filter(is_active=True).order_by('last_name', 'first_name')
        self.stdout.write(f"Se verifică pontajul pentru {users.count()} utilizatori activi...")
        
        for user in users:
            # Query all dates the user logged a timesheet entry this month
            logged_dates = set(
                Timesheet.objects.filter(
                    user=user,
                    date__range=[first_of_month, today],

                ).values_list("date", flat=True)
            )
            missing_dates = []
            curr_date = first_of_month
            while curr_date <= today:
                if curr_date.weekday() < 5 and curr_date not in logged_dates:
                    missing_dates.append(curr_date.strftime("%d.%m.%Y"))
                curr_date += timedelta(days=1)

            if missing_dates:
                missing_str = ", ".join(missing_dates[:10])
                if len(missing_dates) > 10:
                    missing_str += f" și încă {len(missing_dates) -10} zile."

                    user_display = user.get_full_name() or user.username

                    subject = "[Notificare] Pontaj incomplet - Parcul Natural Bucegi"
                    email_body = (
                    f"Bună {user_display},\n\n"
                    f"Te informez că ai zile necompletate în aplicația de rapoarte de activitate pentru luna curentă.\n\n"
                    f"Zile necompletate până astăzi ({today.strftime('%d.%m.%Y')}):\n"
                    f"{missing_str}\n\n"
                    f"Te rog să accesezi platforma (https://rapoarteactivitate.bucegipark.ro) "
                    f"și să îți actualizezi pontajul cât mai curând posibil.\n\n"
                    f"Spor la treabă,\n"
                    f"Administrația Parcului Natural Bucegi"
                    f"\nGenerat automat de sistem - rapoarteactivitate.bucegipark.ro"
                )
                    
                send_mail(
                            subject=subject,
                            message=email_body,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[getattr(settings, "ACCOUNTANT_EMAIL", "bucegipark@gmail.ro")],  # Replace with the actual accounting email address
                            fail_silently=False,
                )
                reminders_sent += 1    
                self.stdout.write(f" - Reminder trimis către: {user_display} ({user.email})")

            self.stdout.write(
                self.style.SUCCESS(
                f"Proces finalizat. S-au trimis {reminders_sent} e-mailuri de reamintire."
                )
            )