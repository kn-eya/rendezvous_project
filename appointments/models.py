from django.db import models
from django.contrib.auth.models import User

# -------------------------
# Service général
# -------------------------
class Service(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to="services_icons/", blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

# -------------------------
# Catégorie d’un service
# -------------------------
class Category(models.Model):
    name = models.CharField(max_length=100)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='categories')
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)  # tarif spécifique par catégorie

    def __str__(self):
        return f"{self.name} ({self.service.name})"

# -------------------------
# Prestataire
# -------------------------
class Provider(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True, related_name='providers')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='providers')
    phone = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to="providers/", blank=True, null=True)
    city = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.user.username

# -------------------------
# Disponibilités du prestataire
# -------------------------
class Availability(models.Model):
    DAYS_OF_WEEK = [
        ("Mon","Lundi"), ("Tue","Mardi"), ("Wed","Mercredi"),
        ("Thu","Jeudi"), ("Fri","Vendredi"), ("Sat","Samedi"), ("Sun","Dimanche")
    ]
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="availabilities")
    day_of_week = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.provider.user.username} - {self.day_of_week} {self.start_time}-{self.end_time}"

# -------------------------
# Rendez-vous
# -------------------------
class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('accepted', 'Accepté'),
        ('refused', 'Refusé')
    ]

    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name="appointments")
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="appointments")
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    date = models.DateField()
    time = models.TimeField()
    notes = models.TextField(blank=True)  # notes optionnelles du client
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.client.username} → {self.provider.user.username} ({self.category.name})"

# -------------------------
# Notifications
# -------------------------
class Notification(models.Model):
    # Utilisateur qui reçoit la notification (client ou prestataire)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    
    # Titre et message
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Lien optionnel vers un rendez-vous
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, blank=True, null=True, related_name="notifications")
    
    # Statut lu/non lu
    is_read = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"
