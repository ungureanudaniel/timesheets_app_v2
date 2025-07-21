from django.db import models
from users.models import CustomUser
from timesheet.models import Activity


class MonthlyReport(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    description = models.TextField()
    timeframe = models.CharField(max_length=300)
    date = models.DateField()
    hours = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"Monthly Report for {self.user.username} - {self.month}"
