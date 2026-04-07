# events/gallery_views.py
# =============================================
#  Multi-image gallery upload for events
# =============================================

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Event
from .models import EventGalleryImage



@login_required
def manage_gallery(request, event_pk):
    """Upload and manage gallery images for an event"""
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)

    if request.method == 'POST':
        images  = request.FILES.getlist('images')
        caption = request.POST.get('caption', '')

        if not images:
            messages.error(request, "Please select at least one image.")
            return redirect('manage_gallery', event_pk=event_pk)

        for img in images[:10]:   # Max 10 per upload
            EventGalleryImage.objects.create(
                event   = event,
                image   = img,
                caption = caption,
            )

        messages.success(request, f"✅ {len(images)} image{'s' if len(images)>1 else ''} uploaded!")
        return redirect('manage_gallery', event_pk=event_pk)

    gallery = EventGalleryImage.objects.filter(event=event)
    return render(request, 'events/manage_gallery.html', {
        'event':   event,
        'gallery': gallery,
    })


@login_required
@require_POST
def delete_gallery_image(request, image_pk):
    """Delete a gallery image"""
    img = get_object_or_404(EventGalleryImage, pk=image_pk, event__organizer=request.user)
    img.image.delete(save=False)   # Delete the file from disk
    img.delete()
    return JsonResponse({'success': True})


def view_gallery(request, event_slug):
    # from django.shortcuts import render, get_object_or_404
    # from .models import Event, EventGalleryImage

    event = get_object_or_404(Event, slug=event_slug)
    gallery = EventGalleryImage.objects.filter(event=event)
    return render(request, 'events/view_gallery.html', {
        'event': event,
        'gallery': gallery,
    })