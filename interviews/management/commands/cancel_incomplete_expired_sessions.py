from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from interviews.models import InterviewSession, Question, SessionLog


class Command(BaseCommand):
    help = (
        "Cancel interview sessions where the candidate link is no longer valid "
        "(campaign ended or session expired) AND not all required responses were submitted."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only show what would change without updating the database",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        dry_run = options.get("dry_run", False)

        # We only consider sessions that are not already terminal
        # i.e., not completed, cancelled, or expired
        qs = (
            InterviewSession.objects
            .select_related("campaign", "candidate")
            .prefetch_related("responses__question", "campaign__questions")
            .exclude(status__in=["completed", "cancelled"])  # consider only non-terminal
        )

        sessions_to_cancel = []
        total_checked = 0

        for session in qs.iterator():
            total_checked += 1

            campaign = session.campaign
            # A link is considered no longer valid if:
            # - Campaign ended (end_date in the past or campaign inactive)
            # - OR session expired (expires_at in the past)
            link_invalid = False
            try:
                if campaign.end_date and campaign.end_date < now:
                    link_invalid = True
                if hasattr(campaign, "is_active") and campaign.is_active is False:
                    link_invalid = True
            except Exception:
                # Be permissive: don't break the iteration on data issues
                pass

            if session.expires_at and session.expires_at < now:
                link_invalid = True

            if not link_invalid:
                continue

            # Determine required questions count
            try:
                required_qs_count = campaign.questions.filter(is_required=True).count()
                if required_qs_count == 0:
                    # If no required questions identified, fall back to total questions
                    required_qs_count = campaign.questions.count()
            except Exception:
                # If campaign questions cannot be loaded, skip this session safely
                continue

            # Count distinct responses per required questions
            responses_q_ids = set(
                session.responses.values_list("question_id", flat=True)
            )
            submitted_required = (
                campaign.questions.filter(is_required=True, id__in=responses_q_ids).count()
                if required_qs_count > 0 else 0
            )

            completed_all_required = submitted_required >= required_qs_count and required_qs_count > 0

            # Only cancel if candidate had started the interview
            if session.status in ("started", "in_progress") and not completed_all_required:
                sessions_to_cancel.append(session)

        if dry_run:
            self.stdout.write(self.style.WARNING("[DRY RUN]"))
            self.stdout.write(
                f"Would cancel {len(sessions_to_cancel)} sessions out of {total_checked} checked."
            )
            for s in sessions_to_cancel[:50]:
                self.stdout.write(
                    f" - session={s.id} candidate={getattr(s.candidate, 'email', None)} campaign={getattr(s.campaign, 'title', None)}"
                )
            if len(sessions_to_cancel) > 50:
                self.stdout.write("   ... (truncated) ...")
            return

        updated_count = 0
        with transaction.atomic():
            for session in sessions_to_cancel:
                previous_status = session.status
                session.status = "cancelled"
                session.save(update_fields=["status"])  # keep timestamps unchanged
                updated_count += 1

                try:
                    SessionLog.objects.create(
                        session=session,
                        log_type="status_update",
                        message="Session auto-cancelled: link invalid and incomplete responses",
                        metadata={
                            "previous_status": previous_status,
                            "reason": "link_invalid_and_incomplete",
                        },
                    )
                except Exception:
                    # Do not fail the job for logging issues
                    pass

        self.stdout.write(
            self.style.SUCCESS(
                f"Cancelled {updated_count} sessions (checked {total_checked})."
            )
        )
