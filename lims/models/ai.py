from django.db import models
from django.conf import settings
from django.db import models


class LabAIHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    question = models.TextField()
    answer = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}: {self.question[:50]}"


class EfficiencySnapshot(models.Model):
    analyst = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    week_start = models.DateField()
    week_end = models.DateField()
    average_duration = models.DurationField()
    total_tests = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("analyst", "week_start", "week_end")

    def __str__(self):
        return f"{self.analyst.username}: {self.average_duration} ({self.total_tests} tests)"
