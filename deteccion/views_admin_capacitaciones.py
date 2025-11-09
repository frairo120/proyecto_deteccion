# views_admin_capacitaciones.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q, Avg
from django.template.loader import render_to_string
import csv
from .models import *
from .forms import *

@login_required
@permission_required('deteccion.can_create_evaluacion', raise_exception=True)
def dashboard_admin_capacitaciones(request):
    """Dashboard principal para administradores/supervisores de capacitaciones"""
    # Estadísticas generales
    total_capacitaciones = Capacitacion.objects.count()
    capacitaciones_publicadas = Capacitacion.objects.filter(estado='publicada').count()
    total_trabajadores = User.objects.filter(groups__name='trabajador').count()
    
    # Progreso general de trabajadores
    trabajadores_con_progreso = ProgresoCapacitacion.objects.values('usuario').distinct().count()
    certificados_emitidos = Certificado.objects.count()
    
    # Capacitaciones recientes
    capacitaciones_recientes = Capacitacion.objects.all().order_by('-fecha_creacion')[:5]
    
    # Trabajadores con bajo progreso
    trabajadores_bajo_progreso = []
    trabajadores = User.objects.filter(groups__name='trabajador')
    
    for trabajador in trabajadores:
        progresos = ProgresoCapacitacion.objects.filter(usuario=trabajador)
        total_capacitaciones_trab = Capacitacion.objects.filter(estado='publicada').count()
        completadas = progresos.filter(completada=True).count()
        
        if total_capacitaciones_trab > 0:
            porcentaje = (completadas / total_capacitaciones_trab) * 100
            if porcentaje < 50:  # Menos del 50% de progreso
                trabajadores_bajo_progreso.append({
                    'trabajador': trabajador,
                    'completadas': completadas,
                    'total': total_capacitaciones_trab,
                    'porcentaje': porcentaje
                })
    
    context = {
        'total_capacitaciones': total_capacitaciones,
        'capacitaciones_publicadas': capacitaciones_publicadas,
        'total_trabajadores': total_trabajadores,
        'trabajadores_con_progreso': trabajadores_con_progreso,
        'certificados_emitidos': certificados_emitidos,
        'capacitaciones_recientes': capacitaciones_recientes,
        'trabajadores_bajo_progreso': trabajadores_bajo_progreso[:5],
    }
    return render(request, 'capacitacion/inicio_capacitaciones.html', context)

@login_required
@permission_required('deteccion.can_create_evaluacion', raise_exception=True)
def lista_capacitaciones_admin(request):
    """Lista todas las capacitaciones para administración"""
    capacitaciones = Capacitacion.objects.all().order_by('-fecha_creacion')
    
    # Agregar estadísticas a cada capacitación
    for capacitacion in capacitaciones:
        capacitacion.total_trabajadores = User.objects.filter(groups__name='trabajador').count()
        capacitacion.trabajadores_completados = ProgresoCapacitacion.objects.filter(
            capacitacion=capacitacion, completada=True
        ).count()
        capacitacion.porcentaje_completado = (
            (capacitacion.trabajadores_completados / capacitacion.total_trabajadores * 100) 
            if capacitacion.total_trabajadores > 0 else 0
        )
    
    context = {
        'capacitaciones': capacitaciones,
    }
    return render(request, 'capacitacion/inicio_capacitaciones.html', context)

@login_required
@permission_required('deteccion.can_create_evaluacion', raise_exception=True)
def crear_capacitacion(request):
    """Crear nueva capacitación"""
    if request.method == 'POST':
        form = CapacitacionForm(request.POST, request.FILES)
        if form.is_valid():
            capacitacion = form.save(commit=False)
            capacitacion.creado_por = request.user
            capacitacion.save()
            messages.success(request, 'Capacitación creada exitosamente')
            return redirect('deteccion:lista_capacitaciones_admin')
    else:
        form = CapacitacionForm()
    
    context = {
        'form': form,
        'titulo': 'Crear Nueva Capacitación',
    }
    return render(request, 'capacitacion/form_capacitacion.html', context)

