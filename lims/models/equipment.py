# lims/models/equipment.py

from django.db import models
from django.utils import timezone



ALLOWED_PARAMETERS = [
    # 🔬 Proximate Analysis
    ("Protein", "Protein"),
    ("Fat", "Fat"),
    ("Moisture", "Moisture"),
    ("Ash", "Ash"),
    ("Fiber", "Fiber"),

    # 🌾 Fiber Fractions
    ("Neutral Detergent Fiber", "Neutral Detergent Fiber"),
    ("Acid Detergent Fiber", "Acid Detergent Fiber"),
    ("Acid Detergent Lignin", "Acid Detergent Lignin"),

    # 🔬 Mycotoxins
    ("Total Aflatoxins", "Total Aflatoxins"),
    ("Aflatoxin B1", "Aflatoxin B1"),

    # ⚡ Energy
    ("Gross Energy", "Gross Energy"),

    # 💊 Vitamins (for use with HPLC)
    ("Vitamin A", "Vitamin A"),
    ("Vitamin C", "Vitamin C"),
    ("Vitamin E", "Vitamin E"),
    ("Vitamin B1", "Vitamin B1"),
    ("Vitamin B2", "Vitamin B2"),
]


class Equipment(models.Model):
    parameters_supported = models.ManyToManyField("lims.Parameter", blank=True)
    name = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, unique=True)
    model = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=50, blank=True)
    date_installed = models.DateField()
    manufacturer = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.serial_number})"

class CalibrationRecord(models.Model):
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name="calibrations")
    calibration_date = models.DateField()
    calibrated_by = models.CharField(max_length=100)
    expires_on = models.DateField()
    certificate = models.FileField(upload_to="calibration_certificates/", blank=True, null=True)
    comments = models.TextField(blank=True)

    def is_valid(self):
        return self.expires_on >= timezone.now().date()

    def __str__(self):
        return f"{self.equipment.name} calibrated {self.calibration_date}"
