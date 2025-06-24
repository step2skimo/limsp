from django.contrib.auth.models import AbstractUser
from django.db import models


class RoleChoices(models.TextChoices):
    CLERK = 'clerk', 'Clerk'
    ANALYST = 'analyst', 'Analyst'
    MANAGER = 'manager', 'Manager'

class User(AbstractUser):
    role = models.CharField(max_length=10, choices=RoleChoices.choices)

    def is_clerk(self):
        return self.role == RoleChoices.CLERK

    def is_analyst(self):
        return self.role == RoleChoices.ANALYST

    def is_manager(self):
        return self.role == RoleChoices.MANAGER
