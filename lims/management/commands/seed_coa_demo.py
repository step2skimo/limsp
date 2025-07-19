import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from lims.models import Client, Sample, Parameter, ParameterGroup, TestAssignment, TestResult, SampleStatus

User = get_user_model()

class Command(BaseCommand):
    help = "Seed COA demo data with clients, samples, and results"

    def add_arguments(self, parser):
        parser.add_argument("--clients", type=int, default=1, help="Number of clients to create")
        parser.add_argument("--max-samples", type=int, default=10, help="Max samples per client")
        parser.add_argument("--clear", action="store_true", help="Clear old demo data first")

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing old demo data...")
            TestResult.objects.all().delete()
            TestAssignment.objects.all().delete()
            Sample.objects.all().delete()
            Client.objects.all().delete()

        # ✅ Ensure ParameterGroup exists
        proximate_group, _ = ParameterGroup.objects.get_or_create(name="Proximate")

        # ✅ Ensure proximate parameters exist
        proximate_params = [
            ("Moisture", "%", "Oven (AOAC 930.15 2000)", "≤ 12%", 4000),
            ("Ash", "%", "Furnace (AOAC 942.05, 2000)", "≤ 5%", 4000),
            ("Crude Fibre", "%", "AOAC 978.10, 2000", "≤ 5%", 4000),
            ("Crude Fat", "%", "Soxhlet Extraction (AOAC 920.39)", "≥ 2%", 4000),
            ("Protein", "%", "Kjeldahl (AOAC 942.05 2000)", "≥ 10%", 4000),
        ]

        param_objs = []
        for name, unit, method, limit, price in proximate_params:
            param, _ = Parameter.objects.get_or_create(
                name=name,
                defaults={
                    "unit": unit,
                    "method": method,
                    "limit": limit,
                    "group": proximate_group,
                    "default_price": price,
                }
            )
            param_objs.append(param)

        # ✅ Ensure at least one analyst user exists
        analyst, _ = User.objects.get_or_create(username="demo_analyst", defaults={"password": "password123"})

        # ✅ Create clients, samples, assignments, and results
        for c in range(options["clients"]):
            client = Client.objects.create(
                name=f"Client {c+1}",
                organization="Demo Organization",
                address="123 Lab Street",
                email=f"client{c+1}@example.com",
                phone="08012345678",
                client_id=f"JGLSP{2500 + c+1}"
            )
            self.stdout.write(f"Created client: {client.name}")

            for i in range(options["max_samples"]):
                sample = Sample.objects.create(
                    client=client,
                    sample_code=f"SMP{c+1}{i+1:03d}",
                    sample_type="Feed",
                    weight=round(random.uniform(100, 500), 2),
                    status=SampleStatus.APPROVED,
                    received_date=timezone.now() - timedelta(days=random.randint(1, 7))
                )

                # Create TestAssignments + TestResults
                for param in param_objs:
                    assignment = TestAssignment.objects.create(
                        sample=sample,
                        parameter=param,
                        analyst=analyst,
                        status="completed"
                    )
                    TestResult.objects.create(
                        test_assignment=assignment,
                        value=round(random.uniform(1, 20), 2),
                        recorded_by=analyst
                    )

            self.stdout.write(self.style.SUCCESS(f"Created {options['max_samples']} samples for {client.name}"))

        self.stdout.write(self.style.SUCCESS("✅ COA demo data seeded successfully!"))
