from django.urls import path
from . import views
from django.shortcuts import redirect
from lims.views.dashboard_views import dashboard_redirect
from .views.manager import *
from .views.reports import *
from .views.analyst import *
from .views.reports import analyst_productivity_view
from .views.clerk_views import clerk_dashboard_view
from lims.views.client import enter_token_view
from lims.views.sample_confirm import intake_confirmation_view
from .views.assign_test import *
from django.contrib.auth.views import LogoutView
from lims.views.ai_views import ask_lab_ai
from lims.views.coa import *
from lims.views.charts import *
from lims.views.test_email import test_email
from lims.views.reagent import *

urlpatterns = [

     path("", views.landing_view, name="home"),
     
     path('logout/', LogoutView.as_view(next_page='login'), name='logout'),

     path("dashboard/", dashboard_redirect, name="dashboard"),
     path('analyst/results/history/', views.result_history_view, name='result_history'),
     path('analyst/test/begin/<int:result_id>/', views.begin_test_view, name='begin_test'),
     path("reports/productivity/", analyst_productivity_view, name="analyst_productivity"),
     path("coa/release/client/<int:client_id>/", views.release_client_coa, name="release_client_coa"),

     
    path("test-email/", test_email, name="test_email"),

     
     path("client/token-entry/", enter_token_view, name="enter_token"),
     path("clerk/dashboard/", views.clerk_dashboard_view, name="clerk_dashboard"),
     path("clients/", views.view_all_clients, name="view_all_clients"),
     path("samples/", views.sample_list, name="sample_list"),
     path("samples/search/", views.search_sample_by_code, name="search_sample_by_code"),
     path("samples/status-stats/", views.sample_status_stats, name="sample_stats"),
     path("clerk/summary/", views.clerk_activity_summary, name="clerk_activity_summary"),
     path("intake/", views.sample_intake_view, name="sample_intake"),
     





    path("manager/assign-overview/", assign_overview_all_clients, name="assign_overview_all_clients"),

    path('manager/export-assignments/csv/<str:client_id>/', views.export_assignments_csv, name='export_parameter_assignments_csv'),
    path('manager/export-assignments/pdf/<str:client_id>/', views.export_assignments_pdf, name='export_parameter_assignments_pdf'),

    path('result-success/<int:assignment_id>/', views.result_success, name='result_success'),

    path('intake/confirmation/<str:client_id>/', views.intake_confirmation_view, name='intake_confirmation'),


    path("manager/reports/pdf/", export_report_pdf, name="export_report_pdf"),
    path("manager/reports/excel/", export_report_excel, name="export_report_excel"),
    path("coa/<str:client_id>/", views.generate_coa_pdf, name="generate_coa_pdf"),

    path('coa_dashboard/', views.coa_dashboard, name='coa_dashboard'),
    path('preview_coa/<str:client_id>/', views.preview_coa, name='preview_coa'),
    path('generate_coa/<str:client_id>/', views.generate_coa_pdf, name='generate_coa'),
    path('release_coa/<int:client_id>/', views.release_client_coa, name='release_client_coa'),

    # Manager review
    path('manager/results/review/<int:sample_id>/', views.result_review_view, name='result_review_view'),
    path('manager/results/review_panel/', views.review_panel_grouped_by_client, name='review_panel_grouped_by_client'),
   


    path("manager/reports/", manager_report_view, name="manager_report"),



    path('analyst/dashboard/', views.analyst_dashboard_view, name='analyst_dashboard'),
    path("portal/<str:token>/", views.client_tracking_view, name="client_tracking"),


    path('receipt/download/<int:client_id>/', views.intake_pdf_download, name='intake_receipt_pdf'),
    path('analyst/result/<int:assignment_id>/submit/', views.enter_result_view, name='enter_result'),
   

    path("api/sample_status/", views.sample_status_json, name="sample_status_json"),
    path("api/autocomplete_samples/", views.autocomplete_sample_codes, name="autocomplete_sample_codes"),
   


    path("ai/ask/", ask_lab_ai, name="ask_lab_ai"),

    path("coa_dashboard/", views.coa_dashboard, name="coa_dashboard"),
    path("preview_coa/<str:client_id>/", views.preview_coa, name="preview_coa"),
    path("generate_coa/<str:client_id>/", views.generate_coa_pdf, name="generate_coa"),

    
    path("generate_coa/<str:client_id>/", views.generate_coa_pdf, name="generate_coa"),

    path("qc-chart-data/", qc_metrics_chart_data, name="qc_metrics_chart_data"),
    path("qc-dashboard/", qc_dashboard, name="qc_dashboard"),












    path("manager/dashboard/", views.manager_dashboard, name="manager_dashboard"),
    
  
    path("manager/qc/charts/", views.qc_overview_all_parameters, name="qc_overview_all_parameters"),
    path("analyst/qc/charts/", views.analyst_qc_dashboard, name="analyst_qc_dashboard"),
    path("manager/test-assignments/", views.test_assignment_list, name="test_assignment_list"),
    path('manager/assign-by-parameter/<str:client_id>/<int:parameter_id>/', views.assign_parameter_tests, name='assign_parameter_tests'),
    path('manager/review/grouped/', review_panel_grouped_by_client, name='review_panel_grouped_by_client'),
    path('clients/<int:client_id>/samples/', views.view_client_samples, name='view_client_samples'),





    # Form + Success
    path('reagent-usage/log/', log_reagent_usage, name='reagent-usage-log'),
    path('reagent-usage/success/', reagent_usage_success, name='reagent-usage-success'),

    # Manager dashboard
    path('reagent-usage/dashboard/', manager_reagent_dashboard, name='reagent-dashboard'),

    # Alerts
    path('reagent-usage/alerts/', reagent_alerts, name='reagent-alerts'),

    # Usage history
    path('reagent-usage/history/', usage_history, name='reagent-usage-history'),

    # CSV Export
    path('reagent-usage/export/', export_csv, name='export-csv'),
    path('reagent-usage/analyst/', analyst_dashboard, name='analyst-dashboard'),





    path("equipment/<int:equipment_id>/usage/", views.equipment_usage_view, name="equipment_usage"),








]










