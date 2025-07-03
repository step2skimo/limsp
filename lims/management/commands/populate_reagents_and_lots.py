from django.core.management.base import BaseCommand
from django.utils.timezone import now, timedelta
from lims.models.reagent import Reagent, ReagentLot
import random

class Command(BaseCommand):
    help = 'Populate extended reagents and auto-generate reagent lots for food & feed lab'

    def handle(self, *args, **kwargs):
        # Master reagent groups
        reagent_catalog = {
            "Proximate": [
                "Sulfuric Acid", "Copper Sulfate", "Sodium Hydroxide", "Petroleum Ether",
                "Hexane", "Diethyl Ether", "Acetone", "Hydrochloric Acid", "Ethanol",
                "Boric Acid", "Celite", "Mixed Indicator", "Sodium Sulfate"
            ],
            "General": [
                "Methanol", "Acetonitrile", "PBS Buffer", "Tween 20", "DCPIP", "EDTA",
                "Acetic Acid", "TCA", "Potassium Iodide", "Silver Nitrate",
                "Magnesium Sulfate", "Ferric Chloride", "Oxalic Acid", "Zinc Sulfate",
                "Sodium Thiosulfate", "Ammonium Molybdate"
            ],
            "Microbiology": [
                "Peptone Water", "MacConkey Agar", "XLD Agar", "Lactose Broth",
                "Buffered Peptone Water", "TTC Solution", "Sodium Azide", "Resazurin"
            ],
            "Vitamins": [
                "BHT", "PTAD", "Derivatization Buffer", "Cyanocobalamin",
                "ZnCl₂", "Vitamin Standards Mix", "Ascorbic Acid"
            ],
            "Energy & Reference": [
                "Benzoic Acid", "Gelatine Capsules", "Firing Wire", "Oxygen Gas"
            ],
            "Mycotoxins": [
                "Stop Solution (H2SO4)", "Aflatoxin B1 Standard", "ELISA Wash Buffer",
                "Sample Diluent", "Extraction Solvent (Methanol-Water 70:30)", "TMB Substrate"
            ]
        }

        units = ['mL', 'g', 'µL']
        today = now().date()
        total_reagents = 0
        total_lots = 0

        for group, names in reagent_catalog.items():
            for name in names:
                reagent, created = Reagent.objects.get_or_create(name=name)
                if created:
                    self.stdout.write(f"✅ Created reagent: {name} (Group: {group})")
                    total_reagents += 1
                else:
                    self.stdout.write(f"↩️ Reagent exists: {name}")

                # Generate lots
                for i in range(random.randint(2, 3)):
                    lot_number = f"{name[:3].upper()}-{random.randint(100,999)}"
                    quantity = round(random.uniform(10, 150), 1)
                    unit = random.choice(units)
                    expiry = today + timedelta(days=random.randint(30, 180))

                    ReagentLot.objects.create(
                        reagent=reagent,
                        lot_number=lot_number,
                        quantity=quantity,
                        unit=unit,
                        expiry_date=expiry,
                        status='active'
                    )
                    total_lots += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n🎉 Populated {total_reagents} unique reagents and {total_lots} reagent lots across {len(reagent_catalog)} categories."
            )
        )
