from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission, PermissionsMixin
from django.db import models
from django.db.models import UniqueConstraint
from django.core.validators import RegexValidator
from django.db import models
from .util import valida_cedula
from django.utils import timezone


class Menu(models.Model):
   
    name = models.CharField(verbose_name='Nombre', max_length=150, unique=True)
    icon = models.CharField(verbose_name='Icono', max_length=100, default='bi bi-calendar-x-fill')
    order = models.PositiveSmallIntegerField(verbose_name='Orden', default=0)
    
    def __str__(self):
        return self.name

   
   
    class Meta:
        verbose_name = 'Menu'
        verbose_name_plural = 'Menus'
        ordering = ['order', 'name']



class Module(models.Model):
    url = models.CharField(verbose_name='Url', max_length=100, unique=True)
    name = models.CharField(verbose_name='Nombre', max_length=100)
    menu = models.ForeignKey(Menu, on_delete=models.PROTECT, verbose_name='Menu', related_name='modules')
    description = models.CharField(verbose_name='Descripción', max_length=200, null=True, blank=True)
    icon = models.CharField(verbose_name='Icono', max_length=100, default='bi bi-x-octagon')
    is_active = models.BooleanField(verbose_name='Es activo', default=True)
    order = models.PositiveSmallIntegerField(verbose_name='Orden', default=0)
  
    permissions = models.ManyToManyField(Permission, blank=True)

    def __str__(self):
        return f'{self.name} [{self.url}]'

    class Meta:
        verbose_name = 'Módulo' 
        verbose_name_plural = 'Módulos'
        ordering = ['menu', 'order', 'name']

class GroupModulePermissionManager(models.Manager):
    """ Obtiene los módulos con su respectivo menú del grupo requerido que estén activos """ 
    def get_group_module_permission_active_list(self, group_id):
        return self.select_related('module','module__menu').filter(
            group_id=group_id,
            module__is_active=True
        )
    
class GroupModulePermission(models.Model):
    group = models.ForeignKey(Group, on_delete=models.PROTECT, verbose_name='Grupo', related_name='module_permissions')
    module = models.ForeignKey('deteccion.Module', on_delete=models.PROTECT, verbose_name='Módulo', related_name='group_permissions')
    permissions = models.ManyToManyField(Permission, verbose_name='Permisos')
    # Manager personalizado (conserva toda la funcionalidad del manager por defecto)
    objects = GroupModulePermissionManager()
    def __str__(self):
        return f"{self.module.name} - {self.group.name}"

    class Meta:
        verbose_name = 'Grupo módulo permiso'
        verbose_name_plural = 'Grupos módulos permisos'
        ordering = ['group', 'module']
        constraints = [
            UniqueConstraint(fields=['group', 'module'], name='unique_group_module')
        ]

"""
Modelo User: Extiende el usuario estándar de Django para añadir campos personalizados.
Utiliza email como identificador principal para login en lugar del username.

Ejemplos:
1. admin (email: admin@empresa.com) - Administrador del sistema
2. jperez (email: jperez@empresa.com) - Usuario con roles de Vendedor y Contador
3. mgarcia (email: mgarcia@empresa.com) - Usuario con roles de Contador y Auditor
"""
class User(AbstractUser, PermissionsMixin):
    dni = models.CharField(verbose_name='Cédula o RUC', max_length=13, blank=True, null=True)
    image = models.ImageField(
        verbose_name='Imagen de perfil',
        upload_to='deteccion/users/',
        max_length=1024,
        blank=True,
        null=True
    )
    
    email = models.EmailField('Email', unique=True)
    direction = models.CharField('Dirección', max_length=200, blank=True, null=True)
    phone = models.CharField('Teléfono', max_length=50, blank=True, null=True)
  
 
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        permissions = (
            ("change_userprofile", "Cambiar perfil de Usuario"),
            ("change_userpassword", "Cambiar contraseña de Usuario"),
        )
            
    @property
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_groups(self):
        return self.groups.all()

    def get_short_name(self):
        return self.username

    def get_group_session(self):
        request = get_current_request()
        print("request==>",request)
        return Group.objects.get(pk=request.session['group_id'])

    def set_group_session(self):
        request = get_current_request()

        if 'group' not in request.session:

            groups = request.user.groups.all().order_by('id')

            if groups.exists():
                request.session['group'] = groups.first()
                request.session['group_id'] = request.session['group'].id

    
    def get_image(self):
        if self.image:
            return self.image.url
        else:
            return '/static/img/usuario_anonimo.png'
# Create your models here.




