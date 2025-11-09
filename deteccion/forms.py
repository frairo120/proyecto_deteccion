# deteccion/forms.py
import re
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from .models import Cargo, Empleado, Menu, Module, GroupModulePermission
from deteccion.models import Group

User = get_user_model()

class LoginForm(forms.Form):
    # El campo para el nombre de usuario
    username = forms.CharField(
        label='Nombre de Usuario',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa tu email'
        })
    )
    
    # El campo para la contraseña
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa tu contraseña'
        })
    )

class CargoForm(forms.ModelForm):
    class Meta:
        model = Cargo
        # Incluye todos los campos de tu modelo Cargo
        fields = ['nombre', 'descripcion', 'activo'] 

class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = [
            'nombres', 'apellidos', 'user', 'cedula_ecuatoriana', 
            'dni', 'fecha_nacimiento', 'cargo', 'sueldo', 
            'fecha_ingreso', 'direccion', 'activo'
        ]
        # ELIMINAMOS EL BLOQUE 'widgets' DE AQUÍ
        
    # Usamos el constructor para aplicar estilos y atributos a TODOS los campos
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. Iterar sobre todos los campos para aplicar la clase CSS
        for field_name, field in self.fields.items():
            
            # Excluir el campo 'activo' porque es un CheckboxInput y usa diferente estilo
            if field_name != 'activo':
                # 2. Aplicar la clase 'form-control' a la mayoría de los widgets
                # setdefault se asegura de que si ya tiene una clase, la mantenga y añada 'form-control'
                field.widget.attrs.setdefault('class', 'form-control')

            # 3. Personalizar campos de fecha para usar el selector nativo HTML5
            if field_name in ['fecha_nacimiento', 'fecha_ingreso']:
                field.widget.attrs.update({'type': 'date'})

            # 4. Aplicar Placeholder para campos de texto y número
            if isinstance(field.widget, (forms.TextInput, forms.NumberInput)):
                field.widget.attrs.setdefault('placeholder', field.label)

            # 5. Personalizar el campo 'activo' (checkbox)
            if field_name == 'activo':
                field.widget.attrs.update({'class': 'form-check-input'})

        # 6. Personalización específica para campos particulares
        self.fields['user'].queryset = get_user_model().objects.filter(empleado__isnull=True)
        self.fields['user'].empty_label = "--- Seleccione un usuario ---"
        
        self.fields['sueldo'].widget.attrs.update({
            'min': '0',
            'step': '0.01'
        })

    def clean_cedula_ecuatoriana(self):
        cedula = self.cleaned_data.get('cedula_ecuatoriana')
        # Aquí puedes agregar validaciones adicionales si es necesario
        return cedula

    def clean(self):
        cleaned_data = super().clean()
        cedula_ecuatoriana = cleaned_data.get('cedula_ecuatoriana')
        dni = cleaned_data.get('dni')
        
        # Validar que al menos uno de los dos documentos esté presente
        if not cedula_ecuatoriana and not dni:
            raise forms.ValidationError(
                "Debe proporcionar al menos uno de los documentos: Cédula ecuatoriana o DNI internacional."
            )
        
        return cleaned_data


class UserForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False
    )
    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False
    )

    class Meta:
        model = get_user_model()
        fields = [
            'username', 'first_name', 'last_name', 'email', 
            'password1', 'password2', 'is_active', 'is_staff', 
            'is_superuser', 'groups'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Aplicar clases a los campos del UserForm
        for field_name, field in self.fields.items():
            if field_name not in ['is_active', 'is_staff', 'is_superuser']:
                field.widget.attrs.setdefault('class', 'form-control')
            else:
                # Para checkboxes
                field.widget.attrs.setdefault('class', 'form-check-input')
        
        # Personalizar el campo groups
        self.fields['groups'].widget.attrs.update({'class': 'form-select'})

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 or password2:  # Validar solo si hay contraseña
            if password1 != password2:
                raise forms.ValidationError("Las contraseñas no coinciden.")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password1")
        if password:
            user.set_password(password)
        if commit:
            user.save()
            self.save_m2m()  # Importante para guardar relaciones ManyToMany como 'groups'
        return user

class UserPasswordChangeForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese la nueva contraseña'
        }),
        strip=False,
    )
    new_password2 = forms.CharField(
        label="Confirmar nueva contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme la nueva contraseña'
        }),
    )

