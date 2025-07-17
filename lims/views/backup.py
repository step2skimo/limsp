from django.core import management
from django.http import HttpResponse
import io

def backup_db(request):
    # Allow only authenticated superusers
    if request.user.is_authenticated and request.user.is_superuser:
        # Create in-memory stream
        out = io.StringIO()
        # Dump all data
        
        management.call_command( 'dumpdata',
    '--exclude', 'notifications',
    '--exclude', 'auth.permission',
    '--exclude', 'contenttypes',
    indent=2,
    stdout=out)
       

        # Prepare response for download
        response = HttpResponse(out.getvalue(), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename=db_backup.json'
        return response
    
    return HttpResponse("Unauthorized", status=401)
