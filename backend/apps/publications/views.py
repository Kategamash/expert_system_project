from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from apps.accounts.models import User
from apps.accounts.permissions import role_required
from apps.notifications.utils import notify

from .forms import (
    ProcessCreateForm, DocumentsForm, CoAuthorFormSet,
    UploadConsentForm, LibraryDecisionForm, ReviewerVerdictForm, OEKDecisionForm
)
from .models import Process, PublicationTemplate, CoAuthor, ReviewerAssignment
from .services import (
    start_or_advance_after_creation,
    try_advance_after_coauthor_consents,
    library_apply_decision,
    reviewer_submit,
    author_resubmit_after_internal_fix,
    oek_apply_decision,
    author_resubmit_after_oek_fix,
)


@login_required
def dashboard(request):
    """
    Единая точка входа:
    - AUTHOR видит свои процессы
    - LIBRARY_HEAD видит задачи библиотеки
    - REVIEWER видит задачи рецензирования
    - OEK видит задачи ОЭК
    - COMMISSION видит процессы READY_FOR_DEFENSE
    """
    user = request.user

    context = {"role": user.role}

    if user.role == User.Role.AUTHOR:
        context["processes"] = Process.objects.filter(author=user).order_by("-created_at")
        return render(request, "publications/dashboard.html", context)

    if user.role == User.Role.LIBRARY_HEAD:
        context["processes"] = Process.objects.filter(status=Process.Status.LIBRARY_REVIEW).order_by("created_at")
        return render(request, "publications/dashboard.html", context)

    if user.role == User.Role.REVIEWER:
        context["assignments"] = ReviewerAssignment.objects.filter(reviewer=user).order_by("-process__created_at")
        return render(request, "publications/dashboard.html", context)

    if user.role == User.Role.OEK:
        context["processes"] = Process.objects.filter(status=Process.Status.OEK_REVIEW).order_by("created_at")
        return render(request, "publications/dashboard.html", context)

    if user.role == User.Role.COMMISSION:
        context["processes"] = Process.objects.filter(status=Process.Status.READY_FOR_DEFENSE).order_by("-updated_at")
        return render(request, "publications/dashboard.html", context)

    # fallback for superuser/others
    context["processes"] = Process.objects.all().order_by("-created_at")[:50]
    return render(request, "publications/dashboard.html", context)


@login_required
def process_list(request):
    if request.user.role == User.Role.AUTHOR:
        qs = Process.objects.filter(author=request.user).order_by("-created_at")
    else:
        qs = Process.objects.all().order_by("-created_at")
    return render(request, "publications/process_list.html", {"processes": qs})


@login_required
def process_create(request):
    if request.user.role != User.Role.AUTHOR and not request.user.is_superuser:
        return redirect("publications:dashboard")

    if request.method == "POST":
        p_form = ProcessCreateForm(request.POST)
        d_form = DocumentsForm(request.POST, request.FILES)
        formset = CoAuthorFormSet(request.POST, queryset=CoAuthor.objects.none())

        if p_form.is_valid() and d_form.is_valid() and formset.is_valid():
            process = p_form.save(commit=False)
            process.author = request.user
            process.save()

            # docs
            docs = d_form.save(commit=False)
            docs.process = process
            docs.save()

            # coauthors
            for f in formset:
                if f.cleaned_data and not f.cleaned_data.get("DELETE", False):
                    obj = f.save(commit=False)
                    obj.process = process
                    obj.save()

            start_or_advance_after_creation(process)
            messages.success(request, f"Заявка создана: #{process.pk}")
            return redirect("publications:process_detail", pk=process.pk)
    else:
        p_form = ProcessCreateForm()
        d_form = DocumentsForm()
        formset = CoAuthorFormSet(queryset=CoAuthor.objects.none())

    templates = PublicationTemplate.objects.filter(department=request.user.department).order_by("name")

    return render(
        request,
        "publications/process_create.html",
        {"p_form": p_form, "d_form": d_form, "formset": formset, "templates": templates},
    )


@login_required
def process_detail(request, pk: int):
    process = get_object_or_404(Process, pk=pk)

    # access control:
    if request.user.role == User.Role.AUTHOR and process.author != request.user and not request.user.is_superuser:
        raise Http404()

    # Actions by author: resubmit after fixes
    if request.method == "POST" and request.user.role == User.Role.AUTHOR:
        action = request.POST.get("action")

        if action == "resubmit_internal":
            author_resubmit_after_internal_fix(process)
            messages.success(request, "Отправлено на повторное рецензирование.")
            return redirect("publications:process_detail", pk=process.pk)

        if action == "resubmit_oek":
            author_resubmit_after_oek_fix(process)
            messages.success(request, "Повторно отправлено в ОЭК.")
            return redirect("publications:process_detail", pk=process.pk)

    return render(request, "publications/process_detail.html", {"process": process})


@login_required
def template_download(request, pk: int):
    tpl = get_object_or_404(PublicationTemplate, pk=pk)
    if not tpl.file:
        raise Http404()

    return FileResponse(tpl.file.open("rb"), as_attachment=True, filename=tpl.file.name.split("/")[-1])


