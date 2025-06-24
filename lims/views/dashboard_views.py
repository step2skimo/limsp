from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from users.models import User

@login_required
def dashboard_redirect(request):
    user = request.user
    if user.is_manager():
        return redirect("manager_dashboard")
    elif user.is_analyst():
        return redirect("analyst_dashboard")
    elif user.is_clerk():
        return redirect("clerk_dashboard")  
    else:
        return redirect("login")  

