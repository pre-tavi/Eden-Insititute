"""
Django Admin back-office for Dr. Violet's Classroom management:
Order modules, publish/unpublish lessons, schedule live Google Meet lectures,
attach recorded lessons, and inspect student progress.
"""
from django.contrib import admin

from .models import Lesson, LessonProgress, LiveSession, Module


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ("order", "title", "kind", "duration_seconds", "video_asset_id", "is_published")


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order", "updated_at")
    list_filter = ("course",)
    search_fields = ("title", "course__title")
    inlines = (LessonInline,)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "order", "kind", "duration_seconds", "is_published")
    list_filter = ("kind", "is_published", "module__course")
    search_fields = ("title", "module__title", "video_asset_id")


@admin.register(LiveSession)
class LiveSessionAdmin(admin.ModelAdmin):
    list_display = ("title", "cohort", "starts_at", "duration_minutes", "recording_lesson")
    list_filter = ("cohort__course", "cohort")
    search_fields = ("title", "cohort__name")


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "status", "last_position_s", "completed_at", "updated_at")
    list_filter = ("status", "lesson__module__course")
    search_fields = ("user__email", "lesson__title")
    readonly_fields = ("id", "completed_at", "updated_at")