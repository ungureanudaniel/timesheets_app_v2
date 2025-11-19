from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class EmailOrUsernameModelBackend(ModelBackend):
    """
    Authenticate against either username or email
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        print(f"🔐 Custom backend called with username: '{username}'")
        
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        
        try:
            # Try to find user by username OR email (case-insensitive)
            user = User.objects.get(
                Q(username__iexact=username) | Q(email__iexact=username)
            )
            print(f"✅ User found: {user.username} (email: {user.email})")
        except User.DoesNotExist:
            print(f"❌ User not found with username/email: '{username}'")
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            print(f"⚠️ Multiple users found for: '{username}'")
            user = User.objects.filter(
                Q(username__iexact=username) | Q(email__iexact=username)
            ).first()
            print(f"   Using: {user.username}")

        if user:
            password_correct = user.check_password(password)
            can_authenticate = self.user_can_authenticate(user)
            print(f"🔑 Password check: {password_correct}")
            print(f"👤 Can authenticate: {can_authenticate}")
            
            if password_correct and can_authenticate:
                print("🎉 Authentication SUCCESS")
                return user
        
        print("💥 Authentication FAILED")
        return None