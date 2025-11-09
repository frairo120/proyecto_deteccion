# deteccion/views.py
from django.shortcuts import render, redirect
from django.http import StreamingHttpResponse, JsonResponse
from django.db.models import Q
from .camera import VideoCamera
from .droidcam import DroidCamera
import json
# Global camera instance
camera = None  # Se inicializará cuando se seleccione el tipo de cámara
from django.urls import reverse_lazy,reverse
from django.contrib import messages
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

# Importar Modelos y Forms
from .models import Menu, Module, Cargo, Empleado, GroupModulePermission,User, Alert
from .forms import MenuForm, ModuleForm, CargoForm, EmpleadoForm, LoginForm, GroupForm, GroupModulePermissionForm
from .forms import UserForm,UserEditForm,UserPasswordChangeForm
from django.db.models import Prefetch
import os
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import localtime
from django.db import models
from .models import Capacitacion, ProgresoCapacitacion, Certificado

class MenuContextMixin:
    """Mixin para agregar el contexto de menús y módulos a las vistas."""
    def get_menu_context(self, user):
        """Obtiene los menús y módulos permitidos para el usuario."""
        if not user.is_authenticated:
            return []
        
        # Obtener todos los menús
        menus = Menu.objects.prefetch_related(
            Prefetch(
                'modules',
                queryset=Module.objects.filter(is_active=True),
                to_attr='active_modules'
            )
        ).all()

        menu_list = []
        for menu in menus:
            # Filtrar módulos por permisos del usuario
            group_module_permissions = GroupModulePermission.objects.filter(
                module__menu=menu,
                module__is_active=True,
                group__in=user.groups.all()
            ).select_related('module').distinct()
            
            if group_module_permissions.exists():
                menu_list.append({
                    'menu': menu,
                    'group_module_permission_list': group_module_permissions
                })
        
        return menu_list

# ----------------------------------------------------
# 1. Vistas de Autenticación
# ----------------------------------------------------

def login_vista(request):
    """Maneja el inicio de sesión de usuarios."""
    if request.method == 'POST':
        form = LoginForm(request.POST) 
        if form.is_valid():
            # Nota: Si USERNAME_FIELD es 'email', Django intentará autenticar usando el email 
            # si el campo 'username' del formulario es el que contiene el email.
            username = form.cleaned_data.get('username') 
            password = form.cleaned_data.get('password')
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                # Asegúrate de que 'inicio' esté definido en tus urls principales.
                return redirect('deteccion:inicio')  
            else:
                messages.error(request, 'Credenciales inválidas. Inténtalo de nuevo.')
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})

@login_required
def inicio(request):
    """Vista principal o inicio después del login."""
    if request.user.groups.filter(name='trabajador').exists():
        return redirect('deteccion:inicio_trabajador')
    # Obtener el contexto de menús para el usuario actual
    menu_context = MenuContextMixin().get_menu_context(request.user)
    # Obtener las últimas alertas (las 6 más recientes)
    try:
        # Forzar evaluación aquí para atrapar errores de DB (p. ej. tabla no existe)
        latest_alerts = list(Alert.objects.filter(resolved=False).order_by('-timestamp')[:6])
    except Exception:
        latest_alerts = []

    return render(request, 'inicio.html', {'menu_list': menu_context, 'alerts': latest_alerts})



@login_required
def inicio_trabajador(request):
    """Vista exclusiva para trabajadores - Panel de capacitación"""
    # Verificar que realmente sea trabajador
    if not request.user.groups.filter(name='trabajador').exists():
        return redirect('deteccion:inicio')
    
    # Obtener capacitaciones publicadas
    capacitaciones = Capacitacion.objects.filter(estado='publicada')
    
    # Obtener progreso del usuario actual
    progresos = ProgresoCapacitacion.objects.filter(usuario=request.user).select_related('capacitacion')
    
    # Obtener certificados del usuario actual
    certificados = Certificado.objects.filter(usuario=request.user).select_related('capacitacion')
    
    # Calcular estadísticas
    capacitaciones_completadas = progresos.filter(completada=True).count()
    total_capacitaciones = capacitaciones.count()
    
    # Calcular porcentaje de progreso
    if total_capacitaciones > 0:
        porcentaje_progreso = (capacitaciones_completadas / total_capacitaciones) * 100
    else:
        porcentaje_progreso = 0
    
    # Preparar datos para el template - solución sin filtros
    capacitaciones_con_progreso = []
    for capacitacion in capacitaciones:
        progreso_capacitacion = next(
            (p for p in progresos if p.capacitacion.id == capacitacion.id), 
            None
        )
        capacitaciones_con_progreso.append({
            'capacitacion': capacitacion,
            'progreso': progreso_capacitacion
        })
    
    context = {
        'user': request.user,
        'capacitaciones_con_progreso': capacitaciones_con_progreso,  # Nuevo formato
        'progresos': progresos,
        'certificados': certificados,
        'capacitaciones_completadas': capacitaciones_completadas,
        'total_capacitaciones': total_capacitaciones,
        'porcentaje_progreso': porcentaje_progreso,
        'current_date': timezone.now(),
    }
    return render(request, 'inicio_trabajador.html', context)

