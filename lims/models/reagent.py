from django.db import models
from django.contrib.auth import get_user_model
from .parameter import Parameter 
from django.utils.timezone import now, timedelta



User = get_user_model()

class Reagent(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class ReagentLot(models.Model):
    reagent = models.ForeignKey(Reagent, on_delete=models.CASCADE, related_name='lots')
    lot_number = models.CharField(max_length=50, unique=True)
    expiry_date = models.DateField()
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=10, default='mL')
    status = models.CharField(max_length=20, choices=[
        ('active', 'Active'), ('expired', 'Expired'), ('archived', 'Archived')
    ], default='active')

    def __str__(self):
        return f"{self.reagent.name} - Lot {self.lot_number}"

    @property
    def is_expiring_soon(self):
        return self.expiry_date <= (now().date() + timedelta(days=30))

    @property
    def is_low_stock(self):
        return self.quantity <= 10
 


class ReagentUsage(models.Model):
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    lot = models.ForeignKey(ReagentLot, on_delete=models.CASCADE)
    quantity_used = models.DecimalField(max_digits=10, decimal_places=2)
    purpose = models.TextField(blank=True)
    used_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    date_used = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.parameter.name} / {self.lot.lot_number} by {self.used_by or 'Unknown'}"
