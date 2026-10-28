from datetime import date, timedelta

from django.test import TestCase

from base.demo_data.modules.recruitment_showcase import seed_recruitment_showcase
from base.models import Department, JobPosition
from horilla.testkit import make_company, make_employee
from recruitment.models import (
    Candidate,
    CandidateDocument,
    CandidateRating,
    InterviewSchedule,
    Recruitment,
    RecruitmentSurvey,
    RejectedCandidate,
    Skill,
    SkillZoneCandidate,
)


class RecruitmentShowcaseTests(TestCase):
    def setUp(self):
        self.company = make_company("Recruitment Showcase Co")
        for index, title in enumerate(
            ("Analista de datos", "Especialista de soporte", "Coordinador de proyectos")
        ):
            department = Department.objects.create(department=f"Área de prueba {index}")
            department.company_id.add(self.company)
            JobPosition.objects.create(job_position=title, department_id=department)

        self.employee = make_employee(
            company=self.company, email="showcase.manager@test.horilla"
        )

    def test_seeds_related_examples_and_is_idempotent(self):
        today = date(2026, 10, 28)
        first = seed_recruitment_showcase(company=self.company, today=today)

        self.assertEqual(first["recruitments"], 3)
        self.assertEqual(first["candidates"], 15)
        self.assertEqual(first["interviews"], 6)
        self.assertEqual(first["skills"], 4)
        self.assertEqual(first["surveys"], 2)
        self.assertEqual(Recruitment.objects.count(), 3)
        self.assertEqual(Candidate.objects.count(), 15)
        self.assertFalse(
            Candidate.objects.filter(name__icontains="ejemplo").exists()
        )
        self.assertFalse(
            Candidate.objects.filter(name__iendswith=" (demo)").exists()
        )
        self.assertFalse(
            Candidate.objects.filter(email__iendswith="@example.test").exists()
        )
        self.assertFalse(
            Recruitment.objects.filter(title__icontains="ejemplo").exists()
        )
        self.assertEqual(InterviewSchedule.objects.count(), 6)
        self.assertEqual(CandidateRating.objects.count(), 15)
        self.assertEqual(SkillZoneCandidate.objects.count(), 9)
        self.assertEqual(RecruitmentSurvey.objects.count(), 2)
        self.assertEqual(RejectedCandidate.objects.count(), 3)
        self.assertEqual(CandidateDocument.objects.count(), 3)

        second = seed_recruitment_showcase(
            company=self.company, today=today + timedelta(days=14)
        )

        self.assertEqual(second["recruitments"], 0)
        self.assertEqual(second["candidates"], 0)
        self.assertEqual(second["interviews"], 0)
        self.assertEqual(Recruitment.objects.count(), 3)
        self.assertEqual(Candidate.objects.count(), 15)
        self.assertEqual(Skill.objects.count(), 4)
        self.assertEqual(InterviewSchedule.objects.count(), 6)

    def test_cleans_legacy_demo_candidate_labels_and_email_domain(self):
        seed_recruitment_showcase(company=self.company, today=date(2026, 10, 28))
        candidate = Candidate.objects.get(email="andrea.rojas.01@safezone.example")
        candidate.name = "Daniela Vega (Demo)"
        candidate.email = "daniela.vega@example.test"
        candidate.save(update_fields=("name", "email"))

        seed_recruitment_showcase(company=self.company, today=date(2026, 10, 28))

        candidate.refresh_from_db()
        self.assertEqual(candidate.name, "Daniela Vega")
        self.assertEqual(candidate.email, "daniela.vega@safezone.example")
        self.assertFalse(
            Candidate.objects.filter(name__iendswith=" (demo)").exists()
        )
        self.assertFalse(
            Candidate.objects.filter(email__iendswith="@example.test").exists()
        )
