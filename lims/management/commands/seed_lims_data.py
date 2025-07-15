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
            "Proximate", "Functional Properties", "Phytochemicals", "Protein Digestibility",
            "Oil Analysis", "Fiber Fractions", "Minerals",
            "Vitamins & Contaminants", "Water Analysis"
        ]
        groups = {name: ParameterGroup.objects.get_or_create(name=name)[0] for name in group_names}

        # 2. Parameters
        param_data = [
            # Proximate
            ("Moisture", "Proximate", "%", "Oven (AOAC 930.15 2000)", "≤ 12%", 4000),
            ("Ash", "Proximate", "%", "Furnace (AOAC 942.05, 2000)", "≤ 5%", 4000),
            ("Crude Fibre", "Proximate", "%", "AOAC 962.09, 2000", "≤ 5%", 4000),
            ("Crude Fat", "Proximate", "%", "Soxhlet Extraction (AOAC 2003.05)", "≥ 2%", 4000),
            ("Protein", "Proximate", "%", "Kjedahl (AOAC 984.13 2000)", "≥ 10%", 4000),
           

            # Functional Properties
            ("pH", "Functional Properties", "", "pH Meter", "-", 1000),
            ("Bulk Density", "Functional Properties", "", "Volumetric Cylinder", "-", 2000),
            ("Water Absorption", "Functional Properties", "", "Analytical Balance", "-", 2000),
            ("Oil Absorption", "Functional Properties", "", "Analytical Balance", "-", 2000),
            ("Swelling Index", "Functional Properties", "", "Measuring Cylinder", "-", 2000),
            ("Foaming Capacity", "Functional Properties", "", "Volumetric Cylinder", "-", 2000),
            ("Gelation Capacity", "Functional Properties", "", "Water Bath", "-", 2000),

            # Phytochemicals
            *[(name, "Phytochemicals", "", "Spectrophotometric", "-", 4500)
              for name in ["Alkaloids", "Flavonoids", "Tannins", "Saponins", "Phenolics"]],

            # Protein Digestibility
            ("Protein Digestibility", "Protein Digestibility", "", "AOAC", "-", 8000),
            ("FRAB", "Protein Digestibility", "", "-", "-", 5000),

            # Oil Analysis
            ("Total Free Fatty Acid", "Oil Analysis", "", "Titrimetric", "-", 3000),
            ("Peroxide Value", "Oil Analysis", "", "Titrimetric", "-", 4000),
            ("Iodine Value", "Oil Analysis", "", "Titrimetric", "-", 4000),
            ("Saponification Value", "Oil Analysis", "", "Titrimetric", "-", 3500),
            ("Acid/Titratable Acid Value", "Oil Analysis", "", "Titrimetric", "-", 3000),

            # Fiber Fractions
            *[(name, "Fiber Fractions", "", "AOAC", "-", 4500) for name in [
                "Neutral Detergent Fiber", "Acid Detergent Fiber", "Acid Detergent Lignin",
                "Cellulose", "Hemicelluloses", "Digestibility", "Dry Matter Intake",
                "Relative Feed Value", "Volatile Matter", "Fixed Carbon"
            ]],

            # Minerals
            ("Digestion (prep for AAS)", "Minerals", "", "-", "-", 1000),
            ("Elemental Determination (Ca, Mg, Zn...)", "Minerals", "", "AAS", "-", 1000),
            *[(name, "Minerals", "", "-", "-", 4500) for name in ["Nitrate", "Carbonate", "Bromate", "NaCl", "Organic Matter"]],
            ("Gross Energy", "Minerals", "kcal/kg", "Calorimeter", "-", 3500),

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
            ("Water Purifier", "", "D-303A", "Biobase"),
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


reagents = [
Reagent.objects.create(name="ACETONE/Liter", number_of_containers=7, quantity_per_container=1, unit="")
Reagent.objects.create(name="ACETONITIRATE HPLC GRADE", number_of_containers=2, quantity_per_container=1, unit="")
Reagent.objects.create(name="ALANINE", number_of_containers=1, quantity_per_container=1, unit="")
Reagent.objects.create(name="ALBUMIN", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="ALUMINIUM CHLORIDE", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="ALUTAMINE", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="AMMONIUM CHLORIDE", number_of_containers=1, quantity_per_container=1, unit="")
Reagent.objects.create(name="AMMONIA SOLUTION", number_of_containers=1, quantity_per_container=1, unit="")
Reagent.objects.create(name="AMMONIUM FERROUS", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="AMMONIUM HEPTAMOLYBDATE", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="AMMONIUM HYDROXIDE(2.5L)", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="AMMONIUM METAVANADATE(300g)", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="AMMONIUM MOLYBDATE", number_of_containers=1, quantity_per_container=1, unit="")
Reagent.objects.create(name="AMMONIUM MONOVANADATE", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="AMMONIUM SULFATE", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="AMMONIUM THIOCYNANATE", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="ANILINE", number_of_containers=1, quantity_per_container=1, unit="")
Reagent.objects.create(name="ANTHRONE(4g)", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="ARGININE", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="ASCORBIC ACID", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="ASPARAGINE", number_of_containers=1, quantity_per_container=1, unit="")
Reagent.objects.create(name="BARIUM CHLORIDE", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="BARIUM NITRATE", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="BENZENE", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="BORIC ACID 500g", number_of_containers=3, quantity_per_container=1, unit="")
Reagent.objects.create(name="BROMOCRESOL GREEN", number_of_containers=1, quantity_per_container=1, unit="")
Reagent.objects.create(name="CACIUM CARBONATE", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="CAESIUM CHLORIDE )", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="CASEIN PROTEIN RICH", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="CELITE 545(20g)", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="CHLOROFOAM(2.5L)", number_of_containers=2, quantity_per_container=1, unit="")
Reagent.objects.create(name="CTAB 100g", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="DIETHYL ETHER", number_of_containers=2, quantity_per_container=1, unit="")
Reagent.objects.create(name="DIETHYLENE GLYCOL(2.5l)", number_of_containers=2, quantity_per_container=1, unit="")
Reagent.objects.create(name="DISODIUM HYDROGEN OTHOPHOSPHATE", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="DI-SODIUM TETRABORATE", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="EDTA (500g)", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="EHANEDIOL", number_of_containers=1, quantity_per_container=1, unit="")
Reagent.objects.create(name="ETHANOL 2.5L", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="FERRIC CHLORIDE", number_of_containers=1, quantity_per_container=1, unit="")
Reagent.objects.create(name="FOMIC ACID", number_of_containers=1, quantity_per_container=1, unit="")
Reagent.objects.create(name="GIEMSA’S STAIN", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="GLACIAL ACETIC ACID", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="GLUCOSE", number_of_containers=0, quantity_per_container=1, unit="")
Reagent.objects.create(name="GLUTAMIC ACID", number_of_containers=1, quantity_per_container=1, unit="")
Reagent.objects.create(name="GLYCINE", number_of_containers=1, quantity_per_container=1, unit="")
Reagent.objects.create(name="HISTIDINE MONOHYDROCHLORIDE MONOHYDRATE", number_of_containers=1, quantity_per_container=1, unit="")
Reagent.objects.create(name="HYDROCHLORIC ACID 2.5L", number_of_containers=3, quantity_per_container=1, unit="")
Reagent.objects.create(name="ISOPROPYL ALCOHOL", number_of_containers=1, quantity_per_container=1, unit="")
Reagent.objects.create(name="L-ASCORBIC ACID", number_of_containers=2, quantity_per_container=1, unit="")
Reagent.objects.create(name="L-ASPARTIC", number_of_containers=1, quantity_per_container=1, unit="")
Reagent.objects.create(name="LEUCINE", number_of_containers=1, quantity_per_container=1, unit="")
Reagent.objects.create(name="L-ISOLEUCINE", number_of_containers=1, quantity_per_container=1, unit="")
Reagent.objects.create(name="L-PROLINE", number_of_containers=1, quantity_per_container=1, unit="")
Reagent.objects.create(name="LYSINE MONOCHLORIDE", number_of_containers=1, quantity_per_container=1, unit="")
Reagent.objects.create(name="METHANOL", number_of_containers=2, quantity_per_container=1, unit="")
Reagent.objects.create(name="METHIONINE", number_of_containers=1, quantity_per_container=1, unit="")
Reagent.objects.create(name="NINHYDRIN", number_of_containers=1, quantity_per_container=1, unit="")
Reagent.objects.create(name="NITRIC ACID 2.5L", number_of_containers=3, quantity_per_container=1, unit="")
Reagent.objects.create(name="N-OCTANOL", number_of_containers=1, quantity_per_container=1, unit="")

    {"name": "Glutamic Acid", "number_of_containers": 1},
    {"name": "Glycine", "number_of_containers": 1},
    {"name": "Histidine Monohydrochloride Monohydrate", "number_of_containers": 1},
    {"name": "Hydrochloric Acid 2.5L", "number_of_containers": 3},
    {"name": "Isopropyl Alcohol", "number_of_containers": 1},
    {"name": "L-Ascorbic Acid", "number_of_containers": 2},
    {"name": "L-Aspartic", "number_of_containers": 1},
    {"name": "Leucine", "number_of_containers": 1},
    {"name": "L-Isoleucine", "number_of_containers": 1},
    {"name": "L-Proline", "number_of_containers": 1},
    {"name": "Lysine Monochloride", "number_of_containers": 1},
    {"name": "Methanol", "number_of_containers": 2},
    {"name": "Methionine", "number_of_containers": 1},
    {"name": "Ninhydrin", "number_of_containers": 1},
    {"name": "Nitric Acid 2.5L", "number_of_containers": 3},
    {"name": "N-Octanol", "number_of_containers": 1},
    {"name": "Petroleum Spirit 2.5L", "number_of_containers": 6},
    {"name": "Phenolphthalein (20g)", "number_of_containers": 1},
    {"name": "Polyvinylpyrrolidone", "number_of_containers": 1},
    {"name": "Potassium Hydroxide", "number_of_containers": 1},

    # --- Batch 5 ---
    {"name": "Silica Gel", "number_of_containers": 2},
    {"name": "Sodium Chloride", "number_of_containers": 2},
    {"name": "Sodium Dihydrogen Phosphate", "number_of_containers": 1},
    {"name": "Sodium Hydroxide 500g", "number_of_containers": 4},
    {"name": "Sodium Lauryl Sulphate", "number_of_containers": 1},
    {"name": "Sulphosalicylic Acid", "number_of_containers": 1},
    {"name": "Sulphuric Acid 2.5L", "number_of_containers": 3},
    {"name": "Threonine", "number_of_containers": 1},
    {"name": "Tyrosine", "number_of_containers": 1},
    {"name": "Valine", "number_of_containers": 1},
    {"name": "Alanine", "number_of_containers": 1},
    {"name": "Aniline", "number_of_containers": 1},
    {"name": "Asparagine", "number_of_containers": 1},
    {"name": "Boric Acid 500g", "number_of_containers": 3},
    {"name": "Chlorofoam (2.5L)", "number_of_containers": 2},
    {"name": "CTAB 100g", "number_of_containers": 2},
    {"name": "Diethylene Glycol (2.5L)", "number_of_containers": 2},
    {"name": "Disodium Hydrogen Orthophosphate", "number_of_containers": 0},
    {"name": "Di-sodium Tetraborate", "number_of_containers": 0},
    {"name": "EDTA (500g)", "number_of_containers": 0},