@login_required
@permission_required('deteccion.can_create_evaluacion', raise_exception=True)
def editar_capacitacion(request, capacitacion_id):
    """Editar capacitación existente"""
    capacitacion = get_object_or_404(Capacitacion, id=capacitacion_id)
    
    if request.method == 'POST':
        form = CapacitacionForm(request.POST, request.FILES, instance=capacitacion)
        if form.is_valid():
            form.save()
            messages.success(request, 'Capacitación actualizada exitosamente')
            return redirect('deteccion:lista_capacitaciones_admin')
    else:
        form = CapacitacionForm(instance=capacitacion)
    
    context = {
        'form': form,
        'titulo': f'Editar Capacitación: {capacitacion.titulo}',
        'capacitacion': capacitacion,
    }
    return render(request, 'capacitacion/form_capacitacion.html', context)

@login_required
@permission_required('deteccion.can_create_evaluacion', raise_exception=True)
def cambiar_estado_capacitacion(request, capacitacion_id):
    """Cambiar estado de una capacitación (publicar/archivar)"""
    capacitacion = get_object_or_404(Capacitacion, id=capacitacion_id)
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in ['publicada', 'archivada', 'borrador']:
            capacitacion.estado = nuevo_estado
            capacitacion.save()
            messages.success(request, f'Capacitación {nuevo_estado} exitosamente')
    
    return redirect('deteccion:lista_capacitaciones_admin')

@login_required
@permission_required('deteccion.can_create_evaluacion', raise_exception=True)
def gestionar_evaluacion(request, capacitacion_id):
    """Gestionar evaluación de una capacitación"""
    capacitacion = get_object_or_404(Capacitacion, id=capacitacion_id)
    
    # Verificar si ya existe evaluación
    evaluacion = None
    if hasattr(capacitacion, 'evaluacion'):
        evaluacion = capacitacion.evaluacion
    
    if request.method == 'POST':
        if evaluacion:
            form = EvaluacionForm(request.POST, instance=evaluacion)
        else:
            form = EvaluacionForm(request.POST)
        
        if form.is_valid():
            evaluacion = form.save(commit=False)
            if not evaluacion.pk:  # Nueva evaluación
                evaluacion.capacitacion = capacitacion
                evaluacion.creada_por = request.user
            evaluacion.save()
            messages.success(request, 'Evaluación guardada exitosamente')
            return redirect('deteccion:gestionar_preguntas', evaluacion_id=evaluacion.id)
    else:
        if evaluacion:
            form = EvaluacionForm(instance=evaluacion)
        else:
            form = EvaluacionForm(initial={'titulo': f'Evaluación - {capacitacion.titulo}'})
    
    context = {
        'capacitacion': capacitacion,
        'evaluacion': evaluacion,
        'form': form,
    }
    return render(request, 'capacitacion/gestionar_evaluacion.html', context)

@login_required
@permission_required('deteccion.can_create_evaluacion', raise_exception=True)
def gestionar_preguntas(request, evaluacion_id):
    """Gestionar preguntas y opciones de una evaluación"""
    evaluacion = get_object_or_404(Evaluacion, id=evaluacion_id)
    preguntas = evaluacion.preguntas.all().prefetch_related('opciones').order_by('orden')
    
    if request.method == 'POST':
        # Procesar nueva pregunta
        if 'agregar_pregunta' in request.POST:
            pregunta_form = PreguntaForm(request.POST)
            if pregunta_form.is_valid():
                pregunta = pregunta_form.save(commit=False)
                pregunta.evaluacion = evaluacion
                pregunta.save()
                messages.success(request, 'Pregunta agregada exitosamente')
                return redirect('deteccion:gestionar_preguntas', evaluacion_id=evaluacion.id)
        
        # Procesar nueva opción
        elif 'agregar_opcion' in request.POST:
            pregunta_id = request.POST.get('pregunta_id')
            pregunta = get_object_or_404(Pregunta, id=pregunta_id, evaluacion=evaluacion)
            opcion_form = OpcionRespuestaForm(request.POST)
            if opcion_form.is_valid():
                opcion = opcion_form.save(commit=False)
                opcion.pregunta = pregunta
                opcion.save()
                messages.success(request, 'Opción agregada exitosamente')
                return redirect('deteccion:gestionar_preguntas', evaluacion_id=evaluacion.id)
    
    pregunta_form = PreguntaForm()
    opcion_form = OpcionRespuestaForm()
    
    context = {
        'evaluacion': evaluacion,
        'preguntas': preguntas,
        'pregunta_form': pregunta_form,
        'opcion_form': opcion_form,
    }
    return render(request, 'capacitacion/gestionar_preguntas.html', context)