class Alert(models.Model):
    LEVEL_CHOICES = (
        ('high', 'Alta'),
        ('medium', 'Media'),
        ('low', 'Baja'),
        ('positive', 'Positiva'),
    )
    
    RESOLUTION_CHOICES = (
        ('pending', 'Pendiente'),
        ('resolved', 'Resuelto'),
        ('false_positive', 'Falsa Alerta'),
        ('non_compliant', 'Incumplimiento Real'),
        ('system_error', 'Error del Sistema'),
    )

    message = models.CharField(max_length=255)
    missing = models.CharField(max_length=255, blank=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='high')
    video = models.FileField(upload_to='', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    
    # ✅ NUEVOS CAMPOS PARA RESOLUCIÓN
    resolution_status = models.CharField(
        max_length=20, 
        choices=RESOLUTION_CHOICES, 
        default='pending'
    )
    resolution_notes = models.TextField(blank=True, null=True)
    resolved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='resolved_alerts'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_level_display()} - {self.message} ({self.timestamp:%Y-%m-%d %H:%M:%S})"

    def mark_as_resolved(self, user, status='resolved', notes=''):
        """Marca la alerta como resuelta"""
        self.resolved = True
        self.resolution_status = status
        self.resolution_notes = notes
        self.resolved_by = user
        self.resolved_at = timezone.now()
        self.save()


class Cargo(models.Model):
    # Nombre del cargo (ej. administrador, supervisor, obrero, etc.)
    nombre = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nombre del Cargo",
        help_text="Ej.: administrador, supervisor, obrero "
    )

    # Descripción del cargo (opcional)
    descripcion = models.TextField(
        verbose_name="Descripción del Cargo",
        null=True,
        blank=True,
        help_text="Descripción breve del rol que cumple este cargo (opcional)."
    )

    activo = models.BooleanField(
        default=True,
        verbose_name="Activo",
        help_text="Desactiva este cargo si ya no se usa en el sistema."
    )

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Cargo"
        verbose_name_plural = "Cargos"
        ordering = ['nombre']  # Orden alfabético en listados del admin

# Modelo que representa a los empleados que trabajan en la clínica.
# Incluye información personal, profesional y datos de contacto.
class Empleado(models.Model):
    nombres = models.CharField(max_length=100, verbose_name="Nombre del Empleado")
    apellidos = models.CharField(max_length=100, verbose_name="Apellido del Empleado")
    user = models.OneToOneField(
        'User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Cuenta de Usuario"
    )
    cedula_ecuatoriana = models.CharField(
        max_length=10,
        verbose_name="Cédula",
        validators=[valida_cedula],
        help_text="Ingrese el número de cédula sin espacios ni guiones."
    )
    dni = models.CharField(
        max_length=30,
        verbose_name="Dni internacional",
        blank=True,
        null=True,
        validators=[RegexValidator(regex=r'^[A-Za-z0-9\-\. ]{5,30}$',
                                   message="Ingrese un documento válido (letras, números, guiones o puntos)."
                                   )],
        help_text="Pasaporte, DNI, CURP u otro documento válido internacionalmente."
    )
    fecha_nacimiento = models.DateField(verbose_name="Fecha de Nacimiento")
    
    cargo = models.ForeignKey('Cargo', on_delete=models.PROTECT, verbose_name="Cargo", related_name="cargos")
    sueldo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Sueldo")
    fecha_ingreso = models.DateField(verbose_name="Fecha de Ingreso")
    direccion = models.CharField(max_length=255, verbose_name="Dirección")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    @property
    def nombre_completo(self):
        return f"{self.apellidos} {self.nombres}"

    def __str__(self):
        return self.nombre_completo

    class Meta:
        ordering = ['apellidos', 'nombres']
        verbose_name = "Empleado"
        verbose_name_plural = "Empleados"


