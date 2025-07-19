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
from lims.views.reagents import *
from .views.equipment import *
from .views.backup import backup_db

urlpatterns = [

    path("", views.landing_view, name="home"),
     
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('inventory-dashboard/', inventory_dashboard, name='inventory_dashboard'),
    path('reagents/', reagent_list, name='reagent_list'),
    path('reagents/<int:pk>/', reagent_detail, name='reagent_detail'),
    path('reagents/add/', add_reagent, name='add_reagent'),
    path('reagents/<int:pk>/upload-docs/', upload_documents, name='upload_documents'),
    path('reagents/use/', use_reagent, name='use_reagent'),
    path('reagents/download/pdf/<int:pk>/', download_reagent_pdf, name='download_reagent_pdf'),
    path('reagents/download/csv/', download_inventory_csv, name='download_inventory_csv'),
    path('reagent/preview/', preview_reagent_request, name='preview_reagent_request'),
    path('reagent/send/', send_reagent_request, name='send_reagent_request'),
    path('reagent/issues/', reagent_issue_list, name='reagent_issue_list'),

    path('send-report/', send_manager_report, name='send_manager_report'),
    path("expenses/new/", expense_create, name="expense_create"),



   
    # Equipment Dashboard
    path('equipment-dashboard/', equipment_dashboard, name='equipment_dashboard'),

    # Equipment CRUD
    path('equipment/add/', add_equipment, name='add_equipment'),
    path('equipment/<int:pk>/', equipment_detail, name='equipment_detail'),
    path('equipment/<int:pk>/edit/', edit_equipment, name='edit_equipment'),
    path('equipment/<int:pk>/delete/', delete_equipment, name='delete_equipment'),

    # Calibration CRUD
    path('equipment/<int:equipment_id>/add-calibration/', add_calibration, name='add_calibration'),

    # Export Features
    path('equipment/export/csv/', export_equipment_csv, name='export_equipment_csv'),
    path('equipment/export/pdf/', export_equipment_pdf, name='export_equipment_pdf'),





  #backup
    path('backup/', backup_db, name='backup'),




    path('audit/', inventory_audit, name='inventory_audit'),
    path('consumption/', consumption_report, name='consumption_report'),
    path('expiry/', expiry_report, name='expiry_report'),
    path('suppliers/', supplier_evaluation, name='supplier_evaluation'),
    path('consumption/csv/', export_consumption_csv, name='export_consumption_csv'),
    path('consumption/pdf/', export_consumption_pdf, name='export_consumption_pdf'),
    path('sds/', safety_data_sheets, name='safety_data_sheets'),
    path('coa/', certificate_analysis, name='certificate_analysis'),
    path('reagent/request/', request_reagent, name='request_reagent'),
    path('reagent/report-issue/', report_issue, name='report_issue'),



     path("dashboard/", dashboard_redirect, name="dashboard"),
     path('analyst/results/history/', views.result_history_view, name='result_history'),
    
     path("reports/productivity/", analyst_productivity_view, name="analyst_productivity"),
     path("coa/release/client/<int:client_id>/", views.release_client_coa, name="release_client_coa"),


    path('results/batch/<str:client_id>/<int:parameter_id>/', views.enter_batch_result, name='enter_batch_result'),

    path("test-email/", test_email, name="test_email"),
   
    path('reagents/download/csv/', download_inventory_csv, name='download_csv'),
    path('reagents/<int:pk>/download/pdf/', download_reagent_pdf, name='download_pdf'),


    

     
     path("client/token-entry/", enter_token_view, name="enter_token"),
     path("clerk/dashboard/", views.clerk_dashboard_view, name="clerk_dashboard"),
     path("clients/", views.view_all_clients, name="view_all_clients"),
     path("samples/", views.sample_list, name="sample_list"),
     path("samples/search/", views.search_sample_by_code, name="search_sample_by_code"),
     path("samples/status-stats/", views.sample_status_stats, name="sample_stats"),
     path("clerk/summary/", views.clerk_activity_summary, name="clerk_activity_summary"),
     path("intake/", views.sample_intake_view, name="sample_intake"),
     path('update-client-field/', views.update_client_field, name='update_client_field'),
     path("edit-summary/<str:client_id>/", views.edit_summary, name="edit_summary"),

     

    path('manager/assign-by-parameter-overview/<str:client_id>/', views.assign_by_parameter_overview, name="assign_by_parameter_overview"),




    path("manager/assign-overview/", assign_overview_all_clients, name="assign_overview_all_clients"),
    path("analyst/begin-analysis/<str:client_id>/<int:parameter_id>/", views.begin_parameter_analysis, name="begin_parameter_analysis"),


    path('manager/export-assignments/csv/<str:client_id>/', views.export_assignments_csv, name='export_parameter_assignments_csv'),
    path('manager/export-assignments/pdf/<str:client_id>/', views.export_assignments_pdf, name='export_parameter_assignments_pdf'),

   

    path('intake/confirmation/<str:client_id>/', views.intake_confirmation_view, name='intake_confirmation'),


    path("manager/reports/pdf/", export_report_pdf, name="export_report_pdf"),
    path("manager/reports/excel/", export_report_excel, name="export_report_excel"),
    path("coa/<str:client_id>/", views.generate_coa_pdf, name="generate_coa_pdf"),

    path(
        "results/batch/<str:client_id>/<int:parameter_id>/success/",
        views.batch_result_success,
        name="result_success_batch"
    ),
  
    path("manager/review/<int:parameter_id>/", views.review_by_parameter, name="review_by_parameter"),
    
    path("manager/review/", views.parameter_review_list, name="parameter_review_list"),





    path('coa_dashboard/', views.coa_dashboard, name='coa_dashboard'),
    path('preview_coa/<str:client_id>/', views.preview_coa, name='preview_coa'),
    path('generate_coa/<str:client_id>/', views.generate_coa_pdf, name='generate_coa'),
    path('release_coa/<int:client_id>/', views.release_client_coa, name='release_client_coa'),

    # Manager review
    # path('manager/results/review/<int:sample_id>/', views.result_review_view, name='result_review_view'),
    # path('manager/results/review_panel/', views.review_panel_grouped_by_client, name='review_panel_grouped_by_client'),
   


    path("manager/reports/", manager_report_view, name="manager_report"),



    path('analyst/dashboard/', views.analyst_dashboard_view, name='analyst_dashboard'),
    path("portal/<str:token>/", views.client_tracking_view, name="client_tracking"),


    path('receipt/download/<int:client_id>/', views.intake_pdf_download, name='intake_receipt_pdf'),
   # path('analyst/result/<int:assignment_id>/submit/', views.enter_result_view, name='enter_result'),
   

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
  #  path('manager/review/grouped/', review_panel_grouped_by_client, name='review_panel_grouped_by_client'),
    path('clients/<int:client_id>/samples/', views.view_client_samples, name='view_client_samples'),






    path("equipment/<int:equipment_id>/usage/", views.equipment_usage_view, name="equipment_usage"),








]