@login_required
@permission_required('deteccion.can_create_evaluacion', raise_exception=True)
def eliminar_pregunta(request, pregunta_id):
    """Eliminar pregunta y sus opciones"""
    pregunta = get_object_or_404(Pregunta, id=pregunta_id)
    evaluacion_id = pregunta.evaluacion.id
    pregunta.delete()
    messages.success(request, 'Pregunta eliminada exitosamente')
    return redirect('deteccion:gestionar_preguntas', evaluacion_id=evaluacion_id)

@login_required
@permission_required('deteccion.can_create_evaluacion', raise_exception=True)
def eliminar_opcion(request, opcion_id):
    """Eliminar opción de respuesta"""
    opcion = get_object_or_404(OpcionRespuesta, id=opcion_id)
    evaluacion_id = opcion.pregunta.evaluacion.id
    opcion.delete()
    messages.success(request, 'Opción eliminada exitosamente')
    return redirect('deteccion:gestionar_preguntas', evaluacion_id=evaluacion_id)

@login_required
@permission_required('deteccion.can_create_evaluacion', raise_exception=True)
def reporte_progreso_general(request):
    """Reporte general de progreso de todos los trabajadores"""
    trabajadores = User.objects.filter(groups__name='trabajador')
    capacitaciones = Capacitacion.objects.filter(estado='publicada')
    
    datos_trabajadores = []
    
    for trabajador in trabajadores:
        progresos = ProgresoCapacitacion.objects.filter(usuario=trabajador)
        certificados = Certificado.objects.filter(usuario=trabajador)
        intentos = IntentoEvaluacion.objects.filter(usuario=trabajador)
        
        # Calcular estadísticas
        completadas = progresos.filter(completada=True).count()
        total_capacitaciones = capacitaciones.count()
        porcentaje_progreso = (completadas / total_capacitaciones * 100) if total_capacitaciones > 0 else 0
        
        # Evaluaciones aprobadas vs total
        evaluaciones_aprobadas = intentos.filter(aprobado=True).values('evaluacion').distinct().count()
        total_evaluaciones = Evaluacion.objects.filter(
            capacitacion__in=capacitaciones, 
            activa=True
        ).count()
        
        datos_trabajadores.append({
            'trabajador': trabajador,
            'progresos': progresos,
            'certificados': certificados,
            'intentos': intentos,
            'completadas': completadas,
            'total_capacitaciones': total_capacitaciones,
            'porcentaje_progreso': porcentaje_progreso,
            'evaluaciones_aprobadas': evaluaciones_aprobadas,
            'total_evaluaciones': total_evaluaciones,
            'estado': 'Cumpliendo' if porcentaje_progreso >= 70 else 'En riesgo' if porcentaje_progreso >= 30 else 'No cumpliendo'
        })
    
    # Ordenar por porcentaje de progreso (descendente)
    datos_trabajadores.sort(key=lambda x: x['porcentaje_progreso'], reverse=True)
    
    # Estadísticas generales
    total_trabajadores = len(datos_trabajadores)
    trabajadores_cumpliendo = len([t for t in datos_trabajadores if t['porcentaje_progreso'] >= 70])
    trabajadores_riesgo = len([t for t in datos_trabajadores if 30 <= t['porcentaje_progreso'] < 70])
    trabajadores_no_cumpliendo = len([t for t in datos_trabajadores if t['porcentaje_progreso'] < 30])
    
    context = {
        'datos_trabajadores': datos_trabajadores,
        'total_trabajadores': total_trabajadores,
        'trabajadores_cumpliendo': trabajadores_cumpliendo,
        'trabajadores_riesgo': trabajadores_riesgo,
        'trabajadores_no_cumpliendo': trabajadores_no_cumpliendo,
        'capacitaciones': capacitaciones,
    }
    return render(request, 'capacitacion/reporte_progreso_general.html', context)

