from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

from .models import Appointment, Notification


@receiver(post_save, sender=Appointment)
def create_appointment_notifications(sender, instance, created, **kwargs):
    """
    Notifications internes + email lors de la création ou mise à jour d'un RDV
    """
    # ===========================
    # 🎯 1. Lors de la création du RDV
    # ===========================
    if created:
        # ---- Notification Prestataire ----
        Notification.objects.create(
            user=instance.provider.user,
            title="Nouveau rendez-vous",
            message=(
                f"Vous avez un nouveau rendez-vous avec {instance.client.username} "
                f"le {instance.date} à {instance.time}."
            ),
            appointment=instance
        )

        # ---- Notification Client ----
        Notification.objects.create(
            user=instance.client,
            title="Rendez-vous confirmé",
            message=(
                f"Votre rendez-vous avec {instance.provider.user.username} "
                f"le {instance.date} à {instance.time} a été enregistré."
            ),
            appointment=instance
        )

        # ---- Envoi email (client + prestataire) ----
        send_mail(
            subject="Confirmation de rendez-vous",
            message=(
                f"Bonjour,\n\nVotre rendez-vous est confirmé.\n"
                f"Prestataire : {instance.provider.user.username}\n"
                f"Date : {instance.date}\n"
                f"Heure : {instance.time}\n\nMerci."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.client.email],
            fail_silently=True,
        )

        send_mail(
            subject="Nouveau rendez-vous",
            message=(
                f"Bonjour,\n\nUn client a réservé un rendez-vous.\n"
                f"Client : {instance.client.username}\n"
                f"Date : {instance.date}\n"
                f"Heure : {instance.time}\n\nMerci."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.provider.user.email],
            fail_silently=True,
        )

        return

    # ===========================
    # 🎯 2. Si mise à jour du rendez-vous
    # ===========================
    Notification.objects.create(
        user=instance.client,
        title="Mise à jour de votre rendez-vous",
        message=(
            f"Votre rendez-vous avec {instance.provider.user.username} "
            f"le {instance.date} à {instance.time} a été modifié.\n"
            f"Nouveau statut : {instance.status}"
        ),
        appointment=instance
    )

    Notification.objects.create(
        user=instance.provider.user,
        title="Mise à jour d'un rendez-vous",
        message=(
            f"Le rendez-vous avec {instance.client.username} "
            f"le {instance.date} à {instance.time} a été mis à jour.\n"
            f"Statut : {instance.status}"
        ),
        appointment=instance
    )
