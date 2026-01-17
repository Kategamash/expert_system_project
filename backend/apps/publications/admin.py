from django.contrib import admin
from .models import (
    Council, PublicationTemplate,
    Process, CoAuthor, ProcessDocuments,
    LibraryDecision, ReviewerAssignment, OEKDecision
)


@admin.register(Council)
class CouncilAdmin(admin.ModelAdmin):
    list_display = ("department", "council_number")
    search_fields = ("department", "council_number", "members")


@admin.register(PublicationTemplate)
class PublicationTemplateAdmin(admin.ModelAdmin):
    list_display = ("department", "name", "file")
    search_fields = ("department", "name")


class CoAuthorInline(admin.TabularInline):
    model = CoAuthor
    extra = 0


class DocumentsInline(admin.StackedInline):
    model = ProcessDocuments
    extra = 0


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "author", "status", "is_mifi", "created_at", "updated_at")
    list_filter = ("status", "is_mifi", "council")
    search_fields = ("title", "journal", "author__username", "author__fio")
    inlines = [CoAuthorInline, DocumentsInline]


@admin.register(LibraryDecision)
class LibraryDecisionAdmin(admin.ModelAdmin):
    list_display = ("process", "decision", "librarian", "decided_at")


@admin.register(ReviewerAssignment)
class ReviewerAssignmentAdmin(admin.ModelAdmin):
    list_display = ("process", "reviewer", "verdict", "decided_at")
    list_filter = ("verdict",)


@admin.register(OEKDecision)
class OEKDecisionAdmin(admin.ModelAdmin):
    list_display = ("process", "decision", "oek_user", "decided_at")