@login_required
@permission_required('deteccion.can_create_evaluacion', raise_exception=True)
def exportar_reporte_progreso(request):
    """Exportar reporte de progreso a CSV"""
    trabajadores = User.objects.filter(groups__name='trabajador')
    capacitaciones = Capacitacion.objects.filter(estado='publicada')
    
    # Preparar datos
    datos_trabajadores = []
    for trabajador in trabajadores:
        progresos = ProgresoCapacitacion.objects.filter(usuario=trabajador)
        completadas = progresos.filter(completada=True).count()
        total_capacitaciones = capacitaciones.count()
        porcentaje_progreso = (completadas / total_capacitaciones * 100) if total_capacitaciones > 0 else 0
        
        datos_trabajadores.append({
            'trabajador': trabajador,
            'completadas': completadas,
            'total_capacitaciones': total_capacitaciones,
            'porcentaje_progreso': porcentaje_progreso,
            'estado': 'Cumpliendo' if porcentaje_progreso >= 70 else 'En riesgo' if porcentaje_progreso >= 30 else 'No cumpliendo'
        })
    
    # Crear respuesta CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="reporte_progreso_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['N°', 'TRABAJADOR', 'EMAIL', 'CAPACITACIONES COMPLETADAS', 'TOTAL CAPACITACIONES', 'PROGRESO (%)', 'ESTADO'])
    
    for i, dato in enumerate(datos_trabajadores, 1):
        writer.writerow([
            i,
            dato['trabajador'].get_full_name(),
            dato['trabajador'].email,
            dato['completadas'],
            dato['total_capacitaciones'],
            f"{dato['porcentaje_progreso']:.1f}%",
            dato['estado']
        ])
    
    return response

@login_required
@permission_required('deteccion.can_create_evaluacion', raise_exception=True)
def detalle_progreso_trabajador(request, usuario_id):
    """Detalle del progreso de un trabajador específico"""
    trabajador = get_object_or_404(User, id=usuario_id)
    
    if not trabajador.groups.filter(name='trabajador').exists():
        messages.error(request, 'El usuario seleccionado no es un trabajador.')
        return redirect('deteccion:reporte_progreso_general')
    
    capacitaciones = Capacitacion.objects.filter(estado='publicada')
    progresos = ProgresoCapacitacion.objects.filter(usuario=trabajador).select_related('capacitacion')
    certificados = Certificado.objects.filter(usuario=trabajador).select_related('capacitacion')
    intentos = IntentoEvaluacion.objects.filter(usuario=trabajador).select_related('evaluacion', 'evaluacion__capacitacion')
    
    # Estadísticas
    completadas = progresos.filter(completada=True).count()
    total_capacitaciones = capacitaciones.count()
    porcentaje_progreso = (completadas / total_capacitaciones * 100) if total_capacitaciones > 0 else 0
    
    # Progreso por capacitación
    progreso_detallado = []
    for capacitacion in capacitaciones:
        progreso = progresos.filter(capacitacion=capacitacion).first()
        certificado = certificados.filter(capacitacion=capacitacion).first()
        intento = intentos.filter(evaluacion__capacitacion=capacitacion).order_by('-fecha_intento').first()
        
        progreso_detallado.append({
            'capacitacion': capacitacion,
            'progreso': progreso,
            'certificado': certificado,
            'ultimo_intento': intento,
            'completada': progreso.completada if progreso else False,
            'tiene_evaluacion': hasattr(capacitacion, 'evaluacion') and capacitacion.evaluacion.activa,
        })
    
    context = {
        'trabajador': trabajador,
        'progreso_detallado': progreso_detallado,
        'certificados': certificados,
        'intentos': intentos,
        'completadas': completadas,
        'total_capacitaciones': total_capacitaciones,
        'porcentaje_progreso': porcentaje_progreso,
        'estado': 'Cumpliendo' if porcentaje_progreso >= 70 else 'En riesgo' if porcentaje_progreso >= 30 else 'No cumpliendo'
    }
    return render(request, 'capacitacion/detalle_progreso_trabajador.html', context)

