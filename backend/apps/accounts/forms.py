from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User


class RegisterForm(UserCreationForm):
    role = forms.ChoiceField(choices=User.Role.choices, label="Роль")
    fio = forms.CharField(label="ФИО", max_length=255)
    department = forms.CharField(label="Кафедра", max_length=255, required=False)
    position = forms.CharField(label="Должность", max_length=255, required=False)
    person_status = forms.ChoiceField(choices=User.PersonStatus.choices, label="Статус (студент/сотрудник)")
    email = forms.EmailField(label="Email", required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "fio", "department", "position", "person_status", "role")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data["role"]
        user.fio = self.cleaned_data["fio"]
        user.department = self.cleaned_data.get("department", "")
        user.position = self.cleaned_data.get("position", "")
        user.person_status = self.cleaned_data["person_status"]
        user.email = self.cleaned_data.get("email", "")
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Логин")
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput)


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("fio", "department", "position", "person_status", "email")
        labels = {
            "fio": "ФИО",
            "department": "Кафедра",
            "position": "Должность",
            "person_status": "Статус",
            "email": "Email",
        }