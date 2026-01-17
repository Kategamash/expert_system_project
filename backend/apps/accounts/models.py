from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        AUTHOR = "AUTHOR", "Автор/Оформитель"
        OEK = "OEK", "Сотрудник ОЭК"
        REVIEWER = "REVIEWER", "Рецензент"
        LIBRARY_HEAD = "LIBRARY_HEAD", "Начальник отдела библиотеки"
        COMMISSION = "COMMISSION", "Член экспертной комиссии"

    class PersonStatus(models.TextChoices):
        STUDENT = "STUDENT", "Студент"
        STAFF = "STAFF", "Сотрудник"

    role = models.CharField(max_length=32, choices=Role.choices, default=Role.AUTHOR)
    fio = models.CharField("ФИО", max_length=255, blank=True)
    department = models.CharField("Кафедра", max_length=255, blank=True)
    position = models.CharField("Должность", max_length=255, blank=True)
    person_status = models.CharField("Статус", max_length=16, choices=PersonStatus.choices, default=PersonStatus.STAFF)

    def display_name(self):
        if self.fio:
            return self.fio
        full = f"{self.first_name} {self.last_name}".strip()
        return full or self.username

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"