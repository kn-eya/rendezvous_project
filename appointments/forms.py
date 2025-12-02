from django import forms
from .models import Appointment, Provider, Service, Availability, Category


# =====================
# Formulaire de rendez-vous
# =====================
class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['date', 'time', 'notes']  # plus besoin de provider/category ici
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }


# =====================
# Formulaire du prestataire
# =====================
class ProviderForm(forms.ModelForm):
    class Meta:
        model = Provider
        fields = ['service', 'category', 'phone', 'photo', 'city', 'address']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrer dynamiquement les catégories selon le service sélectionné
        if 'service' in self.data:
            try:
                service_id = int(self.data.get('service'))
                self.fields['category'].queryset = Category.objects.filter(service_id=service_id)
            except (ValueError, TypeError):
                self.fields['category'].queryset = Category.objects.none()
        elif self.instance.pk and self.instance.service:
            self.fields['category'].queryset = Category.objects.filter(service=self.instance.service)
        else:
            self.fields['category'].queryset = Category.objects.none()

from django import forms
from django.forms import inlineformset_factory
from .models import Service, Category

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'description', 'icon', 'is_active']

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'price']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Nom de la catégorie'}),
            'price': forms.NumberInput(attrs={'step': 0.01, 'placeholder': 'Prix'}),
        }

# Inline formset : catégories liées à un service
CategoryFormSet = inlineformset_factory(
    Service, Category, form=CategoryForm,
    fields=['name', 'price'], extra=1, can_delete=True
)


# =====================
# Formulaire des disponibilités
# =====================
class AvailabilityForm(forms.ModelForm):
    class Meta:
        model = Availability
        fields = ['day_of_week', 'start_time', 'end_time']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }
