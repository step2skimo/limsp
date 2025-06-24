from django.core.management.base import BaseCommand
from datetime import date
from lims.models import ParameterGroup, Parameter, ControlSpec, Equipment
from lims.models import CalibrationRecord

class Command(BaseCommand):
    help = 'Seeds parameter groups, parameters, control specs, and equipment.'

    def handle(self, *args, **kwargs):
        # 1. Parameter Groups
        group_names = [
            "Proximate", "Mycotoxins", "Vitamins", "Gross Energy"
        ]
        groups = {name: ParameterGroup.objects.get_or_create(name=name)[0] for name in group_names}

        # 2. Parameters
        params = [
            ("Ash", "Proximate", "%", "Gravimetric (550°C furnace) (AOAC 923.03)", "≤ 5%", 5000),
            ("Moisture", "Proximate", "%", "Oven drying (105°C) (AOAC 925.10)", "≤ 12%", 5000),
            ("Protein", "Proximate", "%", "Kjeldahl (AOAC 978.04)", "≥ 10%", 5000),
            ("Fiber", "Proximate", "%", "Weende method (AOAC 962.09)", "≤ 5%", 5000),
            ("Fat", "Proximate", "%", "Soxtec (AOAC 945.16)", "≥ 2%", 5000),
            ("Total Aflatoxins", "Mycotoxins", "ppb", "Neogen AccuScan", "≤ 20", 2500),
            ("Aflatoxin B1", "Mycotoxins", "ppb", "Neogen AccuScan", "≤ 5", 2500),
            ("Gross Energy", "Gross Energy", "kcal/kg", "Bomb Calorimeter", "-", 4000),
        ]
        vitamin_names = [
            ("Vitamin A", "IU/kg"), ("Vitamin D", "IU/kg"), ("Vitamin E", "mg/kg"),
            ("Vitamin K", "µg/kg"), ("Vitamin B1", "mg/kg"), ("Vitamin B2", "mg/kg"),
            ("Vitamin B3", "mg/kg"), ("Vitamin B6", "mg/kg"), ("Vitamin B9", "µg/kg"),
            ("Vitamin B12", "µg/kg"), ("Vitamin C", "mg/kg")
        ]
        for vname, unit in vitamin_names:
            params.append((vname, "Vitamins", unit, "HPLC (AOAC)", "Standard Range", 3000))

        param_objs = {}
        for name, group, unit, method, ref_limit, price in params:
            obj, _ = Parameter.objects.get_or_create(
                name=name,
                defaults={
                    "group": groups[group],
                    "unit": unit,
                    "method": method,
                    "ref_limit": ref_limit,
                    "default_price": price
                }
            )
            param_objs[name] = obj

        # 3. Control Specs
        specs = {
            "Protein": (11.663, 11.860),
            "Ash": (0.993, 1.424),
            "Moisture": (10.648, 11.132),
            "Fiber": (2.178, 2.328),
            "Fat": (1.322, 1.434),
        }
        for name, (min_v, max_v) in specs.items():
            if name in param_objs:
                ControlSpec.objects.update_or_create(
                    parameter=param_objs[name],
                    defaults={"min_acceptable": min_v, "max_acceptable": max_v, "unit": "%"}
                )

        # 4. Equipment
        equipment_list = [
            ("Laboratory Oven", "H-906128", "SM9053", "Uniscope"),
            ("Furnace", "FUR-002", "AAF-1100", "Carbolite"),
            ("Cyclotec", "CYC-004", "CT-293", "Foss"),
            ("Centrifuge", "CEN-006", "80-2", "Searchtech"),
            ("HPLC", "HPLC-008", "CE-4300", "Cecil"),
            ("Bomb Calorimeter", "CALO-010", "CAL3K-ST", "DDS"),
            ("Soxtec", "SOX-011", "Soxtec 2050", "Foss"),
            ("Water Purifier", "WAD-013", "SCSJ-10F", "Biobase"),
            ("Fibertec", "FIB-014", "FT 121 122", "Foss"),
            ("Sonicator", "SON-015", "XUB5", "Grant"),
            ("Millipore", "MIL-016", "WP6122050", "Millipore"),
            ("Kjeltec", "KJEL-017", "8200", "Foss"),
            ("Analytical Balance", "ANAL-018", "HR-250AZ", "AND"),
            ("PH Meter", "PHM-019", "GP-353", "EDT Instruments"),
            ("Digestor", "DIG-022", "", "Unknown"),
            ("Thermohygrometer", "Ther-025", "HTC-01", "Swastik"),
            ("Accuscan Gold", "Accu-024", "ASG-5420", "Neogen"),
            ("Digital Titrator", "TIT-026", "HIRSCHMANN", "HIRSCHMANN"),
        ]
        equip_objs = {}
        for name, serial, model, mfg in equipment_list:
            eq, _ = Equipment.objects.get_or_create(
                name=name,
                serial_number=serial,
                defaults={
                    "model": model,
                    "date_installed": date.today(),
                    "is_active": True,
                }
            )
            equip_objs[name] = eq

        # 5. Equipment-to-Parameter Mapping
        map_table = {
            "Furnace": ["Ash"],
            "Moisture Analyzer": ["Moisture"],
            "Soxtec": ["Fat"],
            "Digestor": ["Protein"],
            "Kjeltec": ["Protein"],
            "Digital Titrator": ["Protein"],
            "Accuscan Gold": ["Aflatoxin B1", "Total Aflatoxins"],
            "Bomb Calorimeter": ["Gross Energy"],
            "HPLC": [v[0] for v in vitamin_names],
            "Fibertec": ["Fiber"]
        }

                # 6. Calibration Records

        calibrated_on = date(2024, 11, 1)
        expires_on = date(2025, 11, 1)

        for eq in equip_objs.values():
            CalibrationRecord.objects.update_or_create(
                equipment=eq,
                calibration_date=calibrated_on,
                defaults={
                    "calibrated_by": "BV Global",
                    "expires_on": expires_on,
                    "comments": "Seeded with initial calibration status."
                }
            )

        for device, plist in map_table.items():
            eq = equip_objs.get(device)
            if eq:
                for pname in plist:
                    param = param_objs.get(pname)
                    if param:
                        eq.parameters_supported.add(param)

        self.stdout.write(self.style.SUCCESS("✅ Lab data seeded successfully."))