####capacitaciones
import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Capacitacion(models.Model):
    TIPO_CONTENIDO = [
        ('texto', 'Texto'),
        ('pdf', 'PDF'),
        ('video', 'Video'),
        ('imagen', 'Imagen'),
    ]

    ESTADO_CAPACITACION = [
        ('borrador', 'Borrador'),
        ('publicada', 'Publicada'),
        ('archivada', 'Archivada'),
    ]

    titulo = models.CharField(max_length=200, verbose_name="Título")
    descripcion = models.TextField(verbose_name="Descripción")
    tipo_contenido = models.CharField(max_length=10, choices=TIPO_CONTENIDO, verbose_name="Tipo de Contenido")
    contenido_texto = models.TextField(blank=True, null=True, verbose_name="Contenido Textual")
    archivo_pdf = models.FileField(upload_to='capacitaciones/pdf/', blank=True, null=True, verbose_name="Archivo PDF")
    archivo_imagen = models.ImageField(upload_to='capacitaciones/imagenes/', blank=True, null=True, verbose_name="Imagen")
    url_video = models.URLField(blank=True, null=True, verbose_name="URL de Video")
    duracion_minutos = models.IntegerField(default=30, verbose_name="Duración (minutos)", validators=[MinValueValidator(1)])
    estado = models.CharField(max_length=10, choices=ESTADO_CAPACITACION, default='borrador', verbose_name="Estado")
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='capacitaciones_creadas', verbose_name="Creado por")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Actualización")
    puntaje_minimo = models.IntegerField(default=70, verbose_name="Puntaje Mínimo para Aprobar", validators=[MinValueValidator(0), MaxValueValidator(100)])
    intentos_permitidos = models.IntegerField(default=3, verbose_name="Intentos Permitidos", validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = "Capacitación"
        verbose_name_plural = "Capacitaciones"
        ordering = ['-fecha_creacion']
        permissions = [
            ("can_publish_capacitacion", "Puede publicar capacitaciones"),
            ("can_create_evaluacion", "Puede crear evaluaciones"),
        ]

    def __str__(self):
        return self.titulo


class ProgresoCapacitacion(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Usuario")
    capacitacion = models.ForeignKey(Capacitacion, on_delete=models.CASCADE, verbose_name="Capacitación")
    completada = models.BooleanField(default=False, verbose_name="Completada")
    fecha_inicio = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Inicio")
    fecha_completacion = models.DateTimeField(blank=True, null=True, verbose_name="Fecha de Completación")
    progreso_porcentaje = models.IntegerField(default=0, verbose_name="Progreso (%)", validators=[MinValueValidator(0), MaxValueValidator(100)])

    class Meta:
        verbose_name = "Progreso de Capacitación"
        verbose_name_plural = "Progresos de Capacitaciones"
        unique_together = ['usuario', 'capacitacion']
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f"{self.usuario.get_full_name} - {self.capacitacion.titulo}"


class Evaluacion(models.Model):
    TIPO_PREGUNTA = [
        ('opcion_multiple', 'Opción Múltiple'),
        ('verdadero_falso', 'Verdadero/Falso'),
    ]

    capacitacion = models.OneToOneField(Capacitacion, on_delete=models.CASCADE, related_name='evaluacion', verbose_name="Capacitación")
    titulo = models.CharField(max_length=200, verbose_name="Título")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    activa = models.BooleanField(default=True, verbose_name="Activa")
    creada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Creada por")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")

    class Meta:
        verbose_name = "Evaluación"
        verbose_name_plural = "Evaluaciones"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return self.titulo


class Pregunta(models.Model):
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name='preguntas', verbose_name="Evaluación")
    texto = models.TextField(verbose_name="Texto de la Pregunta")
    tipo = models.CharField(max_length=20, choices=Evaluacion.TIPO_PREGUNTA, verbose_name="Tipo de Pregunta")
    puntaje = models.IntegerField(default=10, verbose_name="Puntaje", validators=[MinValueValidator(1)])
    orden = models.PositiveSmallIntegerField(default=0, verbose_name="Orden")

    class Meta:
        verbose_name = "Pregunta"
        verbose_name_plural = "Preguntas"
        ordering = ['orden', 'id']

    def __str__(self):
        return self.texto[:50]


class OpcionRespuesta(models.Model):
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name='opciones', verbose_name="Pregunta")
    texto = models.CharField(max_length=200, verbose_name="Texto de la Opción")
    es_correcta = models.BooleanField(default=False, verbose_name="¿Es Correcta?")
    orden = models.PositiveSmallIntegerField(default=0, verbose_name="Orden")

    class Meta:
        verbose_name = "Opción de Respuesta"
        verbose_name_plural = "Opciones de Respuesta"
        ordering = ['orden', 'id']

    def __str__(self):
        return f"{self.texto} ({'✔' if self.es_correcta else '✖'})"


class IntentoEvaluacion(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Usuario")
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, verbose_name="Evaluación")
    fecha_intento = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Intento")
    puntaje_obtenido = models.IntegerField(default=0, verbose_name="Puntaje Obtenido", validators=[MinValueValidator(0)])
    aprobado = models.BooleanField(default=False, verbose_name="Aprobado")
    numero_intento = models.IntegerField(default=1, verbose_name="Número de Intento")

    class Meta:
        verbose_name = "Intento de Evaluación"
        verbose_name_plural = "Intentos de Evaluación"
        ordering = ['-fecha_intento']

    def __str__(self):
        return f"{self.usuario.get_full_name} - {self.evaluacion.titulo} (Intento {self.numero_intento})"


class RespuestaUsuario(models.Model):
    intento = models.ForeignKey(IntentoEvaluacion, on_delete=models.CASCADE, related_name='respuestas', verbose_name="Intento")
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, verbose_name="Pregunta")
    opcion_seleccionada = models.ForeignKey(OpcionRespuesta, on_delete=models.CASCADE, verbose_name="Opción Seleccionada")

    class Meta:
        verbose_name = "Respuesta de Usuario"
        verbose_name_plural = "Respuestas de Usuarios"

    def __str__(self):
        return f"Resp. {self.intento.usuario.get_full_name} - {self.pregunta.id}"


class Certificado(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Usuario")
    capacitacion = models.ForeignKey(Capacitacion, on_delete=models.CASCADE, verbose_name="Capacitación")
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, verbose_name="Evaluación")
    fecha_emision = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Emisión")
    codigo_certificado = models.CharField(max_length=50, unique=True, verbose_name="Código de Certificado")
    puntaje_final = models.IntegerField(verbose_name="Puntaje Final")

    class Meta:
        verbose_name = "Certificado"
        verbose_name_plural = "Certificados"
        ordering = ['-fecha_emision']

    def save(self, *args, **kwargs):
        if not self.codigo_certificado:
            self.codigo_certificado = f"CERT-{self.usuario.id}-{self.capacitacion.id}-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Certificado {self.codigo_certificado} - {self.usuario.get_full_name}"

