from django.contrib import admin

# deteccion/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    Menu, 
    Module, 
    GroupModulePermission, 
    User, 
    Cargo, 
    Empleado,
    Alert
)

# --- 1. Definir la clase Admin para el modelo User personalizado ---
# Esto es crucial para que el modelo User se muestre correctamente en el Admin.
class UserAdmin(BaseUserAdmin):
    # Campos que se mostrarán en la lista de usuarios del Admin
    list_display = ('email', 'username', 'first_name', 'last_name', 'is_staff')
    # Campos que se podrán buscar
    search_fields = ('email', 'username', 'first_name', 'last_name', 'dni')
    # Campos para filtrar la lista
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')

    
    # Define la apariencia de las secciones de edición de usuario
    fieldsets = (
        (None, {'fields': ('email', 'password')}), # Se usa email como login
        ('Personal info', {'fields': ('first_name', 'last_name', 'dni', 'phone', 'direction', 'image')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    # Los REQUIRED_FIELDS definidos en tu modelo ya no se piden aquí.
    ordering = ('email',)


# --- 2. Definir las clases Admin para tus otros modelos ---

class MenuAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'icon')
    list_editable = ('order', 'icon')
    ordering = ('order', 'name')
    search_fields = ('name',)

class ModuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'menu', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    list_filter = ('menu', 'is_active')
    search_fields = ('name', 'url')

class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'cargo', 'cedula_ecuatoriana', 'fecha_ingreso', 'activo')
    list_filter = ('cargo', 'activo', 'fecha_ingreso')
    search_fields = ('nombres', 'apellidos', 'cedula_ecuatoriana')


class AlertAdmin(admin.ModelAdmin):
    list_display = ('message', 'level', 'timestamp', 'resolved')  # columnas que se verán en la lista
    list_filter = ('level', 'resolved', 'timestamp')  # filtros en la barra lateral
    search_fields = ('message', 'missing')  # barra de búsqueda
    readonly_fields = ('timestamp',)  # campo solo lectura




# --- 3. Registrar los modelos en el sitio de administración ---

# Desregistrar el usuario por defecto (si estaba registrado) y registrar el tuyo
# Aunque tu modelo User hereda de AbstractUser, es mejor registrarlo con tu clase personalizada.
admin.site.register(User, UserAdmin)

# Registrar tus modelos de Menu y Módulos
admin.site.register(Menu, MenuAdmin)
admin.site.register(Module, ModuleAdmin)
admin.site.register(GroupModulePermission)

# Registrar tus modelos de Empleados
admin.site.register(Cargo)
admin.site.register(Empleado, EmpleadoAdmin)
# Register your models here.
admin.site.register(Alert, AlertAdmin)



from django.utils.html import format_html
from .models import (
    Capacitacion,
    ProgresoCapacitacion,
    Evaluacion,
    Pregunta,
    OpcionRespuesta,
    IntentoEvaluacion,
    RespuestaUsuario,
    Certificado
)


# --- Inline para las opciones de respuesta ---
class OpcionRespuestaInline(admin.TabularInline):
    model = OpcionRespuesta
    extra = 2
    fields = ('texto', 'es_correcta', 'orden')
    ordering = ('orden',)


# --- Inline para las preguntas dentro de Evaluacion ---
class PreguntaInline(admin.TabularInline):
    model = Pregunta
    extra = 1
    show_change_link = True
    fields = ('texto', 'tipo', 'puntaje', 'orden')


# --- Evaluacion admin ---
@admin.register(Evaluacion)
class EvaluacionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'capacitacion', 'activa', 'creada_por', 'fecha_creacion')
    list_filter = ('activa', 'fecha_creacion')
    search_fields = ('titulo', 'capacitacion__titulo')
    inlines = [PreguntaInline]
    autocomplete_fields = ['capacitacion', 'creada_por']


# --- Pregunta admin ---
@admin.register(Pregunta)
class PreguntaAdmin(admin.ModelAdmin):
    list_display = ('texto_corto', 'evaluacion', 'tipo', 'puntaje', 'orden')
    list_filter = ('tipo', 'evaluacion')
    search_fields = ('texto',)
    inlines = [OpcionRespuestaInline]

    def texto_corto(self, obj):
        return obj.texto[:60] + ("..." if len(obj.texto) > 60 else "")
    texto_corto.short_description = "Pregunta"


# --- Capacitacion admin ---
@admin.register(Capacitacion)
class CapacitacionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo_contenido', 'estado', 'creado_por', 'fecha_creacion', 'duracion_minutos', 'vista_previa')
    list_filter = ('tipo_contenido', 'estado', 'fecha_creacion')
    search_fields = ('titulo', 'descripcion')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    autocomplete_fields = ['creado_por']

    fieldsets = (
        ("Información General", {
            'fields': ('titulo', 'descripcion', 'estado', 'creado_por')
        }),
        ("Contenido", {
            'fields': ('tipo_contenido', 'contenido_texto', 'archivo_pdf', 'archivo_imagen', 'url_video')
        }),
        ("Configuración de Evaluación", {
            'fields': ('duracion_minutos', 'puntaje_minimo', 'intentos_permitidos')
        }),
        ("Tiempos", {
            'fields': ('fecha_creacion', 'fecha_actualizacion')
        }),
    )

    def vista_previa(self, obj):
        """Muestra una vista del tipo de contenido"""
        if obj.tipo_contenido == 'pdf' and obj.archivo_pdf:
            return format_html(f"<a href='{obj.archivo_pdf.url}' target='_blank'>📄 Ver PDF</a>")
        elif obj.tipo_contenido == 'video' and obj.url_video:
            return format_html(f"<a href='{obj.url_video}' target='_blank'>🎬 Ver Video</a>")
        elif obj.tipo_contenido == 'imagen' and obj.archivo_imagen:
            return format_html(f"<img src='{obj.archivo_imagen.url}' width='100' />")
        elif obj.tipo_contenido == 'texto':
            return format_html(obj.contenido_texto[:60] + "...")
        return "-"
    vista_previa.short_description = "Vista Previa"


# --- Progreso de Capacitación ---
@admin.register(ProgresoCapacitacion)
class ProgresoCapacitacionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'capacitacion', 'progreso_porcentaje', 'completada', 'fecha_inicio')
    list_filter = ('completada',)
    search_fields = ('usuario__email', 'capacitacion__titulo')


# --- Intento de Evaluación ---
@admin.register(IntentoEvaluacion)
class IntentoEvaluacionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'evaluacion', 'puntaje_obtenido', 'aprobado', 'numero_intento', 'fecha_intento')
    list_filter = ('aprobado',)
    search_fields = ('usuario__email', 'evaluacion__titulo')


# --- Certificados ---
@admin.register(Certificado)
class CertificadoAdmin(admin.ModelAdmin):
    list_display = ('codigo_certificado', 'usuario', 'capacitacion', 'puntaje_final', 'fecha_emision')
    search_fields = ('codigo_certificado', 'usuario__email', 'capacitacion__titulo')
    list_filter = ('fecha_emision',)


# --- Respuestas de Usuario (solo para inspección) ---
@admin.register(RespuestaUsuario)
class RespuestaUsuarioAdmin(admin.ModelAdmin):
    list_display = ('intento', 'pregunta', 'opcion_seleccionada')
    search_fields = ('intento__usuario__email', 'pregunta__texto')