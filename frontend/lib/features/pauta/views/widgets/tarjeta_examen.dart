import 'package:flutter/material.dart';

import '../../../../common/tema/tema.dart';
import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_chip_estado.dart';
import '../../../../common/widgets/q_tarjeta.dart';
import '../../data/datos_ejemplo_pauta.dart';

/// El examen activo y el estado de su clave.
///
/// Frente al diseño se quitaron dos cosas que el sistema no puede afirmar: «Validación OMR
/// 100 % determinista» (es una cifra inventada) y «Clave verificada y aprobada (100 %)». Lo que
/// sí describe el flujo real es que el docente habilita la clave explícitamente (RF-07), y eso
/// es lo que se muestra, con una fecha que se declara de ejemplo.
class TarjetaExamen extends StatelessWidget {
  const TarjetaExamen({super.key, required this.examen});

  final ExamenEjemplo examen;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return QTarjeta(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Examen activo',
                      style: textos.labelMedium?.copyWith(color: QColores.cobaltoOscuro),
                    ),
                    const SizedBox(height: 2),
                    Semantics(
                      header: true,
                      child: Text(
                        '${examen.nombre} · ${examen.asignatura}',
                        style: textos.titleLarge,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(examen.grupo, style: textos.bodySmall),
                  ],
                ),
              ),
              const SizedBox(width: QEspacios.sm),
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: QColores.superficieAzulMedia,
                  borderRadius: BorderRadius.circular(QRadios.control),
                ),
                child: const Icon(
                  Icons.assignment_turned_in_outlined,
                  color: QColores.navy,
                  size: 22,
                ),
              ),
            ],
          ),
          const SizedBox(height: QEspacios.md),
          // Dos cifras lado a lado incluso a 390 px: caben, y leerlas juntas es el punto. Con
          // la misma altura, aunque el detalle de una ocupe dos líneas y el de la otra una.
          IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(
                  child: _Cifra(
                    titulo: 'Preguntas',
                    valor: '${examen.preguntas.length}',
                    detalle: 'una respuesta por pregunta',
                  ),
                ),
                const SizedBox(width: QEspacios.sm),
                Expanded(
                  child: _Cifra(
                    titulo: 'Opciones',
                    valor: examen.rangoOpciones,
                    detalle: '${examen.opciones.length} por pregunta',
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: QEspacios.md),
          _EstadoClave(fecha: examen.fechaHabilitacion),
        ],
      ),
    );
  }
}

class _Cifra extends StatelessWidget {
  const _Cifra({required this.titulo, required this.valor, required this.detalle});

  final String titulo;
  final String valor;
  final String detalle;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return Semantics(
      container: true,
      label: '$titulo: $valor, $detalle',
      child: ExcludeSemantics(
        child: Container(
          padding: const EdgeInsets.all(QEspacios.sm + 4),
          decoration: BoxDecoration(
            color: QColores.superficieAzul,
            borderRadius: BorderRadius.circular(QRadios.control),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(titulo, style: textos.labelMedium?.copyWith(color: QColores.textoSuave)),
              const SizedBox(height: 2),
              Text(valor, style: QTexto.cifra),
              Text(detalle, style: textos.bodySmall),
            ],
          ),
        ),
      ),
    );
  }
}

class _EstadoClave extends StatelessWidget {
  const _EstadoClave({required this.fecha});

  final String fecha;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    const tono = QTono.exito;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: QEspacios.sm + 4, vertical: QEspacios.sm + 2),
      decoration: BoxDecoration(
        color: tono.fondo,
        borderRadius: BorderRadius.circular(QRadios.control),
        border: Border.all(color: tono.acento.withValues(alpha: 0.25)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.verified_outlined, size: 20, color: tono.texto),
          const SizedBox(width: QEspacios.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Clave habilitada por el docente',
                  style: textos.labelLarge?.copyWith(color: tono.texto),
                ),
                Text(
                  'El $fecha (fecha de ejemplo)',
                  style: textos.bodySmall?.copyWith(color: QColores.textoSuave),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
