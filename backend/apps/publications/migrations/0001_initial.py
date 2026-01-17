from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Council",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("department", models.CharField(max_length=255, verbose_name="Кафедра")),
                ("council_number", models.CharField(max_length=64, verbose_name="Номер совета")),
                ("members", models.TextField(blank=True, verbose_name="Члены совета")),
            ],
            options={
                "ordering": ("department", "council_number"),
                "unique_together": {("department", "council_number")},
            },
        ),
        migrations.CreateModel(
            name="PublicationTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("department", models.CharField(max_length=255, verbose_name="Кафедра")),
                ("name", models.CharField(max_length=255, verbose_name="Название шаблона")),
                ("file", models.FileField(upload_to="templates/")),
            ],
            options={
                "ordering": ("department", "name"),
            },
        ),
        migrations.CreateModel(
            name="Process",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=400, verbose_name="Название работы")),
                ("journal", models.CharField(max_length=255, verbose_name="Журнал")),
                ("is_mifi", models.BooleanField(default=False, verbose_name="Публикация в рамках МИФИ")),
                ("status", models.CharField(choices=[
                    ("DRAFT", "Черновик"),
                    ("WAITING_COAUTHOR_CONSENTS", "Ожидаются согласия соавторов"),
                    ("LIBRARY_REVIEW", "Проверка библиотеки"),
                    ("LIBRARY_NEEDS_FIX", "Библиотека: требуется исправление"),
                    ("INTERNAL_REVIEW", "Внутреннее рецензирование"),
                    ("INTERNAL_REVIEW_NEEDS_FIX", "Рецензирование: требуется исправление"),
                    ("OEK_REVIEW", "Проверка ОЭК"),
                    ("OEK_NEEDS_FIX", "ОЭК: требуется исправление"),
                    ("READY_FOR_DEFENSE", "Готово к очной защите"),
                    ("REJECTED", "Отклонено"),
                ], default="DRAFT", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("defense_datetime", models.DateTimeField(blank=True, null=True, verbose_name="Время защиты")),
                ("defense_room", models.CharField(blank=True, max_length=128, verbose_name="Аудитория/место защиты")),
                ("author", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="processes", to=settings.AUTH_USER_MODEL)),
                ("council", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="processes", to="publications.council")),
            ],
        ),
        migrations.CreateModel(
            name="ProcessDocuments",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("article_file", models.FileField(upload_to="articles/", verbose_name="Файл статьи/тезисов")),
                ("bibliography_file", models.FileField(upload_to="bibliography/", verbose_name="Список литературы")),
                ("filled_template_file", models.FileField(upload_to="filled_templates/", verbose_name="Заполненный шаблон")),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("process", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="documents", to="publications.process")),
            ],
        ),
        migrations.CreateModel(
            name="CoAuthor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255, verbose_name="ФИО соавтора")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="Email соавтора")),
                ("consent_file", models.FileField(blank=True, null=True, upload_to="coauthor_consents/", verbose_name="Согласие соавтора (скан)")),
                ("process", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="coauthors", to="publications.process")),
            ],
        ),
        migrations.CreateModel(
            name="LibraryDecision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("decision", models.CharField(choices=[
                    ("PENDING", "Ожидает"),
                    ("APPROVED", "Согласовано"),
                    ("REJECTED", "Отклонено"),
                ], default="PENDING", max_length=16)),
                ("comment", models.TextField(blank=True, verbose_name="Комментарий")),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                ("librarian", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("process", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="library_decision", to="publications.process")),
            ],
        ),
        migrations.CreateModel(
            name="OEKDecision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("decision", models.CharField(choices=[
                    ("PENDING", "Ожидает"),
                    ("APPROVED", "Согласовано"),
                    ("REJECTED", "Отклонено"),
                ], default="PENDING", max_length=16)),
                ("comment", models.TextField(blank=True, verbose_name="Комментарий")),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                ("oek_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("process", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="oek_decision", to="publications.process")),
            ],
        ),
        migrations.CreateModel(
            name="ReviewerAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("verdict", models.CharField(choices=[
                    ("PENDING", "Ожидает"),
                    ("RECOMMEND", "Рекомендовать"),
                    ("RECOMMEND_AFTER_FIX", "Рекомендовать после исправлений"),
                    ("NOT_RECOMMEND", "Не рекомендовать"),
                ], default="PENDING", max_length=32)),
                ("comment", models.TextField(blank=True, verbose_name="Комментарий")),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                ("process", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="review_assignments", to="publications.process")),
                ("reviewer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="review_tasks", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "unique_together": {("process", "reviewer")},
            },
        ),
    ]