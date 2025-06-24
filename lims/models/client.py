from django.db import models
import random

def generate_client_id():
    last_client = Client.objects.order_by('-id').first()
    if not last_client or not str(last_client.client_id).startswith("JGLSP"):
        return "JGLSP2500"
    
    last_id = int(str(last_client.client_id).replace("JGLSP", ""))
    new_id = last_id + 1
    return f"JGLSP{new_id}"



class Client(models.Model):
    client_id = models.CharField(max_length=20, unique=True)  
    name = models.CharField(max_length=100)
    organization = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    token = models.CharField(max_length=20, unique=True, blank=True)  
    created = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_token()
        super().save(*args, **kwargs)

    def generate_token(self):
        """Generates a unique token like JGL-TKN-4920."""
        while True:
            token = f"JGL-TKN-{random.randint(1000, 9999)}"
            if not Client.objects.filter(token=token).exists():
                return token

    def __str__(self):
        return f"{self.name} ({self.organization})"

