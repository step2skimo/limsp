from django.db import models
from .test_assignment import TestAssignment
from .equipment import Equipment
from django.conf import settings
from django.contrib.auth import get_user_model

class TestEnvironment(models.Model):
    test_assignment = models.OneToOneField(TestAssignment, on_delete=models.CASCADE)
    temperature = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    humidity = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    pressure = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    instrument = models.ForeignKey(Equipment, null=True, blank=True, on_delete=models.SET_NULL)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.test_assignment} – {self.temperature}°C / {self.humidity}%"
