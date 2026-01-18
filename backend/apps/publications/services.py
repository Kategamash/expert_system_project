import random
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.notifications.utils import notify
from .models import Process, LibraryDecision, ReviewerAssignment, OEKDecision

User = get_user_model()


def start_or_advance_after_creation(process: Process):
    """
    После создания заявки:
    - если есть соавторы -> ждём согласия
    - иначе -> отправляем в библиотеку
    """
    if process.coauthors.exists():
        process.status = Process.Status.WAITING_COAUTHOR_CONSENTS
        process.save(update_fields=["status"])
        notify(process.author, f"Заявка #{process.pk}: загрузите согласия соавторов.", link=f"/process/{process.pk}/", process=process)
    else:
        send_to_library(process)


def all_coauthor_consents_uploaded(process: Process) -> bool:
    if not process.coauthors.exists():
        return True
    return all(bool(c.consent_file) for c in process.coauthors.all())


def try_advance_after_coauthor_consents(process: Process):
    if process.status != Process.Status.WAITING_COAUTHOR_CONSENTS:
        return
    if all_coauthor_consents_uploaded(process):
        send_to_library(process)


def send_to_library(process: Process):
    process.status = Process.Status.LIBRARY_REVIEW
    process.save(update_fields=["status"])

    LibraryDecision.objects.get_or_create(process=process)

    librarian = User.objects.filter(role=User.Role.LIBRARY_HEAD).order_by("id").first()
    if librarian:
        notify(librarian, f"Новая задача: проверить литературу по заявке #{process.pk}", link=f"/tasks/library/")
    notify(process.author, f"Заявка #{process.pk} отправлена в библиотеку на проверку.", link=f"/process/{process.pk}/", process=process)


def library_apply_decision(process: Process, approved: bool, comment: str, librarian: User):
    ld, _ = LibraryDecision.objects.get_or_create(process=process)
    ld.librarian = librarian
    ld.comment = comment
    ld.decided_at = timezone.now()

    if approved:
        ld.decision = LibraryDecision.Decision.APPROVED
        ld.save()

        if process.is_mifi:
            assign_reviewers(process)
        else:
            send_to_oek(process)

        notify(process.author, f"Библиотека согласовала заявку #{process.pk}.", link=f"/process/{process.pk}/", process=process)
    else:
        ld.decision = LibraryDecision.Decision.REJECTED
        ld.save()
        process.status = Process.Status.LIBRARY_NEEDS_FIX
        process.save(update_fields=["status"])
        notify(process.author, f"Библиотека отклонила заявку #{process.pk}. Комментарий: {comment}", link=f"/process/{process.pk}/", process=process)


def reset_reviewers(process: Process):
    # set all to pending, clear decided_at/comment/verdict
    for a in process.review_assignments.all():
        a.verdict = ReviewerAssignment.Verdict.PENDING
        a.comment = ""
        a.decided_at = None
        a.save()


def assign_reviewers(process: Process):
    process.status = Process.Status.INTERNAL_REVIEW
    process.save(update_fields=["status"])

    reviewers = list(User.objects.filter(role=User.Role.REVIEWER).order_by("id"))
    if len(reviewers) < 3:
        # fallback: assign whoever exists
        chosen = reviewers
    else:
        chosen = random.sample(reviewers, 3)

    # Create assignments (idempotent-ish)
    for r in chosen:
        ReviewerAssignment.objects.get_or_create(process=process, reviewer=r)

    for r in chosen:
        notify(r, f"Новая рецензия: заявка #{process.pk}", link=f"/tasks/reviewer/")

    notify(process.author, f"Заявка #{process.pk} отправлена на внутреннее рецензирование.", link=f"/process/{process.pk}/", process=process)


def reviewer_submit(assignment: ReviewerAssignment, verdict: str, comment: str):
    assignment.verdict = verdict
    assignment.comment = comment
    assignment.decided_at = timezone.now()
    assignment.save()

    process = assignment.process
    notify(process.author, f"Получена рецензия по заявке #{process.pk} от {assignment.reviewer.display_name()}.", link=f"/process/{process.pk}/", process=process)

    # If all decided -> finalize stage
    if process.review_assignments.filter(verdict=ReviewerAssignment.Verdict.PENDING).exists():
        return

    verdicts = list(process.review_assignments.values_list("verdict", flat=True))
    not_rec = verdicts.count(ReviewerAssignment.Verdict.NOT_RECOMMEND)
    after_fix = verdicts.count(ReviewerAssignment.Verdict.RECOMMEND_AFTER_FIX)
    rec = verdicts.count(ReviewerAssignment.Verdict.RECOMMEND)

    # rule: if 2 of 3 NOT -> rejected
    if not_rec >= 2:
        process.status = Process.Status.REJECTED
        process.save(update_fields=["status"])
        notify(process.author, f"Заявка #{process.pk} отклонена по результатам рецензирования (>=2 'Не рекомендовать').", link=f"/process/{process.pk}/", process=process)
        return

    # if any AFTER_FIX -> needs fix
    if after_fix >= 1:
        process.status = Process.Status.INTERNAL_REVIEW_NEEDS_FIX
        process.save(update_fields=["status"])
        notify(process.author, f"Заявка #{process.pk}: требуется исправление по рецензиям и повторная отправка.", link=f"/process/{process.pk}/", process=process)
        return

    # else if 2 recommend -> go next
    if rec >= 2:
        send_to_oek(process)
        return

    # fallback
    process.status = Process.Status.INTERNAL_REVIEW_NEEDS_FIX
    process.save(update_fields=["status"])
    notify(process.author, f"Заявка #{process.pk}: требуется уточнение/исправление по рецензиям.", link=f"/process/{process.pk}/", process=process)


