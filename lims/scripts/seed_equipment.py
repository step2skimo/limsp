from lims.models import Equipment, Parameter, CalibrationRecord
from django.utils.dateparse import parse_date
from datetime import date

EQUIPMENT_DATA = [
    {
        "name": "Laboratory Oven",
        "serial": "H-906128",
        "model": "SM9053",
        "category": "Oven",
        "params": ["Moisture"],
    },
    {
        "name": "Furnace",
        "serial": "AUTO-FUR002",
        "model": "AAF-1100",
        "category": "Furnace",
        "params": ["Ash"],
    },
    {
        "name": "Cyclotec",
        "serial": "AUTO-CYC004",
        "model": "CT-293",
        "category": "Mill",
        "params": [],
    },
    {
        "name": "Centrifuge",
        "serial": "AUTO-CEN006",
        "model": "80-2",
        "category": "Centrifuge",
        "params": ["Total Aflatoxin"],
    },
    {
        "name": "HPLC",
        "serial": "AUTO-HPLC008",
        "model": "CE-4300",
        "category": "HPLC",
        "params":  ["Vitamin A", "Vitamin B1", "Vitamin C", "Vitamin D"],
    },
    {
        "name": "Bomb Calorimeter",
        "serial": "AUTO-CALO010",
        "model": "CAL3K-ST",
        "category": "Calorimeter",
        "params": ["Gross Energy"],
    },
    {
        "name": "Soxtec",
        "serial": "AUTO-SOX011",
        "model": "Soxtec 2050",
        "category": "Extractor",
        "params": ["Ash"],
    },
    {
        "name": "Fibertec",
        "serial": "AUTO-FIB014",
        "model": "FT 121/122",
        "category": "Fiber Analyzer",
        "params": ["Fiber"],
    },
    {
        "name": "Accuscan Gold",
        "serial": "AUTO-ACC024",
        "model": "ASG-5420",
        "category": "Mycotoxin Reader",
        "params": ["Total Aflatoxin"],
    },
    {
        "name": "Kjeltec",
        "serial": "AUTO-KJEL017",
        "model": "8200",
        "category": "Protein Analyzer",
        "params": ["Protein"],
    },
    {
        "name": "Digestor",
        "serial": "AUTO-DIG022",
        "model": "Generic Digestor",
        "category": "Digester",
        "params": ["Protein"],
    },
    {
        "name": "Digital Titrator",
        "serial": "AUTO-TIT026",
        "model": "HIRSCHMANN",
        "category": "Titrator",
        "params": ["Protein"],
    },
    {
    "name": "Sonicator",
    "serial": "U50193",
    "model": "XUB5",
    "category": "Sonicator",
    "params": [],  # No parameter link yet
},
{
    "name": "Water Purifier",
    "serial": "AUTO-WAD013",
    "model": "SCSJ-10F",
    "category": "Purifier",
    "params": [],
},
{
    "name": "Millipore Filter",
    "serial": "AUTO-MIL016",
    "model": "WP6122050",
    "category": "Filtration",
    "params": [],
},
{
    "name": "Analytical Balance",
    "serial": "AUTO-ANAL018",
    "model": "HR-250AZ",
    "category": "Balance",
    "params": [],
},
{
    "name": "Thermohygrometer",
    "serial": "AUTO-THER025",
    "model": "HTC-01",
    "category": "Environmental Meter",
    "params": [],
},
{
    "name": "pH Meter",
    "serial": "AUTO-PHM019",
    "model": "GP-353",
    "category": "pH Meter",
    "params": [],
},

]

CALIBRATION_DATE = date(2024, 11, 1)
CALIBRATION_EXPIRY = date(2025, 11, 1)

def run():
    for eq in EQUIPMENT_DATA:
        device, created = Equipment.objects.get_or_create(
            name=eq["name"],
            serial_number=eq["serial"],
            defaults={
                "model": eq.get("model", ""),
                "category": eq["category"],
                "date_installed": parse_date("2024-01-01"),
                "is_active": True,
            }
        )

        for pname in eq["params"]:
            try:
                param = Parameter.objects.get(name__iexact=pname)
                device.parameters_supported.add(param)

                # Optionally assign as default equipment for the parameter
                if pname in ["Protein", "Ash", "Moisture", "Fiber", "Gross Energy", "Aflatoxin", "Vitamins"]:
                    param.default_equipment = device
                    param.save()
            except Parameter.DoesNotExist:
                print(f"⚠️ Parameter '{pname}' not found in DB.")

        if created:
            CalibrationRecord.objects.create(
                equipment=device,
                calibration_date=CALIBRATION_DATE,
                expires_on=CALIBRATION_EXPIRY,
                calibrated_by="System Seeder",
                comments="Auto-seeded during initial setup."
            )
            print(f"✅ Created: {device.name} | 📅 CalibrationRecord added.")
        else:
            print(f"✔️ Exists: {device.name}")
