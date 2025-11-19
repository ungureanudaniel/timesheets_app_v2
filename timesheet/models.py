from django.utils import timezone
from django.db import models
from django.conf import settings
from dashboard.models import Activity
from django.utils import timezone

def default_start_time():
    now = timezone.localtime()
    return now.replace(hour=8, minute=0, second=0, microsecond=0).time()


def default_end_time():
    now = timezone.localtime()
    return now.replace(hour=10, minute=0, second=0, microsecond=0).time()


class FundsSource(models.Model):
    """This class created db tables for the source of funds, which will be selectable from a
    dropdown list when generating a timesheet
    """
    name = models.CharField(max_length=100)
    description = models.TextField()

    class Meta:
        verbose_name = "Funds"
        verbose_name_plural = "Funds"

    def __str__(self):
        return self.name


class Timesheet(models.Model):
    """
    This class created db tables for each timesheet, linked to activity model and FundsSource model by ForeinKey relations
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now().date())
    # hours_worked = models.DecimalField(max_digits=5, decimal_places=0)
    start_time = models.TimeField(default=default_start_time)
    end_time = models.TimeField(default=default_end_time)
    fundssource = models.ForeignKey(FundsSource, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    description = models.TextField()
    # submitted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    # This method is used to set the upload path for images associated with the timesheet
    def get_image_upload_path(self, filename):
            return f'timesheet_images/user_{self.user.pk}/{self.date}/{filename}/%Y/%m/%d/'

    def worked_hours(self):
        start_dt = timezone.datetime.combine(self.date, self.start_time)
        end_dt = timezone.datetime.combine(self.date, self.end_time)
        duration = end_dt - start_dt
        hours = duration.total_seconds() / 3600
        return hours

    # This method is used to set the upload path for documents associated with the timesheet
    def __str__(self):
        return f"Timesheet for {self.user.username}"

class TimesheetImage(models.Model):
    """
    This class creates db tables for images associated with timesheets
    """
    timesheet = models.ForeignKey(Timesheet, related_name='timesheet_images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to=Timesheet.get_image_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.timesheet.user.username} on {self.timesheet.date}"


# class TimesheetDocument(models.Model):
#     """
#     This class creates db tables for documents associated with timesheets
#     """
#     timesheet = models.ForeignKey(Timesheet, related_name='documents', on_delete=models.CASCADE)
#     document = models.FileField(upload_to=Timesheet.get_document_upload_path)

#     def __str__(self):
#         return f"Document for {self.timesheet.user.username} on {self.timesheet.date}"
