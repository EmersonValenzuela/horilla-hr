"""Seed safe, clearly synthetic examples across the Recruitment module."""

from __future__ import annotations

import json
import logging
from datetime import date, time, timedelta

from django.apps import apps
from django.db import transaction

logger = logging.getLogger(__name__)

SHOWCASE_CANDIDATES = (
    ("Andrea Rojas", "female"),
    ("Mateo Salas", "male"),
    ("Valeria Paredes", "female"),
    ("Diego Luna", "male"),
    ("Camila Torres", "female"),
)

SHOWCASE_SKILLS = (
    "Análisis de datos",
    "Comunicación",
    "Gestión de proyectos",
    "Resolución de problemas",
)


@transaction.atomic
def seed_recruitment_showcase(
    *, company=None, today: date | None = None
) -> dict[str, int]:
    """Create idempotent recruitment examples without replacing user records."""
    empty_result = {
        "recruitments": 0,
        "candidates": 0,
        "interviews": 0,
        "skills": 0,
        "surveys": 0,
        "talent_pool_entries": 0,
    }
    if not apps.is_installed("recruitment"):
        return empty_result

    from base.models import Company, JobPosition
    from employee.models import Employee
    from recruitment.models import (
        Candidate,
        CandidateDocumentRequest,
        CandidateRating,
        InterviewSchedule,
        QuestionOrdering,
        Recruitment,
        RecruitmentSurvey,
        RecruitmentSurveyAnswer,
        RejectReason,
        RejectedCandidate,
        Skill,
        SkillZone,
        SkillZoneCandidate,
        Stage,
        StageNote,
        SurveyTemplate,
    )

    today = today or date.today()
    company = company or Company._base_manager.filter(hq=True).order_by("id").last()
    company = company or Company._base_manager.order_by("id").first()
    if company:
        legacy_candidates = Candidate._base_manager.filter(
            recruitment_id__company_id=company,
            name__iendswith=" (Demo)",
            email__iendswith="@example.test",
        ).only("pk", "name", "email")
        for candidate in legacy_candidates:
            name = candidate.name[: -len(" (Demo)")]
            local_part = candidate.email.rsplit("@", 1)[0]
            email = f"{local_part}@safezone.example"
            if Candidate._base_manager.filter(email__iexact=email).exclude(
                pk=candidate.pk
            ).exists():
                email = f"{local_part}.{candidate.pk}@safezone.example"
            Candidate._base_manager.filter(pk=candidate.pk).update(
                name=name, email=email
            )

    employees = (
        list(
            Employee._base_manager.filter(
                employee_work_info__company_id=company
            ).order_by("id")[:2]
        )
        if company
        else []
    )
    positions = (
        list(
            JobPosition._base_manager.filter(
                department_id__company_id=company
            ).order_by("id")[:3]
        )
        if company
        else []
    )
    if not company or not employees or not positions:
        logger.warning(
            "Recruitment showcase skipped: a company, employee, and job position "
            "are required."
        )
        return empty_result

    for recruitment in Recruitment._base_manager.filter(
        company_id=company, title__icontains=" de demostración"
    ):
        recruitment.title = recruitment.title.replace(" de demostración", "")
        recruitment.save(update_fields=("title",))

    result = empty_result.copy()
    skills = []
    for title in SHOWCASE_SKILLS:
        skill, created = Skill._base_manager.get_or_create(title=title)
        skills.append(skill)
        result["skills"] += int(created)

    template_title = "Encuesta de selección Safe Zone"
    template = SurveyTemplate._base_manager.filter(
        title__in=(template_title, "Encuesta de selección (ejemplo Safe Zone)")
    ).order_by("id").first()
    if template:
        template.title = template_title
        template.description = "Preguntas para el proceso de selección."
        template.save(update_fields=("title", "description"))
    else:
        template = SurveyTemplate._base_manager.create(
            title=template_title,
            description="Preguntas para el proceso de selección.",
            company_id=company,
        )
    questions = []
    question_data = (
        (
            "¿Qué experiencia relevante aportarías al puesto?",
            "textarea",
            "",
            "¿Qué experiencia relevante aportarías al puesto? (Ejemplo)",
        ),
        (
            "¿Cuántos años de experiencia tienes en esta área?",
            "number",
            "",
            "¿Cuántos años de experiencia tienes en esta área? (Ejemplo)",
        ),
    )
    for sequence, (text, question_type, options, legacy_text) in enumerate(
        question_data
    ):
        question = RecruitmentSurvey._base_manager.filter(
            question__in=(text, legacy_text), type=question_type
        ).order_by("id").first()
        created = question is None
        if created:
            question = RecruitmentSurvey._base_manager.create(
                question=text,
                type=question_type,
                is_mandatory=sequence == 0,
                sequence=sequence,
                options=options,
            )
        elif question.question != text:
            question.question = text
            question.save(update_fields=("question",))
        question.template_id.add(template)
        question.job_position_ids.add(*positions)
        questions.append(question)
        result["surveys"] += int(created)

    pool_title = "Perfiles de talento Safe Zone"
    pool = SkillZone._base_manager.filter(
        title__in=(pool_title, "Perfiles de talento (ejemplo Safe Zone)")
    ).order_by("id").first()
    if pool:
        pool.title = pool_title
        pool.description = "Perfiles disponibles para futuras convocatorias."
        pool.save(update_fields=("title", "description"))
    else:
        pool = SkillZone._base_manager.create(
            title=pool_title,
            description="Perfiles disponibles para futuras convocatorias.",
            company_id=company,
        )

    rejection_title = "Experiencia no alineada"
    rejection_reason = RejectReason._base_manager.filter(
        title__in=(rejection_title, "Experiencia no alineada (ejemplo)")
    ).order_by("id").first()
    if rejection_reason:
        rejection_reason.title = rejection_title
        rejection_reason.description = (
            "Experiencia no alineada con los requisitos del puesto."
        )
        rejection_reason.save(update_fields=("title", "description"))
    else:
        rejection_reason = RejectReason._base_manager.create(
            title=rejection_title,
            description="Experiencia no alineada con los requisitos del puesto.",
            company_id=company,
        )

    document_title = "Documento de identidad"
    document_request = CandidateDocumentRequest._base_manager.filter(
        title__in=(document_title, "Documento de identidad (ejemplo)"),
        format="pdf",
    ).order_by("id").first()
    if document_request:
        document_request.title = document_title
        document_request.max_size = 5
        document_request.description = (
            "Adjunte su documento de identidad en formato PDF."
        )
        document_request.save(update_fields=("title", "max_size", "description"))
    else:
        document_request = CandidateDocumentRequest._base_manager.create(
            title=document_title,
            format="pdf",
            max_size=5,
            description="Adjunte su documento de identidad en formato PDF.",
        )

    stage_types = (
        ("test", "Prueba técnica", 2),
        ("interview", "Entrevista", 3),
        ("hired", "Seleccionado", 4),
        ("cancelled", "No seleccionado", 5),
    )
    status_by_stage = {
        "applied": "not_sent",
        "test": "sent",
        "interview": "sent",
        "hired": "joined",
        "cancelled": "rejected",
    }
    candidates_for_documents = []
    interview_index = 0

    for position_index, position in enumerate(positions):
        title = f"Convocatoria: {position.job_position}"[:50]
        legacy_title = f"Ejemplo: {position.job_position}"[:50]
        start_date = today - timedelta(days=30 + position_index)
        while Recruitment._base_manager.filter(
            job_position_id=position, start_date=start_date
        ).exists():
            start_date -= timedelta(days=1)
        description = f"Proceso de selección para {position.job_position}."
        recruitment = Recruitment._base_manager.filter(
            title__in=(title, legacy_title),
            company_id=company,
            job_position_id=position,
        ).order_by("id").first()
        recruitment_created = recruitment is None
        if recruitment_created:
            recruitment = Recruitment._base_manager.create(
                title=title,
                description=description,
                company_id=company,
                job_position_id=position,
                vacancy=2,
                start_date=start_date,
                closed=False,
                is_published=True,
                optional_resume=True,
                optional_profile_image=True,
            )
        elif recruitment.title != title or recruitment.description != description:
            recruitment.title = title
            recruitment.description = description
            recruitment.save(update_fields=("title", "description"))
        result["recruitments"] += int(recruitment_created)
        recruitment.open_positions.add(position)
        recruitment.recruitment_managers.add(*employees)
        recruitment.survey_templates.add(template)
        recruitment.skills.add(*skills)

        applied_stage = Stage._base_manager.get(
            recruitment_id=recruitment, stage_type="applied"
        )
        if recruitment_created:
            applied_stage.stage = "Postulación recibida"
            applied_stage.save(update_fields=("stage",))
            Stage._base_manager.filter(
                recruitment_id=recruitment, stage_type="initial"
            ).update(stage="Revisión inicial")

        stages = {"applied": applied_stage}
        for stage_type, stage_name, sequence in stage_types:
            stage, _ = Stage._base_manager.get_or_create(
                recruitment_id=recruitment,
                stage=stage_name,
                defaults={"stage_type": stage_type, "sequence": sequence},
            )
            stage.stage_managers.add(*employees)
            stages[stage_type] = stage

        for question_index, question in enumerate(questions):
            QuestionOrdering._base_manager.get_or_create(
                question_id=question,
                recruitment_id=recruitment,
                defaults={"sequence": question_index},
            )

        for candidate_index, (name, gender) in enumerate(SHOWCASE_CANDIDATES):
            sequence = position_index * len(SHOWCASE_CANDIDATES) + candidate_index + 1
            stage_type = ("applied", "test", "interview", "hired", "cancelled")[
                candidate_index
            ]
            email = (
                f"{name.lower().replace(' ', '.')}.{sequence:02d}@safezone.example"
            )
            legacy_email = f"demo.candidate.{sequence:02d}@safezone.example"
            candidate = Candidate._base_manager.filter(
                email__in=(email, legacy_email)
            ).first()
            candidate_created = candidate is None
            candidate_fields = {
                "name": name,
                "gender": gender,
                "recruitment_id": recruitment,
                "job_position_id": position,
                "stage_id": stages[stage_type],
                "resume": "",
                "mobile": f"999000{sequence:04d}",
                "source": ("application", "software", "other")[candidate_index % 3],
                "referral_source": (
                    "company_career_site",
                    "job_board",
                    "social_media",
                    "employee_referral",
                    "other",
                )[candidate_index],
                "joining_date": today if stage_type == "hired" else None,
                "sequence": sequence,
            }
            if candidate_created:
                candidate = Candidate._base_manager.create(
                    email=email, **candidate_fields
                )
            else:
                updated_fields: dict[str, str] = {}
                if candidate.name != name:
                    updated_fields["name"] = name
                    candidate.name = name
                if candidate.email != email:
                    updated_fields["email"] = email
                    candidate.email = email
                if updated_fields:
                    Candidate._base_manager.filter(pk=candidate.pk).update(
                        **updated_fields
                    )
            result["candidates"] += int(candidate_created)
            Candidate._base_manager.filter(pk=candidate.pk).update(
                offer_letter_status=status_by_stage[stage_type]
            )

            CandidateRating._base_manager.get_or_create(
                employee_id=employees[candidate_index % len(employees)],
                candidate_id=candidate,
                defaults={"rating": 3 + candidate_index % 3},
            )

            if stage_type in {"applied", "test", "interview"}:
                _, pool_entry_created = (
                    SkillZoneCandidate._base_manager.update_or_create(
                        skill_zone_id=pool,
                        candidate_id=candidate,
                        defaults={
                            "reason": "Perfil con potencial para futuras vacantes."
                        },
                    )
                )
                result["talent_pool_entries"] += int(pool_entry_created)

            if stage_type in {"test", "interview"}:
                interview_date = today + timedelta(days=interview_index + 1)
                interview_description = (
                    "Entrevista para revisar experiencia y competencias del puesto."
                )
                interview = InterviewSchedule._base_manager.filter(
                    candidate_id=candidate,
                    description__in=(
                        interview_description,
                        "Entrevista de ejemplo para revisar experiencia y "
                        "competencias del puesto.",
                    ),
                ).first()
                interview_created = interview is None
                if interview_created:
                    interview = InterviewSchedule._base_manager.create(
                        candidate_id=candidate,
                        interview_date=interview_date,
                        interview_time=time(10 + interview_index % 6, 0),
                        description=interview_description,
                    )
                else:
                    interview.interview_date = interview_date
                    interview.interview_time = time(10 + interview_index % 6, 0)
                    interview.description = interview_description
                    interview.completed = False
                    interview.save(
                        update_fields=(
                            "interview_date",
                            "interview_time",
                            "description",
                            "completed",
                        )
                    )
                interview.employee_id.add(employees[interview_index % len(employees)])
                result["interviews"] += int(interview_created)
                interview_index += 1

            if stage_type == "cancelled":
                rejected, _ = RejectedCandidate._base_manager.update_or_create(
                    candidate_id=candidate,
                    defaults={
                        "description": "Candidatura cerrada tras la evaluación."
                    },
                )
                rejected.reject_reason_id.add(rejection_reason)

            if stage_type == "interview":
                stage_note = StageNote._base_manager.filter(
                    candidate_id=candidate,
                    stage_id=stages[stage_type],
                    description__in=(
                        "Entrevista inicial coordinada.",
                        "Entrevista inicial coordinada (registro de ejemplo).",
                    ),
                ).first()
                if stage_note:
                    stage_note.description = "Entrevista inicial coordinada."
                    stage_note.save(update_fields=("description",))
                else:
                    StageNote._base_manager.create(
                        candidate_id=candidate,
                        stage_id=stages[stage_type],
                        description="Entrevista inicial coordinada.",
                        updated_by=employees[0],
                        candidate_can_view=False,
                    )

            if stage_type == "hired":
                candidates_for_documents.append(candidate)

            if stage_type in {"test", "interview", "hired"}:
                answer_data = {
                    str(questions[0].pk): (
                        "Cuento con experiencia relacionada con el puesto."
                    ),
                    str(questions[1].pk): str(2 + candidate_index),
                }
                RecruitmentSurveyAnswer._base_manager.update_or_create(
                    candidate_id=candidate,
                    recruitment_id=recruitment,
                    defaults={
                        "job_position_id": position,
                        "answer_json": json.dumps(
                            answer_data, ensure_ascii=False
                        ),
                    },
                )

    if candidates_for_documents:
        document_request.candidate_id.add(*candidates_for_documents)

    logger.info("Recruitment showcase seeded: %s", result)
    return result
