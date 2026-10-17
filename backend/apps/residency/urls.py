"""URL routes for the Nairobi & Embu 5-day practical residency app."""
from django.urls import path

from .views import ResidencyBlockListView, ResidencyRegistrationListCreateView

app_name = "residency"

urlpatterns = [
    path("blocks/", ResidencyBlockListView.as_view(), name="block-list"),
    path(
        "registrations/",
        ResidencyRegistrationListCreateView.as_view(),
        name="registration-list-create",
    ),
]