from django import forms
from django.forms import modelformset_factory
from .models import Process, CoAuthor, ProcessDocuments, LibraryDecision, ReviewerAssignment, OEKDecision


class ProcessCreateForm(forms.ModelForm):
    class Meta:
        model = Process
        fields = ("title", "journal", "council", "is_mifi")
        labels = {
            "title": "Название работы",
            "journal": "Журнал",
            "council": "Номер совета",
            "is_mifi": "Публикация в рамках МИФИ (нужно внутреннее рецензирование)",
        }


class DocumentsForm(forms.ModelForm):
    class Meta:
        model = ProcessDocuments
        fields = ("article_file", "bibliography_file", "filled_template_file")
        labels = {
            "article_file": "Файл статьи/тезисов",
            "bibliography_file": "Список литературы (отдельный файл)",
            "filled_template_file": "Заполненный шаблон",
        }


class CoAuthorForm(forms.ModelForm):
    class Meta:
        model = CoAuthor
        fields = ("name", "email")
        labels = {"name": "ФИО соавтора", "email": "Email соавтора"}


CoAuthorFormSet = modelformset_factory(
    CoAuthor,
    form=CoAuthorForm,
    extra=1,
    can_delete=True,
)


class UploadConsentForm(forms.ModelForm):
    class Meta:
        model = CoAuthor
        fields = ("consent_file",)
        labels = {"consent_file": "Скан согласия соавтора"}


class LibraryDecisionForm(forms.ModelForm):
    class Meta:
        model = LibraryDecision
        fields = ("decision", "comment")
        labels = {"decision": "Решение", "comment": "Комментарий"}


class ReviewerVerdictForm(forms.ModelForm):
    class Meta:
        model = ReviewerAssignment
        fields = ("verdict", "comment")
        labels = {"verdict": "Вердикт", "comment": "Комментарий"}


class OEKDecisionForm(forms.ModelForm):
    defense_datetime = forms.DateTimeField(
        required=False,
        label="Назначить дату/время защиты (опционально)",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )
    defense_room = forms.CharField(required=False, label="Место защиты (опционально)")

    class Meta:
        model = OEKDecision
        fields = ("decision", "comment")
        labels = {"decision": "Решение", "comment": "Комментарий"}

class ReviewerReworkUploadForm(forms.ModelForm):
    class Meta:
        model = ProcessDocuments
        fields = ("article_file", "filled_template_file")
        labels = {
            "article_file": "Исправленный файл статьи/тезисов (если нужно)",
            "filled_template_file": "Исправленный заполненный шаблон (если нужно)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["article_file"].required = False
        self.fields["filled_template_file"].required = False

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("article_file") and not cleaned.get("filled_template_file"):
            raise forms.ValidationError("Загрузите хотя бы один исправленный файл.")
        return cleaned


class BibliographyReworkUploadForm(forms.ModelForm):
    class Meta:
        model = ProcessDocuments
        fields = ("bibliography_file",)
        labels = {"bibliography_file": "Исправленный список литературы"}