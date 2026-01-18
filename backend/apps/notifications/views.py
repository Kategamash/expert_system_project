from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from .models import Notification
from apps.publications.models import ReviewerAssignment

@login_required
def notification_list(request):
    qs = Notification.objects.filter(user=request.user)
    return render(request, "notifications/list.html", {"notifications": qs})


@login_required
def notification_detail(request, pk: int):
    n = get_object_or_404(Notification, pk=pk, user=request.user)

    if not n.is_read:
        n.is_read = True
        n.save(update_fields=["is_read"])

    process = n.process

    reviewer_comments = []
    library_comment = None

    if process:
        # Комментарии рецензеров (все непустые, не PENDING)
        qs = (process.review_assignments
              .exclude(comment="")
              .exclude(verdict=ReviewerAssignment.Verdict.PENDING)
              .select_related("reviewer")
              .order_by("reviewer_id"))

        for a in qs:
            reviewer_comments.append({
                "reviewer": a.reviewer.display_name(),
                "verdict": a.get_verdict_display(),
                "comment": a.comment,
                "decided_at": a.decided_at,
            })

        # Комментарий библиотеки
        ld = getattr(process, "library_decision", None)
        if ld and ld.comment:
            library_comment = {
                "decision": ld.get_decision_display(),
                "comment": ld.comment,
                "decided_at": ld.decided_at,
            }

    return render(request, "notifications/detail.html", {
        "notification": n,
        "process": process,
        "reviewer_comments": reviewer_comments,
        "library_comment": library_comment,
    })


@login_required
def mark_read(request, pk: int):
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    n.is_read = True
    n.save(update_fields=["is_read"])
    return redirect("notifications:list")


@login_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect("notifications:list")