@login_required
@permission_required('deteccion.can_create_evaluacion', raise_exception=True)
def reporte_capacitacion_detalle(request, capacitacion_id):
    """Reporte detallado de una capacitación específica"""
    capacitacion = get_object_or_404(Capacitacion, id=capacitacion_id)
    trabajadores = User.objects.filter(groups__name='trabajador')
    
    datos_trabajadores = []
    for trabajador in trabajadores:
        progreso = ProgresoCapacitacion.objects.filter(usuario=trabajador, capacitacion=capacitacion).first()
        certificado = Certificado.objects.filter(usuario=trabajador, capacitacion=capacitacion).first()
        intentos = IntentoEvaluacion.objects.filter(
            usuario=trabajador, 
            evaluacion__capacitacion=capacitacion
        ).order_by('-fecha_intento')
        
        datos_trabajadores.append({
            'trabajador': trabajador,
            'progreso': progreso,
            'certificado': certificado,
            'intentos': intentos,
            'ultimo_intento': intentos.first() if intentos.exists() else None,
            'mejor_puntaje': max([i.puntaje_obtenido for i in intentos]) if intentos.exists() else 0,
        })
    
    # Estadísticas de la capacitación
    total_trabajadores = len(datos_trabajadores)
    trabajadores_completados = len([t for t in datos_trabajadores if t['progreso'] and t['progreso'].completada])
    trabajadores_certificados = len([t for t in datos_trabajadores if t['certificado']])
    
    context = {
        'capacitacion': capacitacion,
        'datos_trabajadores': datos_trabajadores,
        'total_trabajadores': total_trabajadores,
        'trabajadores_completados': trabajadores_completados,
        'trabajadores_certificados': trabajadores_certificados,
        'porcentaje_completado': (trabajadores_completados / total_trabajadores * 100) if total_trabajadores > 0 else 0,
    }
    return render(request, 'capacitacion/reporte_capacitacion_detalle.html', context)


@login_required
def detalle_capacitacion(request, pk):
    """
    Muestra el detalle de una capacitación específica
    """
    capacitacion = get_object_or_404(Capacitacion, pk=pk)
    
    # Obtener progreso del usuario actual
    progreso_usuario = ProgresoCapacitacion.objects.filter(
        usuario=request.user, 
        capacitacion=capacitacion
    ).first()
    
    # Obtener certificado del usuario actual
    certificado_usuario = Certificado.objects.filter(
        usuario=request.user, 
        capacitacion=capacitacion
    ).first()
    
    # Obtener intentos de evaluación
    intentos_evaluacion = IntentoEvaluacion.objects.filter(
        usuario=request.user,
        evaluacion__capacitacion=capacitacion
    ).order_by('-fecha_intento')
    
    # Último intento (si existe)
    intento_evaluacion = intentos_evaluacion.first() if intentos_evaluacion.exists() else None
    
    # Estadísticas generales
    total_estudiantes = User.objects.filter(groups__name='trabajador').count()
    completadas_count = ProgresoCapacitacion.objects.filter(
        capacitacion=capacitacion, 
        completada=True
    ).count()
    
    # Calcular tasa de finalización
    if total_estudiantes > 0:
        tasa_finalizacion = (completadas_count / total_estudiantes) * 100
    else:
        tasa_finalizacion = 0
    
    context = {
        'capacitacion': capacitacion,
        'progreso_usuario': progreso_usuario,
        'certificado_usuario': certificado_usuario,
        'intentos_evaluacion': intentos_evaluacion,
        'intento_evaluacion': intento_evaluacion,
        'total_estudiantes': total_estudiantes,
        'completadas_count': completadas_count,
        'tasa_finalizacion': tasa_finalizacion,  # Nuevo campo calculado
    }
    return render(request, 'capacitacion/detalle_capacitacion.html', context)


# Agrega esto en views_admin_capacitaciones.py o en tu archivo de vistas de capacitación
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View

