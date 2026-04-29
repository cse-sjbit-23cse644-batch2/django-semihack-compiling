from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('profile/', views.my_profile, name='my_profile'),
    path('cgpa-planner/', views.cgpa_planner, name='cgpa_planner'),
    path('dna-profile/', views.dna_profile, name='dna_profile'),
    path('backlog-risk/', views.backlog_risk, name='backlog_risk'),
    path('emotional-health/', views.emotional_health, name='emotional_health'),
    path('emotional-health/chat/', views.emotional_chat, name='emotional_chat'),
    path('emotional-health/chat/export.pdf', views.emotional_chat_pdf, name='emotional_chat_pdf'),
    path('performance/', views.performance, name='performance'),
    path('reports/', views.reports, name='reports'),
    path('settings/', views.settings_page, name='settings_page'),
    path('upload/', views.upload_csv, name='upload_csv'),
    path('upload/confirm/', views.confirm_csv_upload, name='confirm_csv_upload'),
    path('download-report/', views.download_report, name='download_report'),
]
