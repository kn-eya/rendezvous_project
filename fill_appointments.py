# fill_appointments.py

from datetime import date, timedelta, datetime
from django.contrib.auth.models import User
from appointments.models import Provider, Availability, Appointment

# -------------------------------
# Prestataire et client
# -------------------------------
provider = Provider.objects.get(id=1)  # Aymen
client = User.objects.get(username='ali2')  # Ali2

# -------------------------------
# Disponibilités de la semaine
# -------------------------------
availabilities = [
    ('Mon', '09:00', '17:00', '12:00', '13:00'),
    ('Tue', '10:00', '16:00', None, None),
    ('Wed', '09:00', '17:00', '12:30', '13:30'),
    ('Thu', '08:30', '15:30', '12:00', '12:45'),
    ('Fri', '09:00', '18:00', '13:00', '14:00'),
    ('Sat', '10:00', '14:00', None, None),
    ('Sun', '11:00', '15:00', None, None)
]

for day, start, end, break_start, break_end in availabilities:
    # Supprime les anciennes disponibilités de ce jour
    Availability.objects.filter(provider=provider, day_of_week=day).delete()

    # Convertir heures en time
    start_time = datetime.strptime(start, "%H:%M").time()
    end_time = datetime.strptime(end, "%H:%M").time()
    bs = datetime.strptime(break_start, "%H:%M").time() if break_start else None
    be = datetime.strptime(break_end, "%H:%M").time() if break_end else None

    Availability.objects.create(
        provider=provider,
        day_of_week=day,
        start_time=start_time,
        end_time=end_time,
        break_start=bs,
        break_end=be
    )

print("✅ Disponibilités ajoutées")

# -------------------------------
# Rendez-vous réels
# -------------------------------
today = date.today()
start_of_week = today - timedelta(days=today.weekday())  # Lundi de la semaine

reserved_slots = [
    ('Mon', '09:30'),
    ('Mon', '11:00'),
    ('Tue', '14:00'),
    ('Wed', '15:00'),
    ('Fri', '10:00')
]

# Supprimer les rendez-vous existants pour cette semaine
Appointment.objects.filter(
    provider=provider,
    date__gte=start_of_week,
    date__lte=start_of_week + timedelta(days=6)
).delete()

for day_name, time_str in reserved_slots:
    day_index = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].index(day_name)
    appt_date = start_of_week + timedelta(days=day_index)
    appt_time = datetime.strptime(time_str, "%H:%M").time()

    Appointment.objects.create(
        provider=provider,
        client=client,
        category=provider.category,
        date=appt_date,
        time=appt_time,
        status='accepted'
    )

print("✅ Rendez-vous réels ajoutés")
