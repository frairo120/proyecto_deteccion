import cv2
import numpy as np
import os
import time
from ultralytics import YOLO
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DroidCamera:
    def __init__(self, model_path=None, ip_address="192.168.1.100", port="4747"):
        self.video = None
        self.is_running = False
        self.ip_address = ip_address
        self.port = port
        self.last_alert_time = None
        self.alert_cooldown = 5  # segundos entre alertas
        self.last_capture_time = 0
        self.capture_interval = 2  # segundos mínimo entre capturas
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        
        # ✅ VARIABLES PARA RETRASO DE 3 SEGUNDOS
        self.human_detection_time = None
        self.alert_pending = False
        self.pending_alert_data = None
        self.alert_delay = 3.0  # 3 segundos de retraso
        
        # Ruta absoluta al modelo YOLO
        model_path = r'C:\Users\jonat\Desktop\modelo_entrenado\sistema\models2\Models\best.pt'

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Error loading model: {model_path} not found")

        try:
            logger.info(f"Attempting to load YOLOv8 model from: {model_path}")
            self.model = YOLO(model_path)
            logger.info("✅ YOLOv8 model loaded successfully")

            # Configuración optimizada
            self.model.conf = 0.25
            self.model.iou = 0.45

            logger.info("Model configuration complete")
            logger.info(f"Detectable classes: {self.model.names}")

        except Exception as e:
            logger.error(f"❌ Error loading model: {str(e)}")
            raise

    def __del__(self):
        self.stop()

    def _safe_release_camera(self):
        """Libera la cámara de forma segura"""
        try:
            if self.video:
                self.video.release()
                self.video = None
        except Exception as e:
            logger.warning(f"Warning during camera release: {e}")

    def _reconnect_camera(self):
        """Reconecta la cámara después de errores"""
        self.stop()
        time.sleep(2)  # Esperar antes de reconectar
        self.start()

    def _check_alert_delay(self, current_time):
        """Verifica si han pasado 3 segundos desde la detección del humano"""
        if self.human_detection_time is None:
            return False
        
        elapsed_time = current_time - self.human_detection_time
        return elapsed_time >= self.alert_delay

    def _process_human_detection(self, frame, detected_classes, current_time):
        """Procesa la detección de humano con retraso de 3 segundos"""
        required_items = {
            "helmet": "Casco",
            "vest": "Chaleco", 
            "boots": "Botas"
        }

        # Verificar elementos faltantes
        missing_items = []
        for item_class, item_label in required_items.items():
            if item_class not in detected_classes:
                missing_items.append(item_label)

        # Si hay elementos faltantes
        if missing_items:
            if self.human_detection_time is None:
                # ✅ PRIMERA DETECCIÓN: Iniciar contador de 3 segundos
                self.human_detection_time = current_time
                self.alert_pending = True
                self.pending_alert_data = {
                    'frame': frame.copy(),
                    'missing_items': missing_items,
                    'detection_time': current_time
                }
                logger.info(f"🕒 Humano detectado sin EPP. Esperando {self.alert_delay} segundos... Faltan: {', '.join(missing_items)}")
                return None, None
            
            elif self._check_alert_delay(current_time):
                # ✅ PASARON 3 SEGUNDOS: Generar alerta
                alert_message = f"Persona sin {', '.join(missing_items)}"
                missing_item = ', '.join(missing_items)
                
                logger.info(f"⚠️ ALERTA GENERADA después de {self.alert_delay} segundos: {alert_message}")
                
                # Guardar captura y alerta
                self.save_alert_capture(frame, alert_message, missing_item)
                
                # Resetear para la próxima detección
                self.human_detection_time = None
                self.alert_pending = False
                self.pending_alert_data = None
                
                return alert_message, missing_item
            else:
                # ✅ TODAVÍA EN PERIODO DE ESPERA
                elapsed = current_time - self.human_detection_time
                remaining = max(0, self.alert_delay - elapsed)
                logger.debug(f"⏳ Esperando: {remaining:.1f}s restantes...")
                return None, None
        else:
            # ✅ HUMANO CON TODO EL EPP: Resetear detección
            if self.human_detection_time is not None:
                logger.info("✅ Humano detectado con todo el EPP. Resetear contador.")
                self.human_detection_time = None
                self.alert_pending = False
                self.pending_alert_data = None

        return None, None

    def save_alert_capture(self, frame, alert_message, missing_item):
        """Guarda captura localmente"""
        current_time = time.time()

        # Verificar cooldown
        if current_time - self.last_capture_time < self.capture_interval:
            return None

        try:
            alertas_dir = 'media/alertas'
            os.makedirs(alertas_dir, exist_ok=True)

            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = f'alerta_{timestamp}_{missing_item.replace(" ", "_").lower()}.jpg'
            local_path = os.path.join(alertas_dir, filename)

            logger.info(f"📸 Guardando imagen de alerta: {local_path}")

            success = cv2.imwrite(local_path, frame)
            if not success:
                logger.error(f"❌ Error: No se pudo guardar la imagen en {local_path}")
                return None

            logger.info(f"✅ Imagen guardada exitosamente: {local_path}")

            self.last_capture_time = current_time
            db_path = f'alertas/{filename}'

            # Guardar en base de datos
            alert_obj = self.save_alert_to_db(alert_message, missing_item, db_path, current_time)

            if alert_obj:
                logger.info(f"✅ Alerta guardada en BD con ID: {alert_obj.id}")
            else:
                logger.info("⚠️ Alerta no guardada en BD (posible cooldown)")

            return db_path

        except Exception as e:
            logger.error(f"❌ Error crítico guardando captura: {e}")
            return None

    def save_alert_to_db(self, alert_message, missing_item, filename, current_time):
        """Guarda la alerta en la base de datos Django"""
        try:
            from django.utils import timezone
            from .models import Alert

            # Evitar alertas duplicadas por cooldown
            if not self.last_alert_time or (current_time - self.last_alert_time) > self.alert_cooldown:
                alert = Alert.objects.create(
                    message=alert_message,
                    missing=missing_item,
                    level='high',
                    video=filename,
                    timestamp=timezone.now()
                )

                logger.info(f"✅ Alerta guardada en BD: {alert_message} - Imagen: {filename}")
                self.last_alert_time = current_time
                return alert
            else:
                logger.info("⏳ Alerta omitida (cooldown activo)")
                return None

        except (ImportError, NameError) as e:
            logger.warning(f"⚠️ Django no disponible: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error guardando alerta en BD: {e}")
            return None

    def start(self):
        """Inicia la conexión con DroidCam con manejo robusto de errores"""
        if self.is_running:
            return True

        try:
            self._safe_release_camera()

            droidcam_url = f"http://{self.ip_address}:{self.port}/video"
            logger.info(f"Attempting to connect to DroidCam at: {droidcam_url}")

            # Configurar VideoCapture con parámetros optimizados
            self.video = cv2.VideoCapture(droidcam_url)
            
            # Configuraciones para mejorar la estabilidad
            self.video.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.video.set(cv2.CAP_PROP_FPS, 15)
            self.video.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

            # Esperar a que la cámara se inicialice
            time.sleep(2)

            if not self.video.isOpened():
                logger.error("❌ No se pudo conectar a DroidCam. Verifica IP y puerto.")
                self._safe_release_camera()
                return False

            # Leer frame de prueba
            ret, frame = self.video.read()
            if not ret or frame is None:
                logger.error("❌ No se pudo leer el primer frame.")
                self._safe_release_camera()
                return False

            logger.info("✅ DroidCam initialized successfully")
            self.is_running = True
            self.consecutive_errors = 0
            return True

        except Exception as e:
            logger.error(f"❌ Error starting DroidCam: {str(e)}")
            self.is_running = False
            self._safe_release_camera()
            return False

    def stop(self):
        """Detiene la cámara de forma segura"""
        self.is_running = False
        self._safe_release_camera()
        logger.info("🛑 DroidCam stopped successfully")

    def _validate_frame(self, frame):
        """Valida que el frame sea usable"""
        if frame is None:
            return False
        if frame.size == 0:
            return False
        if frame.shape[0] == 0 or frame.shape[1] == 0:
            return False
        return True

    def get_frame(self):
        """Obtiene un frame con manejo robusto de errores"""
        if not self.is_running or self.video is None or not self.video.isOpened():
            logger.warning("Cámara no disponible, intentando reconectar...")
            if not self.start():
                return None

        try:
            # Leer frame
            success, image = self.video.read()
            
            if not success or not self._validate_frame(image):
                self.consecutive_errors += 1
                logger.warning(f"Frame inválido o error de lectura (error #{self.consecutive_errors})")
                
                if self.consecutive_errors >= self.max_consecutive_errors:
                    logger.error("Máximo de errores consecutivos alcanzado, reconectando...")
                    self._reconnect_camera()
                return None

            # Resetear contador de errores
            self.consecutive_errors = 0
            original_image = image.copy()
            current_time = time.time()

            # YOLOv8 Prediction con manejo de errores
            try:
                results = self.model.predict(image, conf=0.25, verbose=False, imgsz=320)

                if results and len(results) > 0:
                    result = results[0]
                    num_detections = len(result.boxes)

                    detected_classes = [self.model.names[int(cls)] for cls in result.boxes.cls]

                    alert_message = None
                    missing_item = None
                    epp_status = {}

                    has_person = "human" in detected_classes

                    # ✅ NUEVA LÓGICA: Solo procesar si hay humano
                    if has_person:
                        alert_message, missing_item = self._process_human_detection(
                            original_image, detected_classes, current_time
                        )
                        
                        # Actualizar estado EPP para visualización
                        required_items = {"helmet": "Casco", "vest": "Chaleco", "boots": "Botas"}
                        for item_class, item_label in required_items.items():
                            epp_status[item_label] = item_class in detected_classes
                    else:
                        # ✅ NO HAY HUMANO: Resetear detección
                        if self.human_detection_time is not None:
                            logger.info("👤 Humano ya no detectado. Resetear contador.")
                            self.human_detection_time = None
                            self.alert_pending = False
                            self.pending_alert_data = None

                        # Si no hay humano, todos los EPP son None
                        required_items = {"helmet": "Casco", "vest": "Chaleco", "boots": "Botas"}
                        for item_label in required_items.values():
                            epp_status[item_label] = None

                    annotated_frame = result.plot()
                    y_offset = 40

                    # Mostrar estado EPP
                    for item_label in required_items.values():
                        current_status = epp_status.get(item_label, None)

                        if current_status is True:
                            color = (0, 255, 0)
                            estado = "OK"
                        elif current_status is False:
                            color = (0, 0, 255)
                            estado = "FALTANTE"
                        else:
                            color = (255, 255, 0)
                            estado = "N/A"

                        cv2.putText(
                            annotated_frame,
                            f"{item_label}: {estado}",
                            (10, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            color,
                            2
                        )
                        y_offset += 35

                    cv2.putText(annotated_frame, f"Detecciones: {num_detections}", (10, y_offset),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    y_offset += 30

                    # Mostrar contador si hay alerta pendiente
                    if self.alert_pending and self.human_detection_time is not None:
                        elapsed = current_time - self.human_detection_time
                        remaining = max(0, self.alert_delay - elapsed)
                        cv2.putText(annotated_frame, f"⏳ Alertando en: {remaining:.1f}s", 
                                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                        y_offset += 30

                    if alert_message:
                        cv2.putText(annotated_frame, "⚠️ ALERTA: EPP FALTANTE", (10, y_offset),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        y_offset += 30
                        cv2.putText(annotated_frame, f"Falta: {missing_item}", (10, y_offset),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                    ret, jpeg = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    return jpeg.tobytes()

                else:
                    # Sin detecciones - resetear
                    self.human_detection_time = None
                    self.alert_pending = False
                    self.pending_alert_data = None
                    
                    cv2.putText(original_image, "Detecciones: 0", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    cv2.putText(original_image, "No se detectaron objetos relevantes", (10, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

                    ret, jpeg = cv2.imencode('.jpg', original_image, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    return jpeg.tobytes()

            except Exception as e:
                logger.error(f"Error en procesamiento YOLO: {e}")
                # Devolver frame original si falla el procesamiento
                ret, jpeg = cv2.imencode('.jpg', original_image, [cv2.IMWRITE_JPEG_QUALITY, 80])
                return jpeg.tobytes()

        except Exception as e:
            logger.error(f"Error crítico procesando frame: {e}")
            self.consecutive_errors += 1
            return None

# Ejemplo de uso mejorado
if __name__ == "__main__":
    camera = DroidCamera(ip_address="192.168.0.100", port="4747")
    
    try:
        if camera.start():
            cv2.namedWindow("Detección de EPP - DroidCam", cv2.WINDOW_NORMAL)

            logger.info("Sistema iniciado. Presiona 'q' para salir.")
            logger.info("📸 Las alertas se generarán después de 3 segundos de detección continua")

            while True:
                frame_data = camera.get_frame()
                if frame_data is None:
                    logger.warning("No se pudo obtener el frame. Reintentando...")
                    time.sleep(1)
                    continue

                try:
                    nparr = np.frombuffer(frame_data, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if frame is not None:
                        cv2.imshow("Detección de EPP - DroidCam", frame)
                    else:
                        logger.warning("Frame decodificado es None")
                except Exception as e:
                    logger.error(f"Error decodificando frame: {e}")

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        else:
            logger.error("No se pudo iniciar la cámara")

    except KeyboardInterrupt:
        logger.info("🛑 Aplicación detenida por el usuario.")
    except Exception as e:
        logger.error(f"Error en la aplicación: {e}")
    finally:
        camera.stop()
        cv2.destroyAllWindows()