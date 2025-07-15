from django.db import models

class COAInterpretation(models.Model):
    client = models.ForeignKey("Client", on_delete=models.CASCADE)
    summary_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Interpretation for {self.client.client_id}"
