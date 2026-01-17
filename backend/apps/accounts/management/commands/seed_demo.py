from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from apps.publications.models import Council, PublicationTemplate, Process, CoAuthor, ProcessDocuments
from django.core.files.base import ContentFile


User = get_user_model()


class Command(BaseCommand):
    help = "Создаёт тестовые данные (пользователи/шаблоны/пример заявок). Идемпотентно."

    def handle(self, *args, **kwargs):
        # superuser
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(username="admin", password="admin12345", email="admin@example.com")
            self.stdout.write(self.style.SUCCESS("Created superuser admin/admin12345"))

        # roles
        users = [
            ("author1", "AUTHOR", "Иванов Иван Иванович"),
            ("oek1", "OEK", "Петров Пётр Петрович"),
            ("lib1", "LIBRARY_HEAD", "Сидорова Мария Сергеевна"),
            ("rev1", "REVIEWER", "Рецензент 1"),
            ("rev2", "REVIEWER", "Рецензент 2"),
            ("rev3", "REVIEWER", "Рецензент 3"),
            ("comm1", "COMMISSION", "Член комиссии 1"),
        ]
        for username, role, fio in users:
            if not User.objects.filter(username=username).exists():
                u = User.objects.create_user(
                    username=username,
                    password="Passw0rd!234",
                    role=role,
                    fio=fio,
                    department="Кафедра №1",
                    position="Сотрудник",
                )
                self.stdout.write(self.style.SUCCESS(f"Created user {u.username} / Passw0rd!234"))

        # councils
        council, _ = Council.objects.get_or_create(
            department="Кафедра №1",
            council_number="Совет-101",
            defaults={"members": "Иванов И.И.; Петров П.П.; Сидоров С.С."},
        )

        # publication template (a placeholder demo file)
        if not PublicationTemplate.objects.exists():
            tpl = PublicationTemplate(department="Кафедра №1", name="Шаблон оформления (DEMO)")
            tpl.file.save("template_demo.txt", ContentFile("DEMO TEMPLATE FILE. Replace with your real docx."), save=True)
            self.stdout.write(self.style.SUCCESS("Created demo publication template"))

        author = User.objects.get(username="author1")

        # process 1 (MIFI internal, with coauthor)
        if not Process.objects.filter(title="Демо-заявка (МИФИ)").exists():
            p1 = Process.objects.create(
                author=author,
                title="Демо-заявка (МИФИ)",
                journal="Вестник МИФИ",
                council=council,
                is_mifi=True,
                status="LIBRARY_REVIEW",
            )
            CoAuthor.objects.create(process=p1, name="Соавтор 1", email="coauthor1@example.com")

            docs = ProcessDocuments(process=p1)
            docs.article_file.save("article_demo.txt", ContentFile("DEMO ARTICLE"), save=False)
            docs.bibliography_file.save("refs_demo.txt", ContentFile("DEMO REFS"), save=False)
            docs.filled_template_file.save("filled_template_demo.txt", ContentFile("DEMO FILLED TEMPLATE"), save=False)
            docs.save()

            self.stdout.write(self.style.SUCCESS("Created process: Демо-заявка (МИФИ)"))

        # process 2 (external, no internal review)
        if not Process.objects.filter(title="Демо-заявка (внешний журнал)").exists():
            p2 = Process.objects.create(
                author=author,
                title="Демо-заявка (внешний журнал)",
                journal="Elsevier Journal",
                council=council,
                is_mifi=False,
                status="LIBRARY_REVIEW",
            )
            docs = ProcessDocuments(process=p2)
            docs.article_file.save("article_demo2.txt", ContentFile("DEMO ARTICLE 2"), save=False)
            docs.bibliography_file.save("refs_demo2.txt", ContentFile("DEMO REFS 2"), save=False)
            docs.filled_template_file.save("filled_template_demo2.txt", ContentFile("DEMO FILLED TEMPLATE 2"), save=False)
            docs.save()

            self.stdout.write(self.style.SUCCESS("Created process: Демо-заявка (внешний журнал)"))

        self.stdout.write(self.style.SUCCESS("Seeding done."))