@method_decorator(csrf_exempt, name='dispatch')
class ActualizarProgresoView(View):
    """Vista para actualizar el progreso de una capacitación"""
    
    def post(self, request, capacitacion_id):
        try:
            capacitacion = get_object_or_404(Capacitacion, id=capacitacion_id)
            usuario = request.user
            
            # Verificar que el usuario sea trabajador
            if not usuario.groups.filter(name='trabajador').exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Solo los trabajadores pueden actualizar progreso'
                }, status=403)
            
            # Obtener o crear el progreso
            progreso, created = ProgresoCapacitacion.objects.get_or_create(
                usuario=usuario,
                capacitacion=capacitacion,
                defaults={
                    'porcentaje_completado': 0,
                    'completada': False,
                    'ultimo_acceso': timezone.now()
                }
            )
            
            # Determinar acción basada en los datos enviados
            accion = request.POST.get('accion', 'acceder')
            
            if accion == 'completar':
                progreso.porcentaje_completado = 100
                progreso.completada = True
                progreso.fecha_completado = timezone.now()
                
                # Crear certificado automáticamente si se completa
                if not Certificado.objects.filter(usuario=usuario, capacitacion=capacitacion).exists():
                    certificado = Certificado.objects.create(
                        usuario=usuario,
                        capacitacion=capacitacion,
                        fecha_emision=timezone.now(),
                        codigo_verificacion=f"CER-{usuario.id}-{capacitacion.id}-{timezone.now().strftime('%Y%m%d')}",
                        estado='emitido'
                    )
                
            elif accion == 'actualizar_porcentaje':
                nuevo_porcentaje = int(request.POST.get('porcentaje', 0))
                progreso.porcentaje_completado = min(max(nuevo_porcentaje, 0), 100)
                progreso.completada = (progreso.porcentaje_completado == 100)
                if progreso.completada and not progreso.fecha_completado:
                    progreso.fecha_completado = timezone.now()
                    
            elif accion == 'marcar_iniciada':
                progreso.porcentaje_completado = 10  # Iniciada pero no completada
                progreso.completada = False
                progreso.fecha_completado = None
                
            else:  # acceder - solo actualizar último acceso
                progreso.ultimo_acceso = timezone.now()
            
            # Actualizar tiempo invertido si se proporciona
            tiempo_invertido = request.POST.get('tiempo_invertido')
            if tiempo_invertido:
                progreso.tiempo_invertido = int(tiempo_invertido)
            
            progreso.save()
            
            return JsonResponse({
                'success': True,
                'progreso': {
                    'porcentaje_completado': progreso.porcentaje_completado,
                    'completada': progreso.completada,
                    'ultimo_acceso': progreso.ultimo_acceso.isoformat(),
                    'fecha_completado': progreso.fecha_completado.isoformat() if progreso.fecha_completado else None,
                    'tiempo_invertido': progreso.tiempo_invertido
                },
                'accion': accion,
                'mensaje': self._get_mensaje_exito(accion, created)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def _get_mensaje_exito(self, accion, created):
        mensajes = {
            'acceder': 'Progreso actualizado correctamente',
            'completar': '¡Felicidades! Has completado la capacitación',
            'actualizar_porcentaje': 'Progreso actualizado correctamente',
            'marcar_iniciada': 'Capacitación marcada como iniciada'
        }
        return mensajes.get(accion, 'Progreso actualizado')

# Versión basada en función (alternativa)
@csrf_exempt
@login_required
def actualizar_progreso(request, capacitacion_id):
    """Vista para actualizar progreso (versión basada en función)"""
    if request.method == 'POST':
        try:
            capacitacion = get_object_or_404(Capacitacion, id=capacitacion_id)
            usuario = request.user
            
            # Verificar que el usuario sea trabajador
            if not usuario.groups.filter(name='trabajador').exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Solo los trabajadores pueden actualizar progreso'
                }, status=403)
            
            # Obtener datos JSON si se enviaron
            if request.content_type == 'application/json':
                import json
                data = json.loads(request.body)
            else:
                data = request.POST
            
            # Obtener o crear el progreso
            progreso, created = ProgresoCapacitacion.objects.get_or_create(
                usuario=usuario,
                capacitacion=capacitacion,
                defaults={
                    'porcentaje_completado': 0,
                    'completada': False,
                    'ultimo_acceso': timezone.now()
                }
            )
            
            # Determinar acción
            accion = data.get('accion', 'acceder')
            
            if accion == 'completar':
                progreso.porcentaje_completado = 100
                progreso.completada = True
                progreso.fecha_completado = timezone.now()
                
                # Crear certificado automáticamente
                if not Certificado.objects.filter(usuario=usuario, capacitacion=capacitacion).exists():
                    Certificado.objects.create(
                        usuario=usuario,
                        capacitacion=capacitacion,
                        fecha_emision=timezone.now(),
                        codigo_verificacion=self._generar_codigo_certificado(usuario, capacitacion),
                        estado='emitido'
                    )
                
            elif accion == 'actualizar_porcentaje':
                nuevo_porcentaje = int(data.get('porcentaje', progreso.porcentaje_completado))
                progreso.porcentaje_completado = min(max(nuevo_porcentaje, 0), 100)
                progreso.completada = (progreso.porcentaje_completado == 100)
                if progreso.completada and not progreso.fecha_completado:
                    progreso.fecha_completado = timezone.now()
                    
            elif accion == 'marcar_iniciada':
                progreso.porcentaje_completado = 10
                progreso.completada = False
                progreso.fecha_completado = None
                progreso.ultimo_acceso = timezone.now()
                
            else:  # acceder
                progreso.ultimo_acceso = timezone.now()
            
            # Actualizar tiempo invertido
            tiempo_invertido = data.get('tiempo_invertido')
            if tiempo_invertido:
                progreso.tiempo_invertido = int(tiempo_invertido)
            
            progreso.save()
            
            return JsonResponse({
                'success': True,
                'progreso': {
                    'id': progreso.id,
                    'porcentaje_completado': progreso.porcentaje_completado,
                    'completada': progreso.completada,
                    'ultimo_acceso': progreso.ultimo_acceso.isoformat(),
                    'fecha_completado': progreso.fecha_completado.isoformat() if progreso.fecha_completado else None,
                    'tiempo_invertido': progreso.tiempo_invertido
                },
                'accion': accion,
                'created': created,
                'mensaje': self._get_mensaje_exito(accion, created)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

def _generar_codigo_certificado(usuario, capacitacion):
    """Genera un código único para el certificado"""
    import uuid
    return f"CER-{usuario.id}-{capacitacion.id}-{uuid.uuid4().hex[:8].upper()}"

def _get_mensaje_exito(accion, created):
    mensajes = {
        'acceder': 'Progreso actualizado correctamente' if not created else 'Capacitación iniciada',
        'completar': '¡Felicidades! Has completado la capacitación',
        'actualizar_porcentaje': 'Progreso actualizado correctamente',
        'marcar_iniciada': 'Capacitación marcada como iniciada'
    }
    return mensajes.get(accion, 'Progreso actualizado')


# Agregar estas vistas al final de views_admin_capacitaciones.py

@login_required
def inicio_trabajador(request):
    """Vista principal del panel del trabajador"""
    # Obtener solo capacitaciones publicadas
    capacitaciones = Capacitacion.objects.filter(estado='publicada').order_by('-fecha_creacion')
    
    # Obtener progresos del usuario actual
    progresos = ProgresoCapacitacion.objects.filter(usuario=request.user).select_related('capacitacion')
    
    # Combinar capacitaciones con progresos
    capacitaciones_con_progreso = []
    for capacitacion in capacitaciones:
        progreso = progresos.filter(capacitacion=capacitacion).first()
        capacitaciones_con_progreso.append({
            'capacitacion': capacitacion,
            'progreso': progreso
        })
    
    # Obtener certificados del usuario
    certificados = Certificado.objects.filter(usuario=request.user)
    
    # Calcular estadísticas
    total_capacitaciones = capacitaciones.count()
    capacitaciones_completadas = progresos.filter(completada=True).count()
    
    # Calcular porcentaje de progreso general
    if total_capacitaciones > 0:
        porcentaje_progreso = (capacitaciones_completadas / total_capacitaciones) * 100
    else:
        porcentaje_progreso = 0
    
    context = {
        'capacitaciones_con_progreso': capacitaciones_con_progreso,
        'total_capacitaciones': total_capacitaciones,
        'capacitaciones_completadas': capacitaciones_completadas,
        'porcentaje_progreso': porcentaje_progreso,
        'certificados': certificados,
        'progresos': progresos,
        'current_date': timezone.now(),
    }
    return render(request, 'capacitacion/inicio_trabajador.html', context)

@login_required
def detalle_capacitacion(request, pk):
    """
    Muestra el detalle de una capacitación específica
    """
    capacitacion = get_object_or_404(Capacitacion, pk=pk)
    
    # Verificar que la capacitación esté publicada o el usuario sea staff
    if capacitacion.estado != 'publicada' and not request.user.is_staff:
        raise PermissionDenied("Esta capacitación no está disponible")
    
    # Obtener progreso del usuario actual
    progreso_usuario = ProgresoCapacitacion.objects.filter(
        usuario=request.user, 
        capacitacion=capacitacion
    ).first()
    
    # Obtener certificado del usuario actual
    certificado_usuario = Certificado.objects.filter(
        usuario=request.user, 
        capacitacion=capacitacion
    ).first()
    
    # Obtener intentos de evaluación si existe evaluación
    intentos_evaluacion = []
    intento_evaluacion = None
    
    if hasattr(capacitacion, 'evaluacion') and capacitacion.evaluacion.activa:
        intentos_evaluacion = IntentoEvaluacion.objects.filter(
            usuario=request.user,
            evaluacion=capacitacion.evaluacion
        ).order_by('-fecha_intento')
        intento_evaluacion = intentos_evaluacion.first() if intentos_evaluacion.exists() else None
    
    # Estadísticas generales
    total_estudiantes = User.objects.filter(groups__name='trabajador').count()
    completadas_count = ProgresoCapacitacion.objects.filter(
        capacitacion=capacitacion, 
        completada=True
    ).count()
    
    # Calcular tasa de finalización
    if total_estudiantes > 0:
        tasa_finalizacion = (completadas_count / total_estudiantes) * 100
    else:
        tasa_finalizacion = 0
    
    context = {
        'capacitacion': capacitacion,
        'progreso_usuario': progreso_usuario,
        'certificado_usuario': certificado_usuario,
        'intentos_evaluacion': intentos_evaluacion,
        'intento_evaluacion': intento_evaluacion,
        'total_estudiantes': total_estudiantes,
        'completadas_count': completadas_count,
        'tasa_finalizacion': tasa_finalizacion,
    }
    return render(request, 'capacitacion/detalle_capacitacion.html', context)

@csrf_exempt
@login_required
def iniciar_capacitacion(request, capacitacion_id):
    """Vista para iniciar una capacitación"""
    if request.method == 'POST':
        try:
            capacitacion = get_object_or_404(Capacitacion, id=capacitacion_id)
            
            # Verificar que la capacitación esté publicada
            if capacitacion.estado != 'publicada':
                return JsonResponse({
                    'success': False,
                    'error': 'Esta capacitación no está disponible'
                }, status=403)
            
            # Crear o actualizar progreso
            progreso, created = ProgresoCapacitacion.objects.get_or_create(
                usuario=request.user,
                capacitacion=capacitacion,
                defaults={
                    'completada': False,
                    'progreso_porcentaje': 0,
                }
            )
            
            # Manejar el tipo de contenido
            if capacitacion.tipo_contenido == 'pdf' and capacitacion.archivo_pdf:
                # Redirigir al PDF
                return JsonResponse({
                    'success': True,
                    'redirect_url': capacitacion.archivo_pdf.url,
                    'message': 'Redirigiendo al PDF'
                })
            elif capacitacion.tipo_contenido == 'video' and capacitacion.url_video:
                # Redirigir al video
                return JsonResponse({
                    'success': True,
                    'redirect_url': capacitacion.url_video,
                    'message': 'Redirigiendo al video'
                })
            elif capacitacion.tipo_contenido == 'texto' and capacitacion.contenido_texto:
                # Redirigir al detalle donde se mostrará el texto
                return JsonResponse({
                    'success': True,
                    'redirect_url': f'/inicio/detalle/capacitaciones/{capacitacion.id}/',
                    'message': 'Redirigiendo al contenido'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'No hay contenido disponible para esta capacitación'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)