class MenuForm(forms.ModelForm):
    class Meta:
        model = Menu
        fields = [
            "name",
            "icon",
            "order",
           
        ]
        error_messages = {
          
            "name": {
                "unique": "Ya existe un menu con este nombre.",
            },
        }
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Ingrese nombre del menu",
                "id": "id_name",
                "class": "shadow-sm bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 pr-12 dark:bg-principal dark:border-gray-600 dark:placeholder-gray-400 dark:text-gray-400 dark:focus:ring-blue-500 dark:focus:border-blue-500 dark:shadow-sm-light",
            }),
          
            "icon": forms.TextInput(attrs={
                "placeholder": "Ingrese clase del ícono (ej. bi bi-house)",
                "id": "id_icon",
                "class": "shadow-sm bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 pr-12 dark:bg-principal dark:border-gray-600 dark:placeholder-gray-400 dark:text-gray-400 dark:focus:ring-blue-500 dark:focus:border-blue-500 dark:shadow-sm-light",
            }),
            "order": forms.NumberInput(attrs={
                "placeholder": "Ingrese el orden",
                "id": "id_order",
                "class": "shadow-sm bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 pr-12 dark:bg-principal dark:border-gray-600 dark:placeholder-gray-400 dark:text-gray-400 dark:focus:ring-blue-500 dark:focus:border-blue-500 dark:shadow-sm-light",
            }),
         
        }
        labels = {
            "name": "Nombre Menu",
            "icon": "Ícono",
            "order": "Orden",
            
        }

    def clean_name(self):
        name = self.cleaned_data.get("name")
        return name.upper()
    
    def clean_icon(self):
        icon = self.cleaned_data['icon']
        if not icon:
            raise forms.ValidationError("El campo ícono es requerido.")
        
        # Patrones para FontAwesome v5 y v6
        patterns = [
            r'^(fas|far|fal|fad|fab|fa)\s+fa-\w+',      # fas fa-user (v5)
            r'^fa-(solid|regular|light|duotone|brands)\s+fa-\w+',  # fa-solid fa-user (v6)
            r'^fa-\w+$',                                 # fa-user (formato simple)
        ]
        
        is_valid = any(re.match(pattern, icon) for pattern in patterns)
        
        if not is_valid:
            raise forms.ValidationError(
                "Formato de ícono inválido. Ejemplos válidos: "
                "'fas fa-user', 'fa-solid fa-person', 'fa-home'"
            )
        
        return icon


