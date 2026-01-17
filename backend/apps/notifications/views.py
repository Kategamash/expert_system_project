from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from .models import Notification


@login_required
def notification_list(request):
    qs = Notification.objects.filter(user=request.user)
    return render(request, "notifications/list.html", {"notifications": qs})


@login_required
def mark_read(request, pk: int):
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    n.is_read = True
    n.save(update_fields=["is_read"])
    if n.link:
        return redirect(n.link)
    return redirect("notifications:list")


@login_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect("notifications:list")