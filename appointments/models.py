from django.db import models
from django.contrib.auth.models import User

class Service(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    def __str__(self):
        return self.name

class SubService(models.Model):
    name = models.CharField(max_length=100)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="subservices")
    def __str__(self):
        return f"{self.service.name} - {self.name}"

class Provider(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    subservice = models.ForeignKey(SubService, on_delete=models.CASCADE, related_name="providers")
    phone = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to="providers/", blank=True, null=True)
    def __str__(self):
        return f"{self.user.username} - {self.subservice.name}"

class Availability(models.Model):
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="availabilities")
    day_of_week = models.IntegerField(choices=[(i,i) for i in range(7)])
    start_time = models.TimeField()
    end_time = models.TimeField()
    def __str__(self):
        return f"{self.provider.user.username} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"

class Appointment(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('accepted', 'Accepted'), ('refused', 'Refused')]
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name="appointments")
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="appointments")
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    def __str__(self):
        return f"{self.client.username} → {self.provider.user.username} on {self.date} {self.time}"
