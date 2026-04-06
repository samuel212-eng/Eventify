import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eventsite.settings')
django.setup()

from events.models import Event
from django.utils.text import slugify

for event in Event.objects.all():
    if not event.slug:
        base = slugify(event.title)
        slug = base
        n = 1
        while Event.objects.filter(slug=slug).exclude(pk=event.pk).exists():
            slug = f"{base}-{n}"
            n += 1
        Event.objects.filter(pk=event.pk).update(slug=slug)
        print(f"Fixed: {event.title}")

print("All done!")