@login_required
def upload_coauthor_consent(request, process_pk: int, coauthor_pk: int):
    process = get_object_or_404(Process, pk=process_pk, author=request.user)
    coauthor = get_object_or_404(CoAuthor, pk=coauthor_pk, process=process)

    if process.status != Process.Status.WAITING_COAUTHOR_CONSENTS:
        messages.warning(request, "Сейчас этап согласий соавторов не активен для этой заявки.")
        return redirect("publications:process_detail", pk=process.pk)

    if request.method == "POST":
        form = UploadConsentForm(request.POST, request.FILES, instance=coauthor)
        if form.is_valid():
            form.save()
            messages.success(request, "Согласие загружено.")
            try_advance_after_coauthor_consents(process)
            return redirect("publications:process_detail", pk=process.pk)
    else:
        form = UploadConsentForm(instance=coauthor)

    return render(request, "publications/upload_consent.html", {"process": process, "coauthor": coauthor, "form": form})


@role_required(User.Role.LIBRARY_HEAD)
def library_tasks(request):
    processes = Process.objects.filter(status=Process.Status.LIBRARY_REVIEW).order_by("created_at")
    return render(request, "publications/library_tasks.html", {"processes": processes})


@role_required(User.Role.LIBRARY_HEAD)
def library_decide(request, pk: int):
    process = get_object_or_404(Process, pk=pk)

    if process.status != Process.Status.LIBRARY_REVIEW:
        messages.warning(request, "Эта заявка сейчас не на этапе библиотеки.")
        return redirect("publications:library_tasks")

    ld = getattr(process, "library_decision", None)
    if request.method == "POST":
        form = LibraryDecisionForm(request.POST, instance=ld)
        if form.is_valid():
            obj = form.save(commit=False)
            # interpret decision
            approved = obj.decision == obj.Decision.APPROVED
            rejected = obj.decision == obj.Decision.REJECTED

            if not (approved or rejected):
                messages.warning(request, "Выберите 'Согласовано' или 'Отклонено'.")
                return redirect("publications:library_decide", pk=process.pk)

            library_apply_decision(process, approved=approved, comment=obj.comment, librarian=request.user)
            messages.success(request, "Решение сохранено.")
            return redirect("publications:library_tasks")
    else:
        form = LibraryDecisionForm(instance=ld)

    return render(request, "publications/process_detail.html", {"process": process, "library_form": form})


@role_required(User.Role.REVIEWER)
def reviewer_tasks(request):
    assignments = ReviewerAssignment.objects.filter(reviewer=request.user).order_by("-process__created_at")
    return render(request, "publications/reviewer_tasks.html", {"assignments": assignments})


@role_required(User.Role.REVIEWER)
def reviewer_submit_view(request, assignment_pk: int):
    assignment = get_object_or_404(ReviewerAssignment, pk=assignment_pk, reviewer=request.user)
    process = assignment.process

    if process.status != Process.Status.INTERNAL_REVIEW:
        messages.warning(request, "Эта заявка сейчас не на этапе активного рецензирования.")
        return redirect("publications:reviewer_tasks")

    if request.method == "POST":
        form = ReviewerVerdictForm(request.POST, instance=assignment)
        if form.is_valid():
            a = form.save(commit=False)
            if a.verdict == a.Verdict.PENDING:
                messages.warning(request, "Выберите итоговый вердикт.")
                return redirect("publications:reviewer_submit", assignment_pk=assignment.pk)
            reviewer_submit(assignment, verdict=a.verdict, comment=a.comment)
            messages.success(request, "Рецензия отправлена.")
            return redirect("publications:reviewer_tasks")
    else:
        form = ReviewerVerdictForm(instance=assignment)

    return render(request, "publications/process_detail.html", {"process": process, "reviewer_form": form, "assignment": assignment})


@role_required(User.Role.OEK)
def oek_tasks(request):
    processes = Process.objects.filter(status=Process.Status.OEK_REVIEW).order_by("created_at")
    return render(request, "publications/oek_tasks.html", {"processes": processes})


@role_required(User.Role.OEK)
def oek_decide_view(request, pk: int):
    process = get_object_or_404(Process, pk=pk)

    if process.status != Process.Status.OEK_REVIEW:
        messages.warning(request, "Эта заявка сейчас не на этапе ОЭК.")
        return redirect("publications:oek_tasks")

    od = getattr(process, "oek_decision", None)

    if request.method == "POST":
        form = OEKDecisionForm(request.POST, instance=od)
        if form.is_valid():
            obj = form.save(commit=False)
            approved = obj.decision == obj.Decision.APPROVED
            rejected = obj.decision == obj.Decision.REJECTED
            if not (approved or rejected):
                messages.warning(request, "Выберите 'Согласовано' или 'Отклонено'.")
                return redirect("publications:oek_decide", pk=process.pk)

            defense_datetime = form.cleaned_data.get("defense_datetime")
            defense_room = form.cleaned_data.get("defense_room", "")

            oek_apply_decision(
                process,
                approved=approved,
                comment=obj.comment,
                oek_user=request.user,
                defense_datetime=defense_datetime,
                defense_room=defense_room,
            )
            messages.success(request, "Решение ОЭК сохранено.")
            return redirect("publications:oek_tasks")
    else:
        form = OEKDecisionForm(instance=od, initial={
            "defense_room": process.defense_room,
        })

    return render(request, "publications/process_detail.html", {"process": process, "oek_form": form})