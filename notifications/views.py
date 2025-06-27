from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Notification
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.http import JsonResponse

@login_required
def unread_count(request):
    count = request.user.notifications.filter(read=False).count()
    return JsonResponse({'unread': count})


@login_required
def notification_list(request):
    notifications = request.user.notifications.order_by('-created_at')

    # Optional: mark all as read on visit
    notifications.filter(read=False).update(read=True)

    return render(request, 'notifications/list.html', {'notifications': notifications})

@login_required
def mark_all_read(request):
    request.user.notifications.filter(read=False).update(read=True)
    return HttpResponseRedirect(reverse('notifications:list'))


@login_required
def notification_detail(request, pk):
    note = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not note.read:
        note.read = True
        note.save()
    return render(request, 'notifications/detail.html', {'note': note})
