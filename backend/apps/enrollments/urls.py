"""URL routes for the student enrollments app."""
from django.urls import path

from .views import EnrollmentDetailView, EnrollmentListCreateView

app_name = "enrollments"

urlpatterns = [
    path("", EnrollmentListCreateView.as_view(), name="enrollment-list-create"),
    path("<uuid:pk>/", EnrollmentDetailView.as_view(), name="enrollment-detail"),
]