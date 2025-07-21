from allauth.account.signals import user_signed_up
from django.dispatch import receiver
from django.contrib.auth.models import Group


@receiver(user_signed_up)
def user_signed_up_receiver(request, user, **kwargs):
    # Automatically add the user to a group after signing up
    group = Group.objects.get(name='REPORTER')
    user.groups.add(group)
    user.save()
