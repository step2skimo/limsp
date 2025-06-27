from onelogin.saml2.settings import OneLogin_Saml2_Settings

def prepare_django_request(request):
    return {
        'http_host': request.get_host(),
        'script_name': request.path,
        'get_data': request.GET.copy(),
        'post_data': request.POST.copy(),
        'https': 'on' if request.is_secure() else 'off',
    }

def get_saml_settings():
    return OneLogin_Saml2_Settings(custom_base_path='saml/saml', sp_validation_only=True)
