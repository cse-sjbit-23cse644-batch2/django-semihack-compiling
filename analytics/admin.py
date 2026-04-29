from django.contrib import admin
from .models import Student, Subject, ResultRecord, EmotionalProfile, WellnessChatMessage


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("student_id", "name", "department", "semester", "target_cgpa")
    search_fields = ("student_id", "name")


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "credits", "semester")


@admin.register(ResultRecord)
class ResultRecordAdmin(admin.ModelAdmin):
    list_display = ("student", "subject", "internal_marks", "external_marks",
                    "final_score", "pass_fail_status")
    list_filter = ("pass_fail_status",)


@admin.register(EmotionalProfile)
class EmotionalProfileAdmin(admin.ModelAdmin):
    list_display = ("student", "stress_level", "sleep_hours", "study_hours",
                    "motivation_score", "burnout_indicator", "date_logged")
    list_filter = ("burnout_indicator",)


@admin.register(WellnessChatMessage)
class WellnessChatMessageAdmin(admin.ModelAdmin):
    list_display = ("student_id", "role", "mood_label", "mood_score",
                    "created_at", "content_preview")
    list_filter = ("role", "mood_label")
    search_fields = ("student_id", "content")
    readonly_fields = ("created_at",)

    @admin.display(description="Content")
    def content_preview(self, obj):
        return obj.content[:80] + ("…" if len(obj.content) > 80 else "")
