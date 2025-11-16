from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import Appointment
from twilio.rest import Client
import os

TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

def send_sms(to, message):
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(body=message, from_=TWILIO_PHONE_NUMBER, to=to)

@receiver(post_save, sender=Appointment)
def notify_client(sender, instance, created, **kwargs):
    message = f"Bonjour {instance.client.username}, votre rendez-vous avec {instance.provider.user.username} le {instance.date} à {instance.time} est {instance.status}."
    send_mail(f"Rendez-vous {instance.status}", message, None, [instance.client.email])
    if hasattr(instance.client, 'profile') and instance.client.profile.phone:
        send_sms(instance.client.profile.phone, message)
