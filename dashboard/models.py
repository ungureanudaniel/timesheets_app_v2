from django.db import models
from django.conf import settings
import datetime as dt
from django.utils import timezone
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
User = get_user_model()


def current_year():
    return timezone.now().year


class ActivityProgram(models.Model):
    """Weekly activity program: one per ISO week, holding several activity items."""
    registration_nr = models.IntegerField()
    registration_date = models.DateField(default=timezone.now)
    year = models.IntegerField(default=current_year)
    week = models.IntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_activity_programs'
    )

    # Approvers who add an extra signature to the program
    director = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    chief_ranger = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    accountant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    biologist = models.ForeignKey(
            settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
        )
    education = models.ForeignKey(
            settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
        )
    # All personnel who must sign the program (every active user when it is created)
    assigned_rangers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='assigned_activity_programs',
        blank=True
    )

    class Meta:
        unique_together = ('year', 'week')
        ordering = ['-year', '-week']

    def __str__(self):
        return f"Program săptămâna {self.week}/{self.year}"

    def create_approver_signatures(self):
        """Create the pending extra signatures for director, chief ranger and accountant."""
        approvers = {
            ActivityProgramSignature.Role.DIRECTOR: self.director,
            ActivityProgramSignature.Role.CHIEF_RANGER: self.chief_ranger,
            ActivityProgramSignature.Role.ACCOUNTANT: self.accountant,
            ActivityProgramSignature.Role.BIOLOGIST: self.biologist,
            ActivityProgramSignature.Role.EDUCATION: self.education,

        }
        for role, user in approvers.items():
            if user:
                # .value: mysql-connector cannot convert TextChoices members
                ActivityProgramSignature.objects.get_or_create(program=self, ranger=user, role=role.value)

    @property
    def is_fully_signed(self):
        signatures = ActivityProgramSignature.objects.filter(program=self)
        return signatures.exists() and not signatures.filter(is_signed=False).exists()


class ActivityProgramItem(models.Model):
    """One activity of a weekly program and the rangers assigned to it."""
    program = models.ForeignKey(
        ActivityProgram,
        on_delete=models.CASCADE,
        related_name='items'
    )
    activity_code = models.CharField(max_length=20)
    activity_title = models.CharField(max_length=300)
    rangers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='activity_program_items',
        blank=True
    )

    class Meta:
        ordering = ['pk']

    def __str__(self):
        return f"{self.activity_code} - {self.activity_title}"


class ActivityProgramSignature(models.Model):
    class Role(models.TextChoices):
        PERSONNEL = 'PERSONNEL', 'Personal'
        DIRECTOR = 'DIRECTOR', 'Director'
        CHIEF_RANGER = 'CHIEF_RANGER', 'Șef pază'
        ACCOUNTANT = 'ACCOUNTANT', 'Contabil'
        BIOLOGIST = 'BIOLOGIST', 'BIOLOG'
        EDUCATION = 'EDUCATION', 'EDUCAȚIE'

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
    # Approvers get an extra signature in their role, besides their personnel one
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PERSONNEL.value)
    is_signed = models.BooleanField(default=False)
    signed_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    signature_data = models.TextField(null=True, blank=True)  # Base64 Canvas PNG

    class Meta:
        unique_together = ('program', 'ranger', 'role')

    def __str__(self):
        status = "Signed" if self.is_signed else "Pending"
        return f"{self.ranger} - {self.program} - {self.get_role_display()} ({status})"


# Signal to auto-create pending signature records when rangers are assigned
@receiver(m2m_changed, sender=ActivityProgram.assigned_rangers.through)
def create_ranger_signatures(sender, instance, action, pk_set, **kwargs):
    if action == "post_add":
        for ranger_id in pk_set:
            ActivityProgramSignature.objects.get_or_create(
                program=instance,
                ranger_id=ranger_id,
                role=ActivityProgramSignature.Role.PERSONNEL.value
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