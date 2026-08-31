"""
Responsabilidad: Recepción y validación de archivos escaneados (individual o en lote) y encolado del procesamiento.
Requisitos: RF-01
Importa: infraestructura, identidad
"""

from ingesta.recepcion import EXTENSIONES_ACEPTADAS, motivo_de_rechazo, recibir_lote

# Interfaz pública del módulo. Quien use `ingesta` importa de aquí y no de sus archivos
# internos: `recepcion.py` puede reorganizarse sin romper a nadie mientras estos tres nombres
# sigan significando lo mismo.
__all__ = ["recibir_lote", "motivo_de_rechazo", "EXTENSIONES_ACEPTADAS"]
