from django.core.management.base import BaseCommand
from datetime import date
from django.utils import timezone
from lims.models import (
    ParameterGroup, Parameter, ControlSpec,
    Equipment, CalibrationRecord, Reagent


)

class Command(BaseCommand):
    help = 'Seeds parameter groups, parameters, control specs, equipment, calibration records, and mappings.'

    def handle(self, *args, **kwargs):
        # 1. Parameter Groups
        group_names = [
            "Proximate", "Functional Properties", "Phytochemicals", "Protein Digestibility", "Gross Energy",
            "Oil Analysis", "Fiber Fractions", "Minerals",
            "Vitamins & Contaminants", "Water Analysis"
        ]
        groups = {name: ParameterGroup.objects.get_or_create(name=name)[0] for name in group_names}

        # 2. Parameters
        param_data = [
          
    # Proximate
    ("Moisture", "Proximate", "%", "Oven (AOAC 930.15 2000)", "≤ 12%", 4000),
    ("Ash", "Proximate", "%", "Furnace (AOAC 942.05, 2000)", "≤ 5%", 4000),
    ("Crude Fibre", "Proximate", "%", "AOAC 978.10, 2000", "≤ 5%", 4000),
    ("Crude Fat", "Proximate", "%", "Soxhlet Extraction (AOAC 920.39)", "≥ 2%", 4000),
    ("Protein", "Proximate", "%", "Kjeldahl (AOAC 942.05 2000)", "≥ 10%", 4000),

    # Functional Properties
    ("pH", "Functional Properties", "pH", "pH Meter", "-", 2000),
    ("Bulk Density", "Functional Properties", "g/mL", "", "-", 2500),  # alt: g/cm3
    ("Swelling Capacity", "Functional Properties", "mL/g", "", "-", 2500),
    ("Total Solids", "Functional Properties", "%", "", "-", 2500),
    ("Emulsification Capacity", "Functional Properties", "%", "", "-", 2500),  # alt: mL oil/g
    ("Water Absorption Capacity", "Functional Properties", "g/g", "", "-", 2500),
    ("Oil Absorption Capacity", "Functional Properties", "g/g", "", "-", 2500),
    ("Foaming Capacity", "Functional Properties", "%", "", "-", 2500),  # % volume increase
    ("Wettability", "Functional Properties", "s", "", "-", 2500),  # time to wet
    ("Gluten (Dry & Wet)", "Functional Properties", "%", "", "-", 2500),
    ("Dispersibility", "Functional Properties", "%", "", "-", 2500),
    ("Brix Content", "Functional Properties", "°Bx", "Refractometer", "-", 2500),
    ("Salt Content", "Functional Properties", "%", "Refractometer", "-", 2500),  
    ("Viscosity", "Functional Properties", "mPa·s", "Viscometer", "-", 2500), 

    # Phytochemicals (spectrophotometric results typically reported per 100g or per g dry matter; adjust as needed)
    ("Alkaloids", "Phytochemicals", "mg/100g", "Spectrophotometric", "-", 4000),
    ("Flavonoids", "Phytochemicals", "mg/100g", "Spectrophotometric", "-", 4500),
    ("Tannins", "Phytochemicals", "mg/100g", "Spectrophotometric", "-", 4500),
    ("Saponins", "Phytochemicals", "mg/100g", "Spectrophotometric", "-", 4000),
    ("Phenolics", "Phytochemicals", "mg GAE/100g", "Spectrophotometric", "-", 4000),  
    ("Phytate", "Phytochemicals", "mg/100g", "Spectrophotometric", "-", 4000),
    ("Oxalate", "Phytochemicals", "mg/100g", "Spectrophotometric", "-", 4000),
    ("Carotenoids", "Phytochemicals", "µg/g", "Spectrophotometric", "-", 4000),
    ("Cyanides", "Phytochemicals", "mg HCN/kg", "Spectrophotometric", "-", 4500),
    ("Total Antioxidant Capacity/DPPH", "Phytochemicals", "% inhibition", "Spectrophotometric", "-", 4000),  
    ("Total starch", "Phytochemicals", "%", "Spectrophotometric", "-", 5000),

    # Protein Digestibility
    ("Protein Digestibility", "Protein Digestibility", "%", "AOAC", "-", 8000),
    ("FRAP", "Protein Digestibility", "µmol Fe2+/g", "-", "-", 5000),  

    # Oil Analysis
    ("Total Free Fatty Acid", "Oil Analysis", "% oleic acid", "Titrimetric", "-", 3000),
    ("Peroxide Value", "Oil Analysis", "meq O2/kg", "Titrimetric", "-", 4000),
    ("Iodine Value", "Oil Analysis", "g I2/100g", "Titrimetric", "-", 4000),
    ("Saponification Value", "Oil Analysis", "mg KOH/g", "Titrimetric", "-", 3500),
    ("Acid/Titratable Acid Value", "Oil Analysis", "mg KOH/g", "Titrimetric", "-", 3000),

    # Fiber Fractions (usually reported on a dry-matter basis)
    ("Neutral Detergent Fiber", "Fiber Fractions", "% DM", "AOAC", "-", 4000),
    ("Acid Detergent Fiber", "Fiber Fractions", "% DM", "AOAC", "-", 4000),
    ("Acid Detergent Lignin", "Fiber Fractions", "% DM", "AOAC", "-", 4500),
    ("Cellulose", "Fiber Fractions", "% DM", "AOAC", "-", 4500),
    ("Hemicelluloses", "Fiber Fractions", "% DM", "AOAC", "-", 4500),
    ("Digestibility", "Fiber Fractions", "%", "AOAC", "-", 4500),  
    ("Dry Matter Intake", "Fiber Fractions", "% BW", "AOAC", "-", 4500),  
    ("Relative Feed Value", "Fiber Fractions", "index", "AOAC", "-", 4500),
    ("Volatile Matter", "Fiber Fractions", "%", "AOAC", "-", 4500),
    ("Fixed Carbon", "Fiber Fractions", "%", "AOAC", "-", 4000),



            # Minerals
            ("Digestion (prep for AAS)", "Minerals", "", "-", "-", 1000),
            ("Elemental Determination (Ca, Mg, Zn...)", "Minerals", "", "AAS", "-", 1000),
            *[(name, "Minerals", "", "-", "-", 4500) for name in ["Nitrate", "Carbonate", "Bromate", "NaCl", "Organic Matter"]],
            #Gross Energy
            ("Gross Energy", "Gross Energy", "kcal/kg", "Calorimeter", "-", 4500),

            # Vitamins & Contaminants
            *[(f"Vitamin {v}", "Vitamins & Contaminants", unit, "HPLC", "-", 10000)
              for v, unit in [("A", "IU/kg"), ("B1", "mg/kg"), ("B2", "mg/kg"),
                              ("B3", "mg/kg"), ("B6", "mg/kg"), ("B9", "µg/kg"),
                              ("B12", "µg/kg"), ("C", "mg/kg"), ("D", "IU/kg"),
                              ("E", "mg/kg"), ("K", "µg/kg")]],
            ("Total Aflatoxin", "Vitamins & Contaminants", "ppb", "Neogen Reader", "≤ 20", 20000),
            ("Aflatoxin B1", "Vitamins & Contaminants", "ppb", "Neogen Reader", "≤ 5", 10000),
            ("Total Plate Count", "Vitamins & Contaminants", "", "Prepared Plate", "-", 4000),
            ("Yeast & Mould", "Vitamins & Contaminants", "", "Prepared Plate", "-", 4000),
            ("Total Coliform", "Vitamins & Contaminants", "", "Prepared Plate", "-", 4000),

            # Water Analysis
            *[(name, "Water Analysis", "", "Titrimetric", "-", 4000)
              for name in ["Total Alkalinity", "Total Acidity", "Total Dissolved Solid", "Total Hardness", "Chloride Ion"]]
        ]
        

        param_objs = {}
        for name, group, unit, method, ref_limit, price in param_data:
            obj, created = Parameter.objects.update_or_create(
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
            "Crude Fibre": (2.178, 2.328),
            "Crude Fat": (1.322, 1.434),
        }
        for name, (min_v, max_v) in specs.items():
            if name in param_objs:
                ControlSpec.objects.update_or_create(
                    parameter=param_objs[name],
                    defaults={"min_acceptable": min_v, "max_acceptable": max_v, "unit": "%"}
                )

        # 4. Equipment
        equipment_list = [
            ("Kjeltec Distillation Unit", "91819250", "8200", "FOSS"),
            ("Kjelroc Digestor", "01210-A-1097", "", "OPSIS Liquid Line"),
            ("Magnetic Stirrer", "","","",),
            ("Fibretec (Hot & Cold Extraction Unit)", "91816165", "FT 121 & 122", "FOSS"),
            ("Soxtec", "91703799", "2050", "FOSS"),
            ("Moisture Analyzer", "P1018035", "ML-50", "A&D"),
            ("Analytical Weighing Balance", "6A7701003", "HR-250AZ", "A&D"),
            ("Furnace", "21-102675", "AAF 1100", "Carbolite"),
            ("Bomb Calorimeter", "02-05106-221062", "CAL 3K-ST", "DDS Calorimeters"),
            ("Laboratory Oven", "H-906128", "", "Uniscope"),
            ("Cyclotec Laboratory Mill", "91839243", "CT293", "FOSS"),
            ("Centrifuge", "", "80-2", "Searchtech"),
            ("Spectrophotometer", "923-386", "CE 2021", "Cecil Instrument"),
            ("HPLC", "150-428", "System 4", "Cecil Instrument"),
            ("Digital Titrator", "", "", "Hirschman"),
            ("pH Meter", "", "GP 353", "EDT Instrument"),
            ("Viscometer", "", "SV10", "AND"),
            ("Viscometer", "", "VISCO", "ATAGO"),
            ("Salt Meter", "", "", "ATAGO"),
            ("Incubator", "", "DNP", "SearchTech Instrument"),
            ("Autoclave", "", "", "Biobase"),
            ("Centrifuge", "", "80-2", "SearchTech Instrument"),
            ("Water Purifier", "", "D-303A", "Biobase"),
            ("Colony Counter", "", "BC-50", "Biobase"),
            ("Ultrasonic Bath", "", "", "Grant"),
            ("Accuscan Gold", "Accu-024", "ASG-5420", "Neogen"),
        ]

        equip_objs = {}
        for name, serial, model, mfg in equipment_list:
            eq, _ = Equipment.objects.update_or_create(
                serial_number=serial,
                defaults={
                    "name": name,
                    "model": model,
                    "manufacturer": mfg,
                    "date_installed": date.today(),
                    "is_active": True,
                }
            )
            equip_objs[name] = eq

        # 5. Calibration
        calibrated_names = {
            "Laboratory Oven", "Furnace", "Cyclotec Laboratory Mill", "Centrifuge",
            "HPLC", "Bomb Calorimeter", "Soxtec", "Water Purifier",
            "Fibretec (Hot & Cold Extraction Unit)", "Kjeltec Distillation Unit",
            "Analytical Weighing Balance", "pH Meter", "Kjelroc Digestor",
            "Accuscan Gold", "Digital Titrator"
        }
        for name in calibrated_names:
            eq = equip_objs.get(name)
            if eq:
                CalibrationRecord.objects.update_or_create(
                    equipment=eq,
                    calibration_date=date(2024, 11, 1),
                    defaults={
                        "calibrated_by": "BV Global",
                        "expires_on": date(2025, 11, 1),
                        "comments": "Seeded with initial calibration status."
                    }
                )

        # 6. Equipment-to-Parameter Mapping
        map_table = {
            "Furnace": ["Ash"],
            "Moisture Analyzer": ["Moisture"],
            "Soxtec": ["Crude Fat"],
            "Kjelroc Digestor": ["Protein"],
            "Kjeltec Distillation Unit": ["Protein"],
            "Digital Titrator": ["Protein"],
            "Spectrophotometer": ["Alkaloids", "Flavonoids", "Tannins", "Saponins", "Phenolics"],
            "Accuscan Gold": ["Aflatoxin B1", "Total Aflatoxin"],
            "Bomb Calorimeter": ["Gross Energy"],
            "HPLC": [f"Vitamin {v}" for v in ["A", "B1", "B2", "B3", "B6", "B9", "B12", "C", "D", "E", "K"]],
            "Fibretec (Hot & Cold Extraction Unit)": ["Crude Fibre"]
        }

        for device, param_names in map_table.items():
            eq = equip_objs.get(device)
            if eq:
                for pname in param_names:
                    param = param_objs.get(pname)
                    if param:
                        eq.parameters_supported.add(param)

        self.stdout.write(self.style.SUCCESS("✅ All lab data seeded successfully."))


