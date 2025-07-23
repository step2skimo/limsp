from django.db import models
from simple_history.models import HistoricalRecords
class COAInterpretation(models.Model):
    client = models.ForeignKey("Client", on_delete=models.CASCADE)
    summary_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return f"Interpretation for {self.client.client_id}"
