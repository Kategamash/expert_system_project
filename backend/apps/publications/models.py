from django.conf import settings
from django.db import models
from django.utils import timezone


class Council(models.Model):
    department = models.CharField("Кафедра", max_length=255)
    council_number = models.CharField("Номер совета", max_length=64)
    members = models.TextField("Члены совета", blank=True)

    class Meta:
        unique_together = ("department", "council_number")
        ordering = ("department", "council_number")

    def __str__(self):
        return f"{self.department} / {self.council_number}"


class PublicationTemplate(models.Model):
    department = models.CharField("Кафедра", max_length=255)
    name = models.CharField("Название шаблона", max_length=255)
    file = models.FileField(upload_to="templates/")

    class Meta:
        ordering = ("department", "name")

    def __str__(self):
        return f"{self.department}: {self.name}"


class Process(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Черновик"
        WAITING_COAUTHOR_CONSENTS = "WAITING_COAUTHOR_CONSENTS", "Ожидаются согласия соавторов"
        LIBRARY_REVIEW = "LIBRARY_REVIEW", "Проверка библиотеки"
        LIBRARY_NEEDS_FIX = "LIBRARY_NEEDS_FIX", "Библиотека: требуется исправление"
        INTERNAL_REVIEW = "INTERNAL_REVIEW", "Внутреннее рецензирование"
        INTERNAL_REVIEW_NEEDS_FIX = "INTERNAL_REVIEW_NEEDS_FIX", "Рецензирование: требуется исправление"
        OEK_REVIEW = "OEK_REVIEW", "Проверка ОЭК"
        OEK_NEEDS_FIX = "OEK_NEEDS_FIX", "ОЭК: требуется исправление"
        READY_FOR_DEFENSE = "READY_FOR_DEFENSE", "Готово к очной защите"
        REJECTED = "REJECTED", "Отклонено"

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="processes")
    title = models.CharField("Название работы", max_length=400)
    journal = models.CharField("Журнал", max_length=255)
    council = models.ForeignKey(Council, on_delete=models.PROTECT, related_name="processes")
    is_mifi = models.BooleanField("Публикация в рамках МИФИ", default=False)

    status = models.CharField(max_length=64, choices=Status.choices, default=Status.DRAFT)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    defense_datetime = models.DateTimeField("Время защиты", null=True, blank=True)
    defense_room = models.CharField("Аудитория/место защиты", max_length=128, blank=True)

    def __str__(self):
        return f"#{self.pk} {self.title} ({self.get_status_display()})"


class CoAuthor(models.Model):
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name="coauthors")
    name = models.CharField("ФИО соавтора", max_length=255)
    email = models.EmailField("Email соавтора", blank=True)
    consent_file = models.FileField("Согласие соавтора (скан)", upload_to="coauthor_consents/", blank=True, null=True)

    def __str__(self):
        return f"{self.name} (process={self.process_id})"


class ProcessDocuments(models.Model):
    process = models.OneToOneField(Process, on_delete=models.CASCADE, related_name="documents")

    article_file = models.FileField("Файл статьи/тезисов", upload_to="articles/")
    bibliography_file = models.FileField("Список литературы", upload_to="bibliography/")
    filled_template_file = models.FileField("Заполненный шаблон", upload_to="filled_templates/")

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Documents(process={self.process_id})"


class LibraryDecision(models.Model):
    class Decision(models.TextChoices):
        PENDING = "PENDING", "Ожидает"
        APPROVED = "APPROVED", "Согласовано"
        REJECTED = "REJECTED", "Отклонено"

    process = models.OneToOneField(Process, on_delete=models.CASCADE, related_name="library_decision")
    librarian = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    decision = models.CharField(max_length=16, choices=Decision.choices, default=Decision.PENDING)
    comment = models.TextField("Комментарий", blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"LibraryDecision(process={self.process_id}, {self.decision})"


class ReviewerAssignment(models.Model):
    class Verdict(models.TextChoices):
        PENDING = "PENDING", "Ожидает"
        RECOMMEND = "RECOMMEND", "Рекомендовать"
        RECOMMEND_AFTER_FIX = "RECOMMEND_AFTER_FIX", "Рекомендовать после исправлений"
        NOT_RECOMMEND = "NOT_RECOMMEND", "Не рекомендовать"

    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name="review_assignments")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="review_tasks")
    verdict = models.CharField(max_length=32, choices=Verdict.choices, default=Verdict.PENDING)
    comment = models.TextField("Комментарий", blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("process", "reviewer")

    def __str__(self):
        return f"Assignment(process={self.process_id}, reviewer={self.reviewer_id}, {self.verdict})"


class OEKDecision(models.Model):
    class Decision(models.TextChoices):
        PENDING = "PENDING", "Ожидает"
        APPROVED = "APPROVED", "Согласовано"
        REJECTED = "REJECTED", "Отклонено"

    process = models.OneToOneField(Process, on_delete=models.CASCADE, related_name="oek_decision")
    oek_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    decision = models.CharField(max_length=16, choices=Decision.choices, default=Decision.PENDING)
    comment = models.TextField("Комментарий", blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"OEKDecision(process={self.process_id}, {self.decision})"