from django.urls import path
from .views import (
    dashboard,
    process_list, process_create, process_detail,
    template_download,
    upload_coauthor_consent,
    library_tasks, library_decide,
    reviewer_tasks, reviewer_submit_view,
    oek_tasks, oek_decide_view,
)

app_name = "publications"

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("processes/", process_list, name="process_list"),
    path("process/create/", process_create, name="process_create"),
    path("process/<int:pk>/", process_detail, name="process_detail"),

    path("template/<int:pk>/download/", template_download, name="template_download"),

    path("process/<int:process_pk>/coauthor/<int:coauthor_pk>/consent/", upload_coauthor_consent, name="upload_consent"),

    path("tasks/library/", library_tasks, name="library_tasks"),
    path("tasks/library/<int:pk>/decide/", library_decide, name="library_decide"),

    path("tasks/reviewer/", reviewer_tasks, name="reviewer_tasks"),
    path("tasks/reviewer/<int:assignment_pk>/submit/", reviewer_submit_view, name="reviewer_submit"),

    path("tasks/oek/", oek_tasks, name="oek_tasks"),
    path("tasks/oek/<int:pk>/decide/", oek_decide_view, name="oek_decide"),
]