"""URL routes for the public catalog app."""
from django.urls import path

from .views import CourseDetailView, CourseListView

app_name = "catalog"

urlpatterns = [
    path("courses/", CourseListView.as_view(), name="course-list"),
    path("courses/<slug:slug>/", CourseDetailView.as_view(), name="course-detail"),
]