class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = [
            "name",
            "url",
            "menu",
            "description",
            "icon",
            "order",
            "is_active",
            "permissions",
        ]
        error_messages = {
            "url": {
                "unique": "Ya existe un módulo con esta URL.",
            },
            "name": {
                "unique": "Ya existe un módulo con este nombre.",
            },
        }
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Ingrese nombre del módulo",
                "id": "id_name",
                "class": "shadow-sm bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 pr-12 dark:bg-principal dark:border-gray-600 dark:placeholder-gray-400 dark:text-gray-400 dark:focus:ring-blue-500 dark:focus:border-blue-500 dark:shadow-sm-light",
            }),
            "url": forms.TextInput(attrs={
                "placeholder": "Ingrese la URL del módulo",
                "id": "id_url",
                "class": "shadow-sm bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 pr-12 dark:bg-principal dark:border-gray-600 dark:placeholder-gray-400 dark:text-gray-400 dark:focus:ring-blue-500 dark:focus:border-blue-500 dark:shadow-sm-light",
            }),
            "menu": forms.Select(attrs={
                "class": "shadow-sm bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-principal dark:border-gray-600 dark:text-gray-400 dark:focus:ring-blue-500 dark:focus:border-blue-500",
            }),
            "description": forms.Textarea(attrs={
                "placeholder": "Descripción opcional del módulo",
                "class": "shadow-sm bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 pr-12 dark:bg-principal dark:border-gray-600 dark:placeholder-gray-400 dark:text-gray-400 dark:focus:ring-blue-500 dark:focus:border-blue-500 dark:shadow-sm-light",
                "rows": 3,
            }),
            "icon": forms.TextInput(attrs={
                "placeholder": "Ingrese clase del ícono (ej. bi bi-house)",
                "id": "id_icon",
                "class": "shadow-sm bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 pr-12 dark:bg-principal dark:border-gray-600 dark:placeholder-gray-400 dark:text-gray-400 dark:focus:ring-blue-500 dark:focus:border-blue-500 dark:shadow-sm-light",
            }),
            "order": forms.NumberInput(attrs={
                "placeholder": "Ingrese el orden",
                "id": "id_order",
                "class": "shadow-sm bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 pr-12 dark:bg-principal dark:border-gray-600 dark:placeholder-gray-400 dark:text-gray-400 dark:focus:ring-blue-500 dark:focus:border-blue-500 dark:shadow-sm-light",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "mt-1 block px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm",
            }),
            "permissions": forms.SelectMultiple(attrs={
                "class": "shadow-sm bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full dark:bg-principal dark:border-gray-600 dark:text-gray-400 dark:focus:ring-blue-500 dark:focus:border-blue-500",
            }),
        }
        labels = {
            "name": "Nombre",
            "url": "Url",
            "menu": "Menú",
            "description": "Descripción",
            "icon": "Ícono",
            "order": "Orden",
            "is_active": "Activo",
            "permissions": "Permisos",
        }

    def clean_name(self):
        name = self.cleaned_data.get("name")
        return name.upper()
    
    def clean_icon(self):
        icon = self.cleaned_data['icon']
        if not icon:
            raise forms.ValidationError("El campo ícono es requerido.")
        
        # Patrones para FontAwesome v5 y v6
        patterns = [
            r'^(fas|far|fal|fad|fab|fa)\s+fa-\w+',      # fas fa-user (v5)
            r'^fa-(solid|regular|light|duotone|brands)\s+fa-\w+',  # fa-solid fa-user (v6)
            r'^fa-\w+$',                                 # fa-user (formato simple)
        ]
        
        is_valid = any(re.match(pattern, icon) for pattern in patterns)
        
        if not is_valid:
            raise forms.ValidationError(
                "Formato de ícono inválido. Ejemplos válidos: "
                "'fas fa-user', 'fa-solid fa-person', 'fa-home'"
            )
        
        return icon
    

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = [
            "name",
            "permissions",
        ]
        error_messages = {

            "name": {
                "unique": "Ya existe un módulo con este nombre.",
            },
        }
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Ingrese nombre del módulo",
                "id": "id_name",
                "class": "shadow-sm bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 pr-12 dark:bg-principal dark:border-gray-600 dark:placeholder-gray-400 dark:text-gray-400 dark:focus:ring-blue-500 dark:focus:border-blue-500 dark:shadow-sm-light",
            }),
            "url": forms.TextInput(attrs={
                "placeholder": "Ingrese la URL del módulo",
                "id": "id_url",
                "class": "shadow-sm bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 pr-12 dark:bg-principal dark:border-gray-600 dark:placeholder-gray-400 dark:text-gray-400 dark:focus:ring-blue-500 dark:focus:border-blue-500 dark:shadow-sm-light",
            }),
            "menu": forms.Select(attrs={
                "class": "shadow-sm bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-principal dark:border-gray-600 dark:text-gray-400 dark:focus:ring-blue-500 dark:focus:border-blue-500",
            }),
            "description": forms.Textarea(attrs={
                "placeholder": "Descripción opcional del módulo",
                "class": "shadow-sm bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 pr-12 dark:bg-principal dark:border-gray-600 dark:placeholder-gray-400 dark:text-gray-400 dark:focus:ring-blue-500 dark:focus:border-blue-500 dark:shadow-sm-light",
                "rows": 3,
            }),
            "icon": forms.TextInput(attrs={
                "placeholder": "Ingrese clase del ícono (ej. bi bi-house)",
                "id": "id_icon",
                "class": "shadow-sm bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 pr-12 dark:bg-principal dark:border-gray-600 dark:placeholder-gray-400 dark:text-gray-400 dark:focus:ring-blue-500 dark:focus:border-blue-500 dark:shadow-sm-light",
            }),
            "order": forms.NumberInput(attrs={
                "placeholder": "Ingrese el orden",
                "id": "id_order",
                "class": "shadow-sm bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 pr-12 dark:bg-principal dark:border-gray-600 dark:placeholder-gray-400 dark:text-gray-400 dark:focus:ring-blue-500 dark:focus:border-blue-500 dark:shadow-sm-light",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "mt-1 block px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm",
            }),
            "permissions": forms.SelectMultiple(attrs={
                "class": "shadow-sm bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full dark:bg-principal dark:border-gray-600 dark:text-gray-400 dark:focus:ring-blue-500 dark:focus:border-blue-500",
            }),
        }
        labels = {
            "name": "Nombre",
            "permissions": "Permisos",
        }

    def clean_name(self):
        name = self.cleaned_data.get("name")
        return name.upper()
    
    def clean_icon(self):
        icon = self.cleaned_data['icon']
        if not icon:
            raise forms.ValidationError("El campo ícono es requerido.")
        
        # Patrones para FontAwesome v5 y v6
        patterns = [
            r'^(fas|far|fal|fad|fab|fa)\s+fa-\w+',      # fas fa-user (v5)
            r'^fa-(solid|regular|light|duotone|brands)\s+fa-\w+',  # fa-solid fa-user (v6)
            r'^fa-\w+$',                                 # fa-user (formato simple)
        ]
        
        is_valid = any(re.match(pattern, icon) for pattern in patterns)
        
        if not is_valid:
            raise forms.ValidationError(
                "Formato de ícono inválido. Ejemplos válidos: "
                "'fas fa-user', 'fa-solid fa-person', 'fa-home'"
            )
        
        return icon
    # C:\Users\jonat\Desktop\modelo_entrenado\sistema\deteccion\forms.py

