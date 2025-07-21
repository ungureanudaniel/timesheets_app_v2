from django.db import models
from users.models import CustomUser


class Activity(models.Model):
    """
    This class creates db tables for the types of actvities
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=6)

    class Meta:
        verbose_name = "Activity"
        verbose_name_plural = "Activities"

    def __str__(self):
        return "{} - {}".format(self.code, self.name)


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
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    date = models.DateField()
    hours_worked = models.DecimalField(max_digits=5, decimal_places=0)
    fundssource = models.ForeignKey(FundsSource, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    description = models.TextField()
    submitted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # This method is used to set the upload path for images associated with the timesheet
    def get_image_upload_path(instance, filename):
            return f'timesheet_images/user_{instance.user.id}/{instance.date}/{filename}'

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
