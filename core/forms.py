from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
from .models import Profil


class CheckoutForm(forms.Form):
    adresse = forms.CharField(
        label="Adresse de livraison",
        max_length=250,
        required=True,
        widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Adresse de livraison'})
    )
    ville = forms.CharField(
        label="Ville",
        max_length=250,
        required=True,
        widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Ville'})
    )
    codePostale = forms.CharField(
        label="Code postale",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Code postale (optionnel)'})
    )


class UserInfoForm (forms.ModelForm): 
    telephone = forms.CharField(label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder':'Numéro de téléphone'}), required=True)
    adresse = forms.CharField(label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder':'Adresse'}), required=True)
    ville = forms.CharField(label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder':'Ville'}), required=True)
    pays = forms.CharField(label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder':'Pays'}), required=False)
    codePostale = forms.CharField(label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder':'Code Postale (Hors Sénégal)'}), required=False)
    
    class Meta : 
        model = Profil
        fields = ('telephone', 'adresse', 'ville',  'codePostale', 'pays')





class UpdateUserForm(forms.ModelForm):
    email = forms.EmailField(
        max_length=254,
        required=False,
        help_text='Optionnel. Entrez une adresse email valide.'
    )
    first_name = forms.CharField(
        max_length=30,
        required=False,
        help_text='Optionnel.'
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        help_text='Optionnel.'
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        help_text='Requis. 150 caractères ou moins. Lettres, chiffres et @/./+/-/_ uniquement.'
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Remove default labels and add bootstrap classes/placeholders
        for field_name in self.fields:
            self.fields[field_name].label = ''
            self.fields[field_name].widget.attrs['class'] = 'form-control'
            # Only set placeholder when help_text exists
            placeholder = self.fields[field_name].help_text or ''
            self.fields[field_name].widget.attrs['placeholder'] = placeholder

        # Specific customizations
        self.fields['username'].widget.attrs.update({
            'placeholder': "Nom d'utilisateur * ou N° de téléphone *",
            'autofocus': 'autofocus'
        })
        self.fields['first_name'].widget.attrs['placeholder'] = 'Prénom'
        self.fields['last_name'].widget.attrs['placeholder'] = 'Nom de famille'
        self.fields['email'].widget.attrs.update({
            'placeholder': 'Adresse email',
            'type': 'email'
        })

        # Accessibility
        self.fields['username'].widget.attrs['aria-label'] = "Nom d'utilisateur ou N° de téléphone"

        # Help texts
        self.fields['username'].help_text = "Requis. Un nom d'utilisateur ou un numéro de téléphone."
        self.fields['email'].help_text = 'Optionnel. Entrez une adresse email valide.'


class PasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set labels
        self.fields['old_password'].label = "Ancien mot de passe"
        self.fields['new_password1'].label = "Nouveau mot de passe"
        self.fields['new_password2'].label = "Confirmation du nouveau mot de passe"

        # Help texts 
        self.fields['old_password'].help_text = ''
        self.fields['new_password1'].help_text = 'Votre mot de passe doit contenir au moins 8 caractères et ne doit pas être trop simple.'
        self.fields['new_password2'].help_text = 'Entrez le même mot de passe que ci-dessus, pour vérification.'

        # Add bootstrap classes and placeholders
        for name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            placeholder_map = {
                'old_password': 'Ancien mot de passe',
                'new_password1': 'Nouveau mot de passe',
                'new_password2': 'Confirmer le nouveau mot de passe',
            }
            field.widget.attrs['placeholder'] = placeholder_map.get(name, '')

        
        if 'new_password2' in self.fields:
            self.fields['new_password2'].error_messages.update({
                'password_mismatch': "Les deux champs de mot de passe ne correspondent pas."
            })
        # Mess error update password
        try:
            self.error_messages.update({
                'password_mismatch': "Les deux champs de mot de passe ne correspondent pas."
            })
        except Exception:
            pass

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if not self.user.check_password(old_password):
            raise ValidationError("Votre ancien mot de passe est incorrect. Veuillez le saisir à nouveau.", code='password_incorrect')
        return old_password


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        max_length=254, 
        required=False,
        help_text='Optionnel. Entrez une adresse email valide.'
    )
    first_name = forms.CharField(
        max_length=30, 
        required=False, 
        help_text='Optionnel.'
    )
    last_name = forms.CharField(
        max_length=30, 
        required=False, 
        help_text='Optionnel.'
    )
    username = forms.CharField(
        max_length=150, 
        required=True, 
        help_text='Requis. 150 caractères ou moins. Lettres, chiffres et @/./+/-/_ uniquement.'
    )
   
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs): 
        super().__init__(*args, **kwargs)
        
        # Supprimer les labels par défaut
        for field_name in self.fields:
            self.fields[field_name].label = ''
            self.fields[field_name].widget.attrs['class'] = 'form-control'
            self.fields[field_name].widget.attrs['placeholder'] = self.fields[field_name].help_text
            
        # Personnalisations spécifiques
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Nom d\'utilisateur * ou N° de téléphone *',
            'autofocus': 'autofocus'
        })
        
        self.fields['first_name'].widget.attrs['placeholder'] = 'Prénom'
        self.fields['last_name'].widget.attrs['placeholder'] = 'Nom de famille'
        
        self.fields['email'].widget.attrs.update({
            'placeholder': 'Adresse email',
            'type': 'email'
        })
        self.fields['password1'].widget.attrs['placeholder'] = 'Mot de passe *'
        self.fields['password2'].widget.attrs['placeholder'] = 'Confirmer le mot de passe *'
        
        # Ajouter des attributs supplémentaires pour l'accessibilité
        self.fields['username'].widget.attrs['aria-label'] = 'Nom d\'utilisateur ou N° de téléphone'
        self.fields['password1'].widget.attrs['aria-label'] = 'Mot de passe'
        self.fields['password2'].widget.attrs['aria-label'] = 'Confirmation du mot de passe'

        self.fields['username'].help_text = ' Requis. Un nom d\'utilisateur (Lettres, chiffres et @/./+/-/_ uniquement.) ou un numéro de téléphone.'
        self.fields['password1'].help_text = ' Votre mot de passe doit contenir au moins 8 caractères et ne doit pas être trop commun.'
        self.fields['password2'].help_text = 'Entrez le même mot de passe que précédemment, pour vérification.'
        self.fields['email'].help_text = ' Optionnel. Entrez une adresse email valide.'