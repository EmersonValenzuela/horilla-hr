from django.core.management.base import BaseCommand

from base.demo_data.modules.recruitment_showcase import seed_recruitment_showcase


class Command(BaseCommand):
    help = "Add safe, synthetic example records to the Recruitment module."

    def handle(self, *args, **options):
        result = seed_recruitment_showcase()
        totals = ", ".join(f"{key}={value}" for key, value in result.items())
        self.stdout.write(self.style.SUCCESS(f"Recruitment examples ready: {totals}"))