from django import forms
# 🚨 CRÍTICO: Debes importar esto para obtener tu modelo de usuario personalizado
from django.contrib.auth import get_user_model 







# Obtener tu modelo User. Si no lo importas, UserForm fallará al intentar usar 'model = User'.
class UserForm(forms.ModelForm):
    first_name = forms.CharField(
        label='Nombre',
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese el nombre'
        })
    )
    
    last_name = forms.CharField(
        label='Apellido',
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese el apellido'
        })
    )
    
    username = forms.CharField(
        label='Nombre de usuario',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese el nombre de usuario'
        })
    )
    
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese el correo electrónico'
        })
    )
    
    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese la contraseña'
        })
    )
    
    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme la contraseña'
        })
    )

    is_active = forms.BooleanField(
        label='Activo',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    is_staff = forms.BooleanField(
        label='Es staff',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    is_superuser = forms.BooleanField(
        label='Es superusuario',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    # Campo Groups (Selección Múltiple)
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input-list'}),
        label="Grupos del Usuario"
    )

    class Meta:
        model = User
        # 🟢 CAMBIO CLAVE: 'groups' como cadena
        fields = ('username', 'first_name', 'last_name', 'email', 
                  'password1', 'password2', 'is_active', 'is_staff', 'is_superuser', 'groups',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:  # Si es una edición
            self.fields['password1'].required = False
            self.fields['password2'].required = False

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if self.instance.pk and not password1:
            return None
        if password1 or password2:
            if password1 != password2:
                raise forms.ValidationError("Las contraseñas no coinciden.")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password1"):
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            # Guardar la relación ManyToMany (Groups)
            self.save_m2m() 
        return user



class UserEditForm(forms.ModelForm):
    first_name = forms.CharField(
        label='Nombre',
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese el nombre'
        })
    )
    
    last_name = forms.CharField(
        label='Apellido',
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese el apellido'
        })
    )
    
    username = forms.CharField(
        label='Nombre de usuario',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese el nombre de usuario'
        })
    )
    
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese el correo electrónico'
        })
    )
    
    is_active = forms.BooleanField(
        label='Activo',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    is_staff = forms.BooleanField(
        label='Es staff',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    is_superuser = forms.BooleanField(
        label='Es superusuario',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    # Campo Groups (Selección Múltiple)
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input-list'}),
        label="Grupos del Usuario"
    )

    class Meta:
        model = User
        # 🟢 CAMBIO CLAVE: 'groups' como cadena
        fields = ('username', 'first_name', 'last_name', 'email', 
                  'is_active', 'is_staff', 'is_superuser', 'groups',)
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Añade lógica si la necesitas, como inicializar el widget de groups
   
class UserPasswordChangeForm(forms.Form):
    new_password1 = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese la nueva contraseña'
        }),
        strip=False,
    )
    new_password2 = forms.CharField(
        label="Confirmar nueva contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme la nueva contraseña'
        }),
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("new_password1")
        p2 = cleaned_data.get("new_password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data

    def save(self, commit=True):
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user



class GroupModulePermissionForm(forms.ModelForm):
    class Meta:
        model = GroupModulePermission
        fields = ['group', 'module', 'permissions']
        widgets = {
            'permissions': forms.CheckboxSelectMultiple(),  # Muestra los permisos como checkboxes
        }
        labels = {
            'group': 'Grupo',
            'module': 'Módulo',
            'permissions': 'Permisos',
        }
        help_texts = {
            'permissions': 'Selecciona los permisos que se asignarán a este grupo para el módulo.',
        }





from .models import Capacitacion, Evaluacion, Pregunta, OpcionRespuesta


class CapacitacionForm(forms.ModelForm):
    """Formulario de creación/edición con validaciones según el tipo de contenido."""
    class Meta:
        model = Capacitacion
        fields = [
            'titulo', 'descripcion', 'tipo_contenido', 'contenido_texto',
            'archivo_pdf', 'archivo_imagen', 'url_video',
            'duracion_minutos', 'puntaje_minimo', 'intentos_permitidos', 'estado'
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'contenido_texto': forms.Textarea(attrs={'rows': 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo_contenido')
        pdf = cleaned_data.get('archivo_pdf')
        texto = cleaned_data.get('contenido_texto')
        video = cleaned_data.get('url_video')
        imagen = cleaned_data.get('archivo_imagen')

        # Validaciones por tipo de contenido
        if tipo == 'pdf' and not pdf:
            raise forms.ValidationError("Debes subir un archivo PDF para este tipo de contenido.")
        elif tipo == 'texto' and not texto:
            raise forms.ValidationError("Debes ingresar contenido textual.")
        elif tipo == 'video' and not video:
            raise forms.ValidationError("Debes ingresar una URL de video.")
        elif tipo == 'imagen' and not imagen:
            raise forms.ValidationError("Debes subir una imagen para este tipo de contenido.")

        return cleaned_data


class EvaluacionForm(forms.ModelForm):
    """Formulario para crear una evaluación de una capacitación."""
    class Meta:
        model = Evaluacion
        fields = ['capacitacion', 'titulo', 'descripcion', 'activa']


class PreguntaForm(forms.ModelForm):
    """Formulario para agregar preguntas a una evaluación."""
    class Meta:
        model = Pregunta
        fields = ['evaluacion', 'texto', 'tipo', 'puntaje', 'orden']


class OpcionRespuestaForm(forms.ModelForm):
    """Formulario para las opciones de una pregunta."""
    class Meta:
        model = OpcionRespuesta
        fields = ['pregunta', 'texto', 'es_correcta', 'orden']
