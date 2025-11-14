# core/forms.py
from django import forms
from .models import UserListing, Category,User

class LoginForm(forms.Form):
    email = forms.EmailField(label="Correo", widget=forms.EmailInput(attrs={
        "class": "form-control", "placeholder": "tucorreo@dominio.com"
    }))
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput(attrs={
        "class": "form-control", "placeholder": "********"
    }))

class UserListingForm(forms.ModelForm):
    class Meta:
        model = UserListing
        fields = ["title", "description", "category", "stock", "price", "photo"]
        labels = {
            "title": "Título",
            "description": "Descripción",
            "category": "Categoría",
            "stock": "Stock",
            "price": "Precio",
            "photo": "Foto",
        }
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Juego de llantas 17\""}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Describe el estado, compatibilidad, etc."}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "stock": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": 0}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

class RegisterForm(forms.Form):
    name = forms.CharField(label="Nombre", widget=forms.TextInput(attrs={
        "class": "form-control", "placeholder": "Tu nombre"
    }))
    email = forms.EmailField(label="Correo", widget=forms.EmailInput(attrs={
        "class": "form-control", "placeholder": "tucorreo@dominio.com"
    }))
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput(attrs={
        "class": "form-control", "placeholder": "********"
    }))
    password2 = forms.CharField(label="Confirmar contraseña", widget=forms.PasswordInput(attrs={
        "class": "form-control", "placeholder": "Repite la contraseña"
    }))

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Ya existe un usuario registrado con este correo.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        return cleaned