def logout_view(request):
    """Cierra la sesión del usuario y redirige al login."""
    logout(request)
    # Redirige a la vista de login (debes asegurar que esta URL funcione).
    return redirect('deteccion:login') 

def grabaciones(request):
    """Muestra la página con el listado de grabaciones."""
    return render(request, 'deteccion/grabaciones.html')







@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff, login_url='/')
def usercreate(request):
    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'El usuario {user.get_full_name} ha sido creado exitosamente.')
            return redirect('deteccion:user_list') 
        else:
            messages.error(request, 'Error al crear el usuario. Por favor, revise los campos.')
    else:
        form = UserForm()

    context = {
        'form': form,
        'title': 'Crear Nuevo Usuario',
    }
    return render(request, 'usuarios/crear_usuario.html', context)


# Vista para editar usuario
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Usuario {user.get_full_name} actualizado correctamente.')
            return redirect('deteccion:user_list')
        else:
            messages.error(request, 'Error al actualizar el usuario. Por favor, revise los campos.')
    else:
        form = UserEditForm(instance=user)

    context = {
        'form': form,
        'title': f'Editar Usuario: {user.username}',
    }
    return render(request, 'usuarios/update.html', context)


# Vista para cambiar contraseña
def user_change_password(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserPasswordChangeForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Contraseña de {user.get_full_name()} actualizada correctamente.')
            return redirect('usuarios:user_list')
        else:
            messages.error(request, 'Error al cambiar la contraseña. Por favor, revise los campos.')
    else:
        form = UserPasswordChangeForm(user)

    context = {
        'form': form,
        'title': f'Cambiar Contraseña: {user.username}',
    }
    return render(request, 'usuarios/cambiar_contrasena.html', context)


# Vista para listar usuarios (ya la tenías, pero agrego test_func correctamente)
class UserListView(LoginRequiredMixin, ListView):
    model = User 
    template_name = 'usuarios/list.html'
    context_object_name = 'object_list'

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

    def get_queryset(self):
        return User.objects.all().prefetch_related('groups').order_by('id')

def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        full_name = user.get_full_name  # sin paréntesis
        user.delete()
        messages.success(request, f'El usuario {full_name} ha sido eliminado exitosamente.')
        return redirect('deteccion:user_list')

    context = {
        'user': user,
        'title': f'Eliminar Usuario: {user.username}',
    }
    return render(request, 'usuarios/delete.html', context)








# ----------------------------------------------------
# 2. Vistas para el modelo Cargo (CRUD)
# ----------------------------------------------------

class CargoListView(LoginRequiredMixin, ListView):
    model = Cargo
    template_name = 'deteccion/cargo_list.html'
    context_object_name = 'cargos'

class CargoCreateView(LoginRequiredMixin, CreateView):
    model = Cargo
    form_class = CargoForm
    template_name = 'deteccion/cargo_form.html'
    success_url = reverse_lazy('deteccion:cargo_list')

class CargoUpdateView(LoginRequiredMixin, UpdateView):
    model = Cargo
    form_class = CargoForm
    template_name = 'deteccion/cargo_form.html'
    success_url = reverse_lazy('deteccion:cargo_list')

class CargoDeleteView(LoginRequiredMixin, DeleteView):
    model = Cargo
    template_name = 'deteccion/cargo_confirm_delete.html'
    success_url = reverse_lazy('deteccion:cargo_list')

# ----------------------------------------------------
# 3. Vistas para el modelo Empleado (CRUD)
# ----------------------------------------------------

class EmpleadoListView(LoginRequiredMixin, ListView):
    model = Empleado
    template_name = 'empleados/lista_empleados.html'
    context_object_name = 'empleados'

class EmpleadoCreateView(LoginRequiredMixin, CreateView):
    model = Empleado
    form_class = EmpleadoForm
    template_name = 'empleados/crear_empleado.html'
    success_url = reverse_lazy('deteccion:lista_empleados')

class EmpleadoUpdateView(LoginRequiredMixin, UpdateView):
    model = Empleado
    form_class = EmpleadoForm
    template_name = 'empleados/empleado_editar.html'
    success_url = reverse_lazy('deteccion:lista_empleados')

class EmpleadoDeleteView(LoginRequiredMixin, DeleteView):
    model = Empleado
    template_name = 'empleados/empleado_eliminar.html'
    success_url = reverse_lazy('deteccion:lista_empleados')

# ----------------------------------------------------
# 4. Vistas para Menu y Module (Lista simple)
# ----------------------------------------------------
class ModuleListView(LoginRequiredMixin, ListView):
    model = Module
    template_name = 'deteccion/module_list.html'
    context_object_name = 'modulos'


# ----------------------------------------------------
# Funciones para la cámara
def gen_frames():
    global camera
    while True:
        if camera:
            frame = camera.get_frame()
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

def video_feed(request):
    return StreamingHttpResponse(gen_frames(),
                               content_type='multipart/x-mixed-replace; boundary=frame')

def toggle_camera(request):
    global camera
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        camera_type = data.get('camera_type', 'pc')  # pc o droidcam
        
        if camera_type == 'droidcam':
            ip = data.get('ip', '192.168.1.100')
            port = data.get('port', '4747')
        
        # Si hay una cámara activa y es de diferente tipo, la detenemos
        if camera and ((camera_type == 'pc' and not isinstance(camera, VideoCamera)) or 
                      (camera_type == 'droidcam' and not isinstance(camera, DroidCamera))):
            camera.stop()
            camera = None
        
        if action == 'start':
            if not camera:
                if camera_type == 'droidcam':
                    camera = DroidCamera(ip_address=ip, port=port)
                else:
                    camera = VideoCamera()
            camera.start()
            return JsonResponse({'status': 'started', 'camera_type': camera_type})
            
        elif action == 'stop':
            if camera:
                camera.stop()
                camera = None
            return JsonResponse({'status': 'stopped'})
            
    return JsonResponse({'status': 'error'}, status=400)
# ----------------------------------------------------


# ----------------------------------------------------
# 4. Vistas para Menu (Lista simple)
# ----------------------------------------------------
# ✅ CREAR MENÚ
class MenuListView(LoginRequiredMixin, ListView):
    model = Menu
    template_name = 'menu/menu_list.html'
    context_object_name = 'menus'

    def get_queryset(self):
        query = self.request.GET.get('q')
        queryset = Menu.objects.all()
        if query:
            queryset = queryset.filter(name__icontains=query)
        return queryset.order_by('order', 'name')


class MenuCreateView(LoginRequiredMixin, CreateView):
    model = Menu
    form_class = MenuForm
    template_name = 'menu/menu_form.html'
    success_url = reverse_lazy('menu:menu_list')

    def form_valid(self, form):
        messages.success(self.request, f"Menú '{form.instance.name}' creado exitosamente.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Por favor, corrija los errores del formulario.")
        return super().form_invalid(form)


# ✅ EDITAR MENÚ
class MenuUpdateView(LoginRequiredMixin, UpdateView):
    model = Menu
    form_class = MenuForm
    template_name = 'menu/menu_form.html'
    success_url = reverse_lazy('menu:menu_list')

    def form_valid(self, form):
        messages.success(self.request, f"Menú '{form.instance.name}' actualizado correctamente.")
        return super().form_valid(form)


# ✅ ELIMINAR MENÚ
class MenuDeleteView(LoginRequiredMixin, DeleteView):
    model = Menu
    template_name = 'menu/delete.html'
    success_url = reverse_lazy('menu:menu_list')

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(self.request, f"Menú '{obj.name}' eliminado exitosamente.")
        return super().delete(request, *args, **kwargs)
    
# ----------------------------------------------------
# 4. Vistas para Module (Lista simple)
# ----------------------------------------------------

class ModuleListView(LoginRequiredMixin, ListView):
    template_name = 'modulo/list.html'
    model = Module
    context_object_name = 'modules'
    permission_required = 'view_module'

    def get_queryset(self):
        # Inicializamos la query vacía
        query = Q()

        # Filtro de búsqueda por nombre o menú
        search = self.request.GET.get('q')
        if search:
            query |= Q(name__icontains=search)
            query |= Q(menu__name__icontains=search)

        # Filtro por estado activo
        active = self.request.GET.get('is_active')
        if active in ['true', 'True', '1']:
            query &= Q(is_active=True)
        elif active in ['false', 'False', '0']:
            query &= Q(is_active=False)

        return self.model.objects.filter(query).order_by('menu', 'order', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_url'] = reverse_lazy('security:module_create')
        # Opcional: mantener filtros en el template
        context['search'] = self.request.GET.get('q', '')
        context['is_active'] = self.request.GET.get('is_active', '')
        return context


class ModuleCreateView(LoginRequiredMixin, CreateView):
    model = Module
    template_name = 'modulo/form.html'
    form_class = ModuleForm
    success_url = reverse_lazy('deteccion:module_list')
    permission_required = 'add_module'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['grabar'] = 'Grabar Módulo'
        context['back_url'] = self.success_url
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        module = self.object
        messages.success(self.request, f"Éxito al crear el módulo {module.name}.")
        return response


class ModuleUpdateView(LoginRequiredMixin, UpdateView):
    model = Module
    template_name = 'modulo/form.html'
    form_class = ModuleForm
    success_url = reverse_lazy('deteccion:module_list')
    permission_required = 'change_module'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['grabar'] = 'Actualizar Módulo'
        context['back_url'] = self.success_url
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        module = self.object
        messages.success(self.request, f"Éxito al actualizar el módulo {module.name}.")
        return response


class ModuleDeleteView(LoginRequiredMixin, DeleteView):
    model = Module
    template_name = 'modulo/delete.html'
    success_url = reverse_lazy('deteccion:module_list')
    permission_required = 'delete_module'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['grabar'] = 'Eliminar Módulo'
        context['description'] = f"¿Desea eliminar el módulo: {self.object.name}?"
        context['back_url'] = self.success_url
        return context

    
    def form_valid(self, form):
        # Guardar info antes de eliminar
        module_name = self.object.name
        
        # Llamar al delete del padre
        response = super().form_valid(form)
        
        # Agregar mensaje
        messages.success(self.request, f"Éxito al eliminar lógicamente el módulo {module_name}.")
        
        return response
    
# ----------------------------------------------------
# 5. Vistas para GroupModulePermission (CRUD)
from django.views.generic import ListView
from django.contrib.auth.models import Group

class GroupModulePermissionsView(ListView):
    model = Group
    template_name = 'grouppermisos/list.html'
    context_object_name = 'groups'

    def get_queryset(self):
        # Optimización: Prefetch para reducir consultas a la DB
        return Group.objects.prefetch_related(
            'module_permissions__module',
            'module_permissions__permissions__content_type'
        ).all()
    


# ✅ LISTAR PERMISOS DE GRUPO POR MÓDULO
class GroupModulePermissionsView(LoginRequiredMixin, ListView):
    model = Group
    template_name = 'grouppermisos/list.html'
    context_object_name = 'groups'

    def get_queryset(self):
        return Group.objects.prefetch_related(
            'module_permissions__module',
            'module_permissions__permissions__content_type'
        ).all()


# ✅ CREAR PERMISOS PARA UN GRUPO
class GroupModulePermissionCreateView(LoginRequiredMixin, CreateView):
    model = GroupModulePermission
    form_class = GroupModulePermissionForm
    template_name = 'grouppermisos/form.html'
    success_url = reverse_lazy('deteccion:cargo_permiso_list')

    def form_valid(self, form):
        messages.success(self.request, "Permisos asignados correctamente al grupo.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Por favor, corrija los errores del formulario.")
        return super().form_invalid(form)


# ✅ EDITAR PERMISOS DE UN GRUPO
class GroupModulePermissionUpdateView(LoginRequiredMixin, UpdateView):
    model = GroupModulePermission
    form_class = GroupModulePermissionForm
    template_name = 'grouppermisos/form.html'
    success_url = reverse_lazy('deteccion:cargo_permiso_list')

    def form_valid(self, form):
        messages.success(self.request, "Permisos actualizados correctamente.")
        return super().form_valid(form)


# ✅ ELIMINAR PERMISOS DE UN GRUPO
class GroupModulePermissionDeleteView(LoginRequiredMixin, DeleteView):
    model = GroupModulePermission
    template_name = 'grouppermisos/delete.html'
    success_url = reverse_lazy('deteccion:cargo_permiso_list')

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(self.request, f"Permisos del grupo '{obj.group.name}' eliminados correctamente.")
        return super().delete(request, *args, **kwargs)











from django.db import transaction
from django.views.generic import TemplateView
from deteccion.models import Group,Permission

class GroupListView(LoginRequiredMixin, ListView):
    template_name = 'security/groups/list.html'
    model = Group
    context_object_name = 'groups'
    permission_required = 'view_group'

    def get_queryset(self):
        q1 = self.request.GET.get('q')
        if q1 is not None:
            self.query.add(Q(name__icontains=q1), Q.OR)
            
        return self.model.objects.prefetch_related(
            'permissions',
            'module_permissions__module',
            'module_permissions__permissions',
        ).filter(self.query).order_by('id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_url'] = reverse_lazy('security:group_create')
        context['all_permissions'] = Permission.objects.select_related('content_type').all()
        return context


class GroupCreateView(LoginRequiredMixin, CreateView):
    model = Group
    template_name = 'security/groups/form.html'
    form_class = GroupForm
    success_url = reverse_lazy('security:group_list')
    permission_required = 'add_group'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['grabar'] = 'Grabar Módulo'
        context['back_url'] = self.success_url
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        group = self.object
        messages.success(self.request, f"Éxito al crear el módulo {group.name}.")
        return response


class GroupUpdateView(LoginRequiredMixin, UpdateView):
    model = Group
    template_name = 'security/groups/form.html'
    form_class = GroupForm
    success_url = reverse_lazy('security:group_list')
    permission_required = 'change_group'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['grabar'] = 'Actualizar Módulo'
        context['back_url'] = self.success_url
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        group = self.object
        messages.success(self.request, f"Éxito al actualizar el módulo {group.name}.")
        return response


class GroupDeleteView(LoginRequiredMixin, DeleteView):
    model = Group
    template_name = 'core/delete.html'
    success_url = reverse_lazy('security:group_list')
    permission_required = 'delete_group'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['grabar'] = 'Eliminar Módulo'
        context['description'] = f"¿Desea eliminar el módulo: {self.object.name}?"
        context['back_url'] = self.success_url
        return context

    
    def form_valid(self, form):
        # Guardar info antes de eliminar
        group_name = self.object.name
        
        # Llamar al delete del padre
        response = super().form_valid(form)
        
        # Agregar mensaje
        messages.success(self.request, f"Éxito al eliminar lógicamente el módulo {group_name}.")
        
        return response
    
    
from django.shortcuts import get_object_or_404, redirect
from deteccion.models import GroupModulePermission

def update_group_permissions(request, group_id):
    if request.method == 'POST':
        for key in request.POST:
            if key.startswith('permissions_'):
                module_id = key.split('_')[1]
                permission_ids = request.POST.getlist(key)
                try:
                    gm = GroupModulePermission.objects.get(group_id=group_id, module_id=module_id)
                    gm.permissions.set(permission_ids)
                except GroupModulePermission.DoesNotExist:
                    continue
        return redirect('security:group_list')  # Ajusta si usas otro nombre de vista



class GroupPermissionsView(TemplateView):
    template_name = 'security/group_permissions.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = get_object_or_404(Group, pk=self.kwargs['pk'])
        context['group'] = group
        context['title1'] = f"Gestionar Permisos - {group.name}"
        
        # Organizar permisos por categoría (app_label)
        permissions = Permission.objects.all().order_by('content_type__app_label', 'name')
        grouped_permissions = {}
        
        for perm in permissions:
            app_label = perm.content_type.app_label
            if app_label not in grouped_permissions:
                grouped_permissions[app_label] = []
            grouped_permissions[app_label].append(perm)
            
        context['grouped_permissions'] = grouped_permissions
        context['current_permissions'] = set(group.permissions.all().values_list('id', flat=True))
        
        return context
    
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, pk=self.kwargs['pk'])
        selected_permissions = request.POST.getlist('permissions')
        
        try:
            with transaction.atomic():
                # Limpiar permisos actuales
                group.permissions.clear()
                
                # Agregar nuevos permisos seleccionados
                if selected_permissions:
                    permissions = Permission.objects.filter(id__in=selected_permissions)
                    group.permissions.add(*permissions)
                
                messages.success(request, 'Permisos actualizados correctamente.')
                return redirect('security:group_list')
                
        except Exception as e:
            messages.error(request, f'Error al actualizar permisos: {str(e)}')
            return redirect('security:group_permissions', pk=group.id)
        



import boto3
from django.shortcuts import render, get_object_or_404
from datetime import timedelta

# Asegúrate de tener tu modelo de Incumplimiento que apunta a Cloud Storage
# from .models import Incumplimiento # (Asumiendo que tienes un modelo similar)
BUCKET_NAME = 'mi-bucket-local' # 👈 Cambia este nombre al de tu bucket en LocalStack
LOCALSTACK_ENDPOINT = 'http://localhost:4566' 

def ver_incumplimiento(request, incumplimiento_id):
    """Muestra detalles del incumplimiento - para archivos locales"""
    incumplimiento = get_object_or_404(Alert, pk=incumplimiento_id)
    
    image_url = None
    debug_info = ""
    
    if incumplimiento.video:
        # Obtener la ruta guardada en la BD
        db_path = incumplimiento.video.name
        debug_info = f"Ruta en BD: {db_path}"
        
        print(f"🔍 Buscando imagen para alerta {incumplimiento_id}: {db_path}")
        
        # Construir ruta local completa
        local_path = os.path.join('media', db_path)
        
        # Verificar si el archivo existe localmente
        if os.path.exists(local_path):
            # Usar la URL de medios de Django
            image_url = f"/media/{db_path}"
            print(f"✅ Imagen encontrada: {image_url}")
            debug_info += f" | Encontrada en: {local_path}"
        else:
            print(f"❌ Archivo NO encontrado: {local_path}")
            debug_info += f" | NO encontrada en: {local_path}"
            
            # ✅ CORRECCIÓN: Llamar a la función directamente, no con self
            alternative_paths = find_alternative_image(incumplimiento_id, db_path)
            if alternative_paths:
                image_url = alternative_paths[0]
                print(f"✅ Imagen alternativa encontrada: {image_url}")
    
    context = {
        'incumplimiento': incumplimiento,
        'image_url': image_url,
        'debug_info': debug_info,
        'title': f'Incumplimiento ID: {incumplimiento_id}'
    }
    
    return render(request, 'usuarios/ver_incumplimiento.html', context)

# ✅ CORRECCIÓN: Quitar el parámetro self
def find_alternative_image(alert_id, original_path):
    """Busca imágenes alternativas si la original no se encuentra"""
    alertas_dir = 'media/alertas'
    if not os.path.exists(alertas_dir):
        return []
    
    # Buscar cualquier imagen que pueda corresponder a esta alerta
    possible_files = []
    for filename in os.listdir(alertas_dir):
        if filename.endswith('.jpg') and str(alert_id) in filename:
            possible_files.append(f"/media/alertas/{filename}")
    
    return possible_files


def alert_list(request):
    # Obtenemos alertas no resueltas de las últimas 24 horas
    since = timezone.now() - timedelta(hours=24)
    alerts = Alert.objects.filter(timestamp__gte=since, resolved=False).order_by('-timestamp')
    
    data = []
    for alert in alerts:
        data.append({
            'id': alert.id,
            'message': alert.message,
            'missing': alert.missing,
            'level': alert.get_level_display(),
            'video_url': alert.video.url if alert.video else '',
            'timestamp': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'resolved': alert.resolved,
            'resolution_status': alert.resolution_status,  # ✅ Nuevo campo
            'resolved_at': alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if alert.resolved_at else None,  # ✅ Nuevo campo
        })
    
    return JsonResponse({'alerts': data})


def alert_list_page(request):
    context = {}
    menu_context = MenuContextMixin().get_menu_context(request.user)
    context['menu_list'] = menu_context
    context['title'] = "Alertas Activas"
    return render(request, 'usuarios/alert_list.html', context)





def latest_alerts(request):
    # Filtrar alertas de las últimas 24 horas y ordenar por las más recientes
    time_threshold = timezone.now() - timedelta(hours=24)
    
    alerts = Alert.objects.filter(
        timestamp__gte=time_threshold
    ).order_by('-timestamp')[:10]  # Solo las 10 más recientes

    alert_data = []
    for a in alerts:
        # Procesar elementos faltantes del campo 'missing'
        missing_elements = []
        if a.missing:
            missing_elements = [elemento.strip() for elemento in a.missing.split(',')]
        
        alert_data.append({
            'id': a.pk,
            'message': a.message,
            'missing_elements': missing_elements,
            'timestamp': localtime(a.timestamp).strftime("%H:%M:%S %d-%m-%Y"), 
            'video': a.video.url if a.video else None, 
            'level': a.level,
            'element_count': len(missing_elements),
            'resolved': a.resolved,  # ✅ Agregar estado de resolución
            'resolution_status': a.resolution_status or 'pending',  # ✅ Estado de resolución
        })
    
    return JsonResponse({"alerts": alert_data})
 
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
import json

@login_required
@require_POST
def resolve_alert(request, alert_id):
    """Marca una alerta como resuelta permitiendo cambiar el nivel"""
    alert = get_object_or_404(Alert, pk=alert_id)
    
    try:
        data = json.loads(request.body)
        resolution_status = data.get('resolution_status', 'resolved')
        resolution_notes = data.get('resolution_notes', '')
        new_level = data.get('new_level')  # ✅ NUEVO: Campo para cambiar nivel
        
        # Validar el estado de resolución
        valid_statuses = ['resolved', 'false_positive', 'non_compliant', 'system_error']
        if resolution_status not in valid_statuses:
            return JsonResponse({
                'success': False, 
                'error': 'Estado de resolución inválido'
            }, status=400)
        
        # ✅ NUEVO: Validar y actualizar el nivel si se proporciona
        valid_levels = ['high', 'medium', 'low', 'positive']
        if new_level and new_level in valid_levels:
            alert.level = new_level
            level_updated = True
        else:
            level_updated = False
        
        # Marcar como resuelta
        alert.resolved = True
        alert.resolution_status = resolution_status
        alert.resolution_notes = resolution_notes
        alert.resolved_by = request.user
        alert.resolved_at = timezone.now()
        alert.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Alerta {alert_id} resuelta exitosamente',
            'alert_id': alert_id,
            'resolution_status': alert.resolution_status,
            'level_updated': level_updated,
            'new_level': alert.level if level_updated else None,
            'resolved_at': alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if alert.resolved_at else None
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def alert_statistics(request):
    """Obtiene estadísticas de las alertas"""
    # Alertas de las últimas 24 horas
    since = timezone.now() - timedelta(hours=24)
    
    total_alerts = Alert.objects.filter(timestamp__gte=since).count()
    unresolved_alerts = Alert.objects.filter(timestamp__gte=since, resolved=False).count()
    resolved_alerts = Alert.objects.filter(timestamp__gte=since, resolved=True).count()
    
    # Estadísticas por tipo de resolución
    resolution_stats = Alert.objects.filter(
        timestamp__gte=since, 
        resolved=True
    ).values('resolution_status').annotate(
        count=models.Count('id')
    )
    
    resolution_data = {stat['resolution_status']: stat['count'] for stat in resolution_stats}
    
    return JsonResponse({
        'total_alerts': total_alerts,
        'unresolved_alerts': unresolved_alerts,
        'resolved_alerts': resolved_alerts,
        'resolution_stats': resolution_data,
        'resolution_rate': (resolved_alerts / total_alerts * 100) if total_alerts > 0 else 0
    })

@login_required
def alert_resolution_modal(request, alert_id):
    """Devuelve el HTML del modal de resolución"""
    alert = get_object_or_404(Alert, pk=alert_id)
    
    context = {
        'alert': alert,
        'resolution_choices': Alert.RESOLUTION_CHOICES
    }
    
    return render(request, 'usuarios/resolution_modal.html', context)