"""
Django Admin configuration for Dr. Violet's Catalog back-office:
Manage Courses, Local/International Prices, and Cohorts from one unified view.
"""
from django.contrib import admin

from .models import Cohort, Course, Price


class PriceInline(admin.TabularInline):
    model = Price
    extra = 2
    max_num = 2
    fields = ("audience", "currency", "amount_minor")


class CohortInline(admin.TabularInline):
    model = Cohort
    extra = 1
    fields = ("name", "starts_on", "capacity", "enrollment_open")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "level", "residency", "status", "updated_at")
    list_filter = ("level", "residency", "status")
    search_fields = ("title", "slug", "summary")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = (PriceInline, CohortInline)


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "starts_on", "capacity", "enrollment_open")
    list_filter = ("enrollment_open", "course__level", "starts_on")
    search_fields = ("name", "course__title")
    readonly_fields = ("id", "created_at", "updated_at")