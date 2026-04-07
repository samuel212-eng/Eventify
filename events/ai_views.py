# events/ai_views.py
# =============================================
#  AI Event Assistant — powered by Claude API
#  A floating chat widget that knows everything
#  about the event and answers attendee questions
# =============================================

import json
import requests
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings

from .models import Event


@require_POST
def ai_event_chat(request, event_pk):
    """
    Receives a user question, sends it to Claude API
    with event context, returns the answer as JSON.
    """
    event = get_object_or_404(Event, pk=event_pk)

    try:
        body     = json.loads(request.body)
        question = body.get('message', '').strip()
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Invalid request'}, status=400)

    if not question:
        return JsonResponse({'error': 'No message provided'}, status=400)

    if len(question) > 500:
        return JsonResponse({'error': 'Message too long'}, status=400)

    # Build a system prompt with full event knowledge
    tiers_info = ""
    if hasattr(event, 'tiers') and event.tiers.filter(is_active=True).exists():
        tiers_info = "\n\nTicket Tiers:\n"
        for tier in event.tiers.filter(is_active=True):
            tiers_info += f"- {tier.name}: KES {tier.price} ({tier.spots_left()} spots left)"
            if tier.perks:
                tiers_info += f" | Perks: {tier.perks}"
            tiers_info += "\n"

    speakers_info = ""
    if hasattr(event, 'speakers') and event.speakers.exists():
        speakers_info = "\n\nSpeakers:\n"
        for s in event.speakers.all():
            speakers_info += f"- {s.name}"
            if s.title:
                speakers_info += f" ({s.title})"
            if s.bio:
                speakers_info += f": {s.bio[:100]}"
            speakers_info += "\n"

    faqs_info = ""
    if hasattr(event, 'faqs') and event.faqs.exists():
        faqs_info = "\n\nFrequently Asked Questions:\n"
        for faq in event.faqs.all():
            faqs_info += f"Q: {faq.question}\nA: {faq.answer}\n\n"

    system_prompt = f"""You are a helpful AI assistant for Eventify, a Kenyan event platform.
You are answering questions about a specific event. Be concise, friendly, and helpful.
If you don't know something specific, say so honestly. Keep answers under 3 sentences unless more detail is needed.
Do NOT make up information that isn't in the event details below.

EVENT DETAILS:
Title: {event.title}
Date: {event.date.strftime('%A, %B %d, %Y at %I:%M %p')}
Location: {event.location}
Price: {'Free' if event.price == 0 else f'KES {event.price}'}
Capacity: {event.capacity} people
Spots remaining: {event.spots_left()}
Category: {event.category.name if event.category else 'General'}
Description: {event.description[:500]}
Organiser: {event.organizer.get_full_name() or event.organizer.username}
{tiers_info}{speakers_info}{faqs_info}"""

    try:
        # Call the Anthropic API
        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key':         getattr(settings, 'ANTHROPIC_API_KEY', ''),
                'anthropic-version': '2023-06-01',
                'content-type':      'application/json',
            },
            json={
                'model':      'claude-haiku-4-5-20251001',  # Fast + cheap for chat
                'max_tokens': 300,
                'system':     system_prompt,
                'messages':   [{'role': 'user', 'content': question}],
            },
            timeout=15,
        )

        if response.status_code == 200:
            data   = response.json()
            answer = data['content'][0]['text']
            return JsonResponse({'answer': answer})
        else:
            return JsonResponse({
                'answer': "I'm having trouble connecting right now. Please check the event description or contact the organiser directly."
            })

    except requests.exceptions.Timeout:
        return JsonResponse({
            'answer': "I'm a bit slow right now. Try again in a moment!"
        })
    except Exception:
        return JsonResponse({
            'answer': "Something went wrong on my end. For urgent questions, please contact the organiser."
        })
