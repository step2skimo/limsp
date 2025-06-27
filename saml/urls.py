from django.urls import path
from . import views

urlpatterns = [
    path('saml/login/', views.saml_login, name='saml_login'),
    path('saml/acs/', views.saml_acs, name='saml_acs'),
    path('saml/metadata/', views.saml_metadata, name='saml_metadata'),
]
