from django import forms
from .models import Appointment, Provider, Service, Availability, Category
from django import forms
from .models import Provider, PortfolioItem


# =====================
# Formulaire de rendez-vous
# =====================
class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['date', 'start_time', 'end_time', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

class ProviderForm(forms.ModelForm):
    class Meta:
        model = Provider
        fields = ['service', 'category', 'phone', 'photo', 'city', 'address']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

class PortfolioItemForm(forms.ModelForm):
    class Meta:
        model = PortfolioItem
        fields = ['image', 'title', 'description', 'price']

class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['date', 'start_time', 'end_time','notes']

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'service', 'price']

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'description', 'icon', 'is_active']

class AvailabilityForm(forms.ModelForm):
    class Meta:
        model = Availability
        fields = ['day_of_week', 'start_time', 'end_time', 'break_start', 'break_end']
