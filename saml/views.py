from django.shortcuts import redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import login, get_user_model
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from .utils import prepare_django_request, get_saml_settings
from onelogin.saml2.metadata import OneLogin_Saml2_Metadata

def saml_login(request):
    auth = OneLogin_Saml2_Auth(prepare_django_request(request), custom_base_path='saml/saml')
    return HttpResponseRedirect(auth.login())

def saml_acs(request):
    auth = OneLogin_Saml2_Auth(prepare_django_request(request), custom_base_path='saml/saml')
    auth.process_response()
    errors = auth.get_errors()
    if not errors:
        email = auth.get_nameid()
        User = get_user_model()
        user, _ = User.objects.get_or_create(email=email)
        login(request, user)
        return redirect('dashboard')  
    return HttpResponse("SAML login failed: " + ", ".join(errors))


def saml_metadata(request):
    settings = get_saml_settings()
    metadata = OneLogin_Saml2_Metadata.builder(
        settings.get_sp_data(),
        settings.get_sp_cert(),
        settings.get_sp_key()
    )
    return HttpResponse(metadata, content_type='text/xml')
