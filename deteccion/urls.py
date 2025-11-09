# deteccion/urls.py
from django.urls import path
from . import views
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from . import views_admin_capacitaciones as admin_views
app_name = 'deteccion' # Define el namespace de la app

urlpatterns = [
    # URLs principales
    path('', lambda request: redirect('deteccion:login')),
    path('login/', views.login_vista, name='login'),
    path('inicio/', views.inicio, name='inicio'), 
    path('logout/', views.logout_view, name='logout'),

    # URLs para la cámara
    path('video_feed/', views.video_feed, name='video_feed'),
    path('toggle_camera/', views.toggle_camera, name='toggle_camera'),
    path('grabaciones/', views.grabaciones, name='grabaciones'),


##alertas
    path('inicio/alerts/', views.alert_list, name='alert_data'),
    path('inicio/alerts/list/', views.alert_list_page, name='alert_list'),
    path('inicio/latest-alerts/', views.latest_alerts, name='latest_alerts'),
    path('inicio/alerts/resolve/<int:alert_id>/', views.resolve_alert, name='resolve_alert'),
    path('inicio/alerts/statistics/', views.alert_statistics, name='alert_statistics'),
    path('inicio/alerts/modal/<int:alert_id>/', views.alert_resolution_modal, name='alert_resolution_modal'),
    
    path('inicio/incunplimiento/<int:incumplimiento_id>/', views.ver_incumplimiento, name='incunplimiento'),
##Cargo
    path('cargos/', views.CargoListView.as_view(), name='cargo_list'),
    path('cargos/new/', views.CargoCreateView.as_view(), name='cargo_create'),
    path('cargos/edit/<int:pk>/', views.CargoUpdateView.as_view(), name='cargo_update'),
    path('cargos/delete/<int:pk>/', views.CargoDeleteView.as_view(), name='cargo_delete'),

# URLs para Empleado
    path('inicio/empleados/', views.EmpleadoListView.as_view(), name='lista_empleados'),
    path('inicio/empleados/new/', views.EmpleadoCreateView.as_view(), name='crear_empleado'),
    path('inicio/empleados/edit/<int:pk>/', views.EmpleadoUpdateView.as_view(), name='empleado_editar'),
    path('inicio/empleados/delete/<int:pk>/', views.EmpleadoDeleteView.as_view(), name='empleado_eliminar'),

# URLs para Menu
    path('inicio/menus/', views.MenuListView.as_view(), name='menu_list'),
    path('inicio/create/', views.MenuCreateView.as_view(), name='menu_create'),
     path('inicio/edit/<int:pk>/', views.MenuUpdateView.as_view(), name='menu_editar'),
    path('inicio/delete/<int:pk>/', views.MenuDeleteView.as_view(), name='menu_eliminar'),


## URLs para Módulo
    path('inicio/modules/', views.ModuleListView.as_view(), name='module_list'),
    path('inicio/modules/create/',  views.ModuleCreateView.as_view(), name='module_create'),
    path('inicio/modules/update/<int:pk>/',  views.ModuleUpdateView.as_view(), name='module_update'),
    path('inicio/modules/delete/<int:pk>/',  views.ModuleDeleteView.as_view(), name='module_delete'),



## URLs para Usuario
    path('inicio/usuarios/crear/', views.usercreate, name='user_create'),
    path('inicio/usuarios/lista/', views.UserListView.as_view(), name='user_list'),
    path('inicio/usuarios/update/<int:pk>/',  views.user_edit, name='update_user'),
    path('inicio/usuarios/delete/<int:pk>/',  views.user_delete, name='user_delete'),
    path('inicio/usuarios/password/<int:pk>/',  views.user_change_password, name='user_password'),

 ## URLs para Cargo-Permiso
    path('inicio/cargopermiso/', views.GroupModulePermissionsView.as_view(), name='cargo_permiso_list'),
    path('inicio/cargopermiso/new/', views.GroupModulePermissionCreateView.as_view(), name='cargo_permiso_create'),
    path('inicio/cargopermiso/delete/<int:pk>/', views.GroupModulePermissionDeleteView.as_view(), name='cargo_permiso_delete'),
    path('inicio/cargopermiso/edit/<int:pk>/', views.GroupModulePermissionUpdateView.as_view(), name='cargo_permiso_edit'),


    # URL de Creación de Usuarios (usando tu vista basada en función)
    path('usuarios/crear/', views.usercreate, name='user_create'),

##capacitaciones
   path('inicio_trabajador/', views.inicio_trabajador, name='inicio_trabajador'),
   path('inicio/capacitaciones/dashboard/', admin_views.dashboard_admin_capacitaciones, name='dashboard_admin_capacitaciones'),
    
    # Gestión de capacitaciones
    path('inicio/admin/capacitaciones/', admin_views.lista_capacitaciones_admin, name='lista_capacitaciones_admin'),
    path('inicio/admin/capacitaciones/crear/', admin_views.crear_capacitacion, name='crear_capacitacion'),
    path('inicio/admin/capacitaciones/<int:capacitacion_id>/editar/', admin_views.editar_capacitacion, name='editar_capacitacion'),
    path('inicio/admin/capacitaciones/<int:capacitacion_id>/cambiar-estado/', admin_views.cambiar_estado_capacitacion, name='cambiar_estado_capacitacion'),
    
    # Gestión de evaluaciones
    path('inicio/admin/capacitaciones/<int:capacitacion_id>/evaluacion/', admin_views.gestionar_evaluacion, name='gestionar_evaluacion'),
    path('inicio/admin/evaluaciones/<int:evaluacion_id>/preguntas/', admin_views.gestionar_preguntas, name='gestionar_preguntas'),
    path('inicio/admin/preguntas/<int:pregunta_id>/eliminar/', admin_views.eliminar_pregunta, name='eliminar_pregunta'),
    path('inicio/admin/opciones/<int:opcion_id>/eliminar/', admin_views.eliminar_opcion, name='eliminar_opcion'),
    
    # Reportes y seguimiento
    path('inicio/admin/reportes/progreso/', admin_views.reporte_progreso_general, name='reporte_progreso_general'),
    path('inicio/admin/reportes/progreso/exportar/', admin_views.exportar_reporte_progreso, name='exportar_reporte_progreso'),
    path('inicio/admin/reportes/progreso/<int:usuario_id>/', admin_views.detalle_progreso_trabajador, name='detalle_progreso_trabajador'),
    path('inicio/admin/reportes/capacitacion/<int:capacitacion_id>/', admin_views.reporte_capacitacion_detalle, name='reporte_capacitacion_detalle'),
    
    path('inicio/detalle/capacitaciones/<int:pk>/', admin_views.detalle_capacitacion, name='detalle_capacitacion'),
    path('capacitacion/<int:capacitacion_id>/actualizar-progreso/', admin_views.actualizar_progreso, name='actualizar_progreso'),
    # Alternativa con clase-based view
    path('capacitacion/<int:capacitacion_id>/progreso/', admin_views.ActualizarProgresoView.as_view(),name='actualizar_progreso_cbv'),
    path('inicio_trabajador/', admin_views.inicio_trabajador, name='inicio_trabajador'),
    path('inicio/detalle/capacitaciones/<int:pk>/', admin_views.detalle_capacitacion, name='detalle_capacitacion'),
    path('capacitaciones/iniciar/<int:capacitacion_id>/', admin_views.iniciar_capacitacion, name='iniciar_capacitacion'),




]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)