from django.urls import path
from .views import notification_list, mark_read, mark_all_read, notification_detail

app_name = "notifications"

urlpatterns = [
    path("", notification_list, name="list"),
    path("<int:pk>/", notification_detail, name="detail"),  # ДОБАВИТЬ
    path("read/<int:pk>/", mark_read, name="read"),
    path("read-all/", mark_all_read, name="read_all"),
]