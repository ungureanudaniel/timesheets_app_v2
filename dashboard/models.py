from django.db import models
from django.conf import settings
import datetime as dt
from django.utils import timezone
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
User = get_user_model()


class ActivityProgram(models.Model):
    user = models.CharField(max_length=300)
    registration_nr = models.IntegerField()
    registration_date = models.DateField(default=timezone.now)
    week = models.IntegerField()
    activity_code = models.CharField(max_length=6)
    activity_title = models.CharField(max_length=300)

    # Assigned rangers who must sign this program
    assigned_rangers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='assigned_activity_programs',
        blank=True
    )

    def __str__(self):
        return f"{self.activity_code} - {self.activity_title}"

    @property
    def is_fully_signed(self):
        total_assigned = self.assigned_rangers.count()
        if total_assigned == 0:
            return False
        signed_count = self.signatures.filter(is_signed=True).count()
        return total_assigned == signed_count


class ActivityProgramSignature(models.Model):
    program = models.ForeignKey(
        ActivityProgram, 
        on_delete=models.CASCADE, 
        related_name='signatures'
    )
    ranger = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='activity_signatures'
    )
    is_signed = models.BooleanField(default=False)
    signed_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    signature_data = models.TextField(null=True, blank=True)  # Base64 Canvas PNG

    class Meta:
        unique_together = ('program', 'ranger')

    def __str__(self):
        status = "Signed" if self.is_signed else "Pending"
        return f"{self.ranger} - {self.program.activity_code} ({status})"


# Signal to auto-create pending signature records when rangers are assigned
@receiver(m2m_changed, sender=ActivityProgram.assigned_rangers.through)
def create_ranger_signatures(sender, instance, action, pk_set, **kwargs):
    if action == "post_add":
        for ranger_id in pk_set:
            ActivityProgramSignature.objects.get_or_create(
                program=instance,
                ranger_id=ranger_id
            )

# class ActivityGroup(models.Model):
#     """Model representing an activity group."""
#     name = models.CharField(max_length=200, verbose_name="Activity Group")
    
#     def __str__(self):
#         return self.name

# class ActivitySubGroup(models.Model):
#     group = models.ForeignKey(ActivityGroup, on_delete=models.CASCADE, related_name='subgroups')
#     name = models.CharField(max_length=200, verbose_name="Subgroup")
#     code = models.CharField(max_length=20, verbose_name="Code")
    
#     def __str__(self):
#         return f"{self.group.name} - {self.name}"

class Activity(models.Model):
    group = models.CharField(max_length=200, verbose_name="Program")
    subgroup = models.CharField(max_length=200, verbose_name="Subprogram")
    code = models.CharField(max_length=20, verbose_name="ID activitate")
    name = models.CharField(max_length=300, verbose_name="Denumire activitate")
    responsible = models.CharField(max_length=100, verbose_name="Responsabil", 
                                 choices=[
                                     ('B', 'Biolog'),
                                     ('D', 'Director'),
                                     ('IT', 'Specialist IT'),
                                     ('RC', 'Responsabil Comunități'),
                                     ('SP', 'Șef Pază'),
                                 ])

    class Meta:
        verbose_name = "Activity"
        verbose_name_plural = "Activities"

    def __str__(self):
        return f"{self.code} - {self.name}"

class Indicator(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='indicators')
    name = models.CharField(max_length=100, verbose_name="Indicator")
    definition = models.TextField(verbose_name="Definire", blank=True)
    management_plan = models.TextField(verbose_name="Plan de management", blank=True)
    
    # Planned values
    planned_year = models.IntegerField(verbose_name="Propus 2025", default=0)
    planned_q1 = models.IntegerField(verbose_name="Trim.I", default=0)
    planned_q2 = models.IntegerField(verbose_name="Trim.II", default=0)
    planned_q3 = models.IntegerField(verbose_name="Trim.III", default=0)
    planned_q4 = models.IntegerField(verbose_name="Trim.IV", default=0)
    
    # Actual values
    planned_total = models.IntegerField(verbose_name="Prevăzut", default=0)
    actual_cumulative = models.IntegerField(verbose_name="Realizat cumulat", default=0)
    
    notes = models.TextField(verbose_name="Observații", blank=True)
    
    def __str__(self):
        return f"{self.activity.name} - {self.name}"
    
    class Meta:
        ordering = ['activity__code']


class Species(models.Model):
    SCIENTIFIC_NAME = 'SN'
    COMMON_NAME = 'CN'
    NAME_TYPE_CHOICES = [
        (SCIENTIFIC_NAME, 'Scientific name'),
        (COMMON_NAME, 'Common name'),
    ]
    
    FLORA = 'FL'
    FAUNA = 'FA'
    TYPE_CHOICES = [
        (FLORA, 'Flora'),
        (FAUNA, 'Fauna'),
    ]
    
    name = models.CharField(max_length=200)
    name_type = models.CharField(max_length=2, choices=NAME_TYPE_CHOICES, default=SCIENTIFIC_NAME)
    species_type = models.CharField(max_length=2, choices=TYPE_CHOICES)
    code = models.CharField(max_length=50, blank=True)
    protected = models.BooleanField(default=False)
    invasive = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Species"
        verbose_name_plural = "Species"

    def __str__(self):
        return self.name

class Habitat(models.Model):
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    protected = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class MonitoringRecord(models.Model):
    INVENTORY = 'INV'
    MAPPING = 'MAP'
    MONITORING = 'MON'
    ACTIVITY_TYPE_CHOICES = [
        (INVENTORY, 'Inventory'),
        (MAPPING, 'Mapping'),
        (MONITORING, 'Monitoring'),
    ]
    
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    species = models.ForeignKey(Species, on_delete=models.SET_NULL, null=True, blank=True)
    habitat = models.ForeignKey(Habitat, on_delete=models.SET_NULL, null=True, blank=True)
    activity_type = models.CharField(max_length=3, choices=ACTIVITY_TYPE_CHOICES)
    date = models.DateField()
    location = models.CharField(max_length=200, blank=True)
    responsible = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.date}"