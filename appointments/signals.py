from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Appointment, Notification

@receiver(post_save, sender=Appointment)
def create_appointment_notification(sender, instance, created, **kwargs):
    """
    Génère une notification quand un rendez-vous est créé ou mis à jour.
    """
    if created:
        # Notification pour le prestataire
        Notification.objects.create(
            user=instance.provider.user,
            title="Nouveau rendez-vous",
            message=f"Vous avez un nouveau rendez-vous avec {instance.client.username} "
                    f"le {instance.date} à {instance.time}.",
            appointment=instance
        )
        # Notification pour le client
        Notification.objects.create(
            user=instance.client,
            title="Rendez-vous confirmé",
            message=f"Votre rendez-vous avec {instance.provider.user.username} "
                    f"le {instance.date} à {instance.time} a été enregistré.",
            appointment=instance
        )
    else:
        # Si le rendez-vous est mis à jour (statut changé)
        Notification.objects.create(
            user=instance.client,
            title="Mise à jour du rendez-vous",
            message=f"Le rendez-vous avec {instance.provider.user.username} "
                    f"le {instance.date} à {instance.time} a été mis à jour. "
                    f"Statut actuel : {instance.status}.",
            appointment=instance
        )
        Notification.objects.create(
            user=instance.provider.user,
            title="Mise à jour du rendez-vous",
            message=f"Le rendez-vous avec {instance.client.username} "
                    f"le {instance.date} à {instance.time} a été mis à jour. "
                    f"Statut actuel : {instance.status}.",
            appointment=instance
        )