def author_resubmit_after_internal_fix(process: Process):
    """
    Автор исправил материалы и отправляет снова тем же рецензентам.
    """
    if process.status != Process.Status.INTERNAL_REVIEW_NEEDS_FIX:
        return
    reset_reviewers(process)
    process.status = Process.Status.INTERNAL_REVIEW
    process.save(update_fields=["status"])
    for a in process.review_assignments.all():
        notify(a.reviewer, f"Повторная рецензия: заявка #{process.pk}", link=f"/tasks/reviewer/")
    notify(process.author, f"Заявка #{process.pk} отправлена на повторное рецензирование.", link=f"/process/{process.pk}/", process=process)


def send_to_oek(process: Process):
    process.status = Process.Status.OEK_REVIEW
    process.save(update_fields=["status"])

    OEKDecision.objects.get_or_create(process=process)

    oek_user = User.objects.filter(role=User.Role.OEK).order_by("id").first()
    if oek_user:
        notify(oek_user, f"Новая задача ОЭК: проверить заявку #{process.pk}", link=f"/tasks/oek/")
    notify(process.author, f"Заявка #{process.pk} отправлена в ОЭК.", link=f"/process/{process.pk}/", process=process)


def oek_apply_decision(process: Process, approved: bool, comment: str, oek_user: User, defense_datetime=None, defense_room=""):
    od, _ = OEKDecision.objects.get_or_create(process=process)
    od.oek_user = oek_user
    od.comment = comment
    od.decided_at = timezone.now()

    if approved:
        od.decision = OEKDecision.Decision.APPROVED
        od.save()

        process.status = Process.Status.READY_FOR_DEFENSE
        if defense_datetime:
            process.defense_datetime = defense_datetime
        if defense_room is not None:
            process.defense_room = defense_room
        process.save(update_fields=["status", "defense_datetime", "defense_room"])

        notify(process.author, f"ОЭК согласовал заявку #{process.pk}. Статус: готово к защите.", link=f"/process/{process.pk}/", process=process)

        # notify commission members
        commission_users = User.objects.filter(role=User.Role.COMMISSION)
        for u in commission_users:
            notify(u, f"Новая заявка готова к защите: #{process.pk}", link=f"/process/{process.pk}/")
    else:
        od.decision = OEKDecision.Decision.REJECTED
        od.save()
        process.status = Process.Status.OEK_NEEDS_FIX
        process.save(update_fields=["status"])
        notify(process.author, f"ОЭК отклонил заявку #{process.pk}. Комментарий: {comment}", link=f"/process/{process.pk}/", process=process)


def author_resubmit_after_oek_fix(process: Process):
    if process.status != Process.Status.OEK_NEEDS_FIX:
        return
    process.status = Process.Status.OEK_REVIEW
    process.save(update_fields=["status"])
    oek_user = User.objects.filter(role=User.Role.OEK).order_by("id").first()
    if oek_user:
        notify(oek_user, f"Повторная проверка ОЭК: заявка #{process.pk}", link=f"/tasks/oek/")
    notify(process.author, f"Заявка #{process.pk} повторно отправлена в ОЭК.", link=f"/process/{process.pk}/", process=process)

def author_resubmit_after_library_fix(process: Process):
    """
    Автор загрузил исправленный список литературы и отправляет снова в библиотеку.
    """
    if process.status != Process.Status.LIBRARY_NEEDS_FIX:
        return

    # сбрасываем решение библиотеки в ожидание
    ld, _ = LibraryDecision.objects.get_or_create(process=process)
    ld.decision = LibraryDecision.Decision.PENDING
    ld.decided_at = None
    ld.save(update_fields=["decision", "decided_at"])

    process.status = Process.Status.LIBRARY_REVIEW
    process.save(update_fields=["status"])

    librarian = User.objects.filter(role=User.Role.LIBRARY_HEAD).order_by("id").first()
    if librarian:
        notify(librarian, f"Повторная проверка: литература по заявке #{process.pk}", link=f"/tasks/library/")

    notify(
        process.author,
        f"Заявка #{process.pk} повторно отправлена в библиотеку на проверку.",
        link=f"/process/{process.pk}/",
        process=process,
    )