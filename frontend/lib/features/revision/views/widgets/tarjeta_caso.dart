import 'package:flutter/material.dart';

import '../../../../common/tema/tema.dart';
import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_chip_estado.dart';
import '../../../../common/widgets/q_panel_navy.dart';
import '../../../../common/widgets/q_tarjeta.dart';
import '../../data/datos_ejemplo_revision.dart';
import '../formato_revision.dart';

/// La marca dudosa que espera decisión: de quién es, qué pregunta, qué vio el lector OMR y los
/// veredictos posibles (RF-03 y RF-08).
///
/// No usa `QTarjeta(riel:)`: la franja superior ya dice el estado, y el riel envuelve el contenido
/// en un `IntrinsicHeight` que obligaría a medir dos veces la tarjeta más grande de la pantalla.
class TarjetaCaso extends StatelessWidget {
  const TarjetaCaso({
    super.key,
    required this.caso,
    required this.estudiante,
    required this.notaTentativa,
    required this.notaSiCorrecta,
    required this.compacta,
    required this.botonesEnFila,
    required this.alDecidir,
  });

  final CasoRevision caso;
  final EstudianteEjemplo estudiante;

  /// Nota sin la pregunta dudosa, en décimas.
  final int notaTentativa;

  /// Nota si el docente acepta la marca que coincide con la clave; nula si ninguna coincide.
  final int? notaSiCorrecta;

  /// Teléfono: menos relleno y la nota debajo del nombre en vez de al lado.
  final bool compacta;

  /// Los tres veredictos en una fila; si no caben con holgura, uno debajo de otro.
  final bool botonesEnFila;
  final ValueChanged<Veredicto> alDecidir;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final relleno = compacta ? QEspacios.md : QEspacios.lg;
    final siCorrecta = notaSiCorrecta;

    // Si aceptar la marca cambia la nota de reprobada a aprobada, se dice: es la decisión que más
    // pesa y la que más daño haría si se tomara a ciegas.
    final defineAprobacion = siCorrecta != null &&
        notaTentativa < corteAprobacionDecimas &&
        siCorrecta >= corteAprobacionDecimas;

    return QTarjeta(
      padding: EdgeInsets.zero,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _Franja(relleno: relleno),
          Padding(
            padding: EdgeInsets.all(relleno),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _Identidad(
                  estudiante: estudiante,
                  notaTentativa: notaTentativa,
                  notaSiCorrecta: siCorrecta,
                  opcionCorrecta: caso.veredictoCorrecto?.opcion,
                  compacta: compacta,
                ),
                const SizedBox(height: QEspacios.md),
                _Pregunta(caso: caso),
                const SizedBox(height: QEspacios.lg),
                Wrap(
                  spacing: QEspacios.sm,
                  runSpacing: QEspacios.sm,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text(
                      'Recorte de la hoja escaneada',
                      style: textos.labelLarge?.copyWith(color: QColores.textoSuave),
                    ),
                    QChipEstado(
                      texto: 'Confianza ${formatearPorcentaje(caso.confianza)}',
                      tono: QTono.advertencia,
                      icono: Icons.warning_amber_outlined,
                      pildora: true,
                    ),
                    if (caso.motivo == MotivoRevision.dobleMarcacion)
                      const QChipEstado(
                        texto: 'Doble marcación',
                        tono: QTono.error,
                        icono: Icons.content_copy_outlined,
                      ),
                    if (defineAprobacion)
                      const QChipEstado(
                        texto: 'Define si aprueba',
                        tono: QTono.info,
                        icono: Icons.flag_outlined,
                      ),
                  ],
                ),
                const SizedBox(height: QEspacios.sm + 4),
                _RecorteOmr(caso: caso, compacto: compacta),
                const SizedBox(height: QEspacios.lg),
                Text('Veredicto docente', style: textos.titleSmall),
                const SizedBox(height: 2),
                Text(
                  'Indique qué quiso marcar el estudiante. La nota se recalcula con su decisión.',
                  style: textos.bodySmall,
                ),
                const SizedBox(height: QEspacios.sm + 4),
                _Veredictos(
                  veredictos: caso.veredictos,
                  enFila: botonesEnFila,
                  alDecidir: alDecidir,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Franja extends StatelessWidget {
  const _Franja({required this.relleno});

  final double relleno;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsetsDirectional.symmetric(horizontal: relleno, vertical: QEspacios.sm + 4),
      decoration: BoxDecoration(
        color: QColores.advertenciaFondo,
        border: Border(
          bottom: BorderSide(color: QColores.advertencia.withValues(alpha: 0.25)),
        ),
      ),
      child: Row(
        children: [
          const Icon(Icons.pending_actions_outlined, size: 20, color: QColores.advertenciaTexto),
          const SizedBox(width: QEspacios.sm),
          Expanded(
            child: Text(
              'Requiere decisión docente',
              style: Theme.of(context)
                  .textTheme
                  .labelLarge
                  ?.copyWith(color: QColores.advertenciaTexto),
            ),
          ),
        ],
      ),
    );
  }
}

class _Identidad extends StatelessWidget {
  const _Identidad({
    required this.estudiante,
    required this.notaTentativa,
    required this.notaSiCorrecta,
    required this.opcionCorrecta,
    required this.compacta,
  });

  final EstudianteEjemplo estudiante;
  final int notaTentativa;
  final int? notaSiCorrecta;
  final String? opcionCorrecta;
  final bool compacta;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final persona = Row(
      children: [
        AvatarIniciales(iniciales: estudiante.iniciales, tamano: 48),
        const SizedBox(width: QEspacios.sm + 4),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(estudiante.nombreCompleto, style: textos.titleMedium),
              const SizedBox(height: 2),
              Text('Código ${estudiante.codigo}', style: QTexto.codigo),
            ],
          ),
        ),
      ],
    );
    final nota = _NotaTentativa(
      nota: notaTentativa,
      siCorrecta: notaSiCorrecta,
      opcion: opcionCorrecta,
      alineacion: compacta ? CrossAxisAlignment.start : CrossAxisAlignment.end,
    );

    if (compacta) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [persona, const SizedBox(height: QEspacios.md), nota],
      );
    }
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(child: persona),
        const SizedBox(width: QEspacios.md),
        nota,
      ],
    );
  }
}

class _NotaTentativa extends StatelessWidget {
  const _NotaTentativa({
    required this.nota,
    required this.siCorrecta,
    required this.opcion,
    required this.alineacion,
  });

  final int nota;
  final int? siCorrecta;
  final String? opcion;
  final CrossAxisAlignment alineacion;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final alternativa = siCorrecta == null || opcion == null
        ? null
        : '${formatearNota(siCorrecta!)} si se acepta $opcion';

    return Semantics(
      container: true,
      label: 'Nota tentativa ${formatearNota(nota)} de 5,0.'
          '${alternativa == null ? '' : ' Si se acepta $opcion, ${formatearNota(siCorrecta!)}.'}',
      child: ExcludeSemantics(
        child: Column(
          crossAxisAlignment: alineacion,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'Nota tentativa',
              style: textos.labelMedium?.copyWith(color: QColores.textoSuave),
            ),
            Text.rich(
              TextSpan(
                children: [
                  TextSpan(
                    text: formatearNota(nota),
                    style: QTexto.cifraGrande.copyWith(color: QColores.navy),
                  ),
                  TextSpan(
                    text: ' / 5,0',
                    style: textos.bodyMedium?.copyWith(color: QColores.textoSuave),
                  ),
                ],
              ),
            ),
            if (alternativa != null)
              Text(
                alternativa,
                style: textos.labelMedium?.copyWith(color: QColores.textoSuave),
              ),
          ],
        ),
      ),
    );
  }
}

class _Pregunta extends StatelessWidget {
  const _Pregunta({required this.caso});

  final CasoRevision caso;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return Container(
      padding: const EdgeInsets.all(QEspacios.md),
      decoration: BoxDecoration(
        color: QColores.superficieAzul,
        borderRadius: BorderRadius.circular(QRadios.control),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  'Pregunta ${caso.pregunta} · ${caso.tema}',
                  style: textos.labelLarge?.copyWith(color: QColores.cobaltoOscuro),
                ),
              ),
              const SizedBox(width: QEspacios.sm),
              Text(
                'Peso ${formatearDecimal(caso.peso)}',
                style: textos.labelMedium?.copyWith(color: QColores.textoSuave),
              ),
            ],
          ),
          const SizedBox(height: QEspacios.sm),
          Wrap(
            spacing: QEspacios.sm,
            runSpacing: QEspacios.xs,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(caso.enunciado, style: textos.bodyLarge),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: QEspacios.sm, vertical: 2),
                decoration: BoxDecoration(
                  color: QColores.superficie,
                  borderRadius: BorderRadius.circular(QRadios.control),
                  border: Border.all(color: QColores.borde),
                ),
                child: Text(caso.formula, style: QTexto.formula),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// El recorte de la hoja sobre fondo navy: las cuatro burbujas tal como las leyó la máquina y la
/// alerta en lenguaje claro. Es el único panel navy de la pantalla, para que conserve su peso.
class _RecorteOmr extends StatelessWidget {
  const _RecorteOmr({required this.caso, required this.compacto});

  final CasoRevision caso;
  final bool compacto;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return QPanelNavy(
      padding: EdgeInsets.zero,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(QRadios.tarjeta),
        child: CustomPaint(
          painter: const _PintorReticula(),
          child: Padding(
            padding: EdgeInsets.all(compacto ? QEspacios.md : QEspacios.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    for (final lectura in caso.lecturas)
                      Flexible(
                        child: SizedBox(width: 96, child: _Burbuja(lectura: lectura)),
                      ),
                  ],
                ),
                const SizedBox(height: QEspacios.md),
                Container(
                  padding: const EdgeInsets.all(QEspacios.sm + 4),
                  decoration: BoxDecoration(
                    color: QColores.textoSobreNavy.withValues(alpha: 0.06),
                    borderRadius: BorderRadius.circular(QRadios.control),
                    border: Border.all(color: QColores.cian.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.info_outlined, size: 18, color: QColores.cian),
                      const SizedBox(width: QEspacios.sm),
                      Expanded(
                        child: Text(
                          '${caso.explicacion} Como ninguna lectura llega al '
                          '$umbralConfianza %, QuantIA no asignó respuesta.',
                          style: textos.bodyMedium?.copyWith(color: QColores.textoSobreNavy),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Burbuja extends StatelessWidget {
  const _Burbuja({required this.lectura});

  final LecturaBurbuja lectura;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final confianza = lectura.confianza;
    final descripcion = confianza == null
        ? 'Opción ${lectura.opcion}: ${lectura.tipo.descripcion}'
        : 'Opción ${lectura.opcion}: ${lectura.tipo.descripcion}, $confianza % de confianza';

    return Semantics(
      container: true,
      label: descripcion,
      child: ExcludeSemantics(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _CirculoBurbuja(lectura: lectura),
            const SizedBox(height: QEspacios.sm),
            Text(
              lectura.tipo.etiqueta,
              textAlign: TextAlign.center,
              style: textos.labelMedium?.copyWith(
                color: lectura.tieneMarca
                    ? QColores.textoSobreNavy
                    : QColores.textoSobreNavySuave,
              ),
            ),
            // La cifra va en cian porque es lectura de la máquina, no del docente.
            if (confianza != null)
              Text(
                formatearPorcentaje(confianza),
                textAlign: TextAlign.center,
                style: textos.labelMedium?.copyWith(
                  color: QColores.cian,
                  fontFeatures: const [FontFeature.tabularFigures()],
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// Cómo se ve cada burbuja en el recorte. El aro cian marca lo que el lector detectó; el relleno
/// imita el grafito: tenue, borrado o completo.
class _CirculoBurbuja extends StatelessWidget {
  const _CirculoBurbuja({required this.lectura});

  final LecturaBurbuja lectura;

  @override
  Widget build(BuildContext context) {
    final brillo = [
      BoxShadow(color: QColores.cian.withValues(alpha: 0.35), blurRadius: 12),
    ];
    final (decoracion, colorLetra) = switch (lectura.tipo) {
      TipoMarca.vacia => (
          BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(
              color: QColores.textoSobreNavySuave.withValues(alpha: 0.45),
              width: 1.5,
            ),
          ),
          QColores.textoSobreNavySuave,
        ),
      TipoMarca.tenue => (
          BoxDecoration(
            shape: BoxShape.circle,
            color: QColores.textoSobreNavySuave.withValues(alpha: 0.4),
            border: Border.all(color: QColores.cian, width: 2),
            boxShadow: brillo,
          ),
          QColores.textoSobreNavy,
        ),
      // Franja diagonal desvanecida, como deja un borrador: se distingue de la marca tenue, que
      // es pareja.
      TipoMarca.borron => (
          BoxDecoration(
            shape: BoxShape.circle,
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                QColores.textoSobreNavySuave.withValues(alpha: 0),
                QColores.textoSobreNavySuave.withValues(alpha: 0.55),
                QColores.textoSobreNavySuave.withValues(alpha: 0.2),
                QColores.textoSobreNavySuave.withValues(alpha: 0),
              ],
              stops: const [0.15, 0.4, 0.65, 0.9],
            ),
            border: Border.all(color: QColores.cian.withValues(alpha: 0.6), width: 2),
            boxShadow: brillo,
          ),
          QColores.textoSobreNavy,
        ),
      TipoMarca.completa => (
          BoxDecoration(
            shape: BoxShape.circle,
            color: QColores.textoSobreNavy.withValues(alpha: 0.92),
            border: Border.all(color: QColores.cian, width: 2),
            boxShadow: brillo,
          ),
          QColores.navy,
        ),
    };

    return Container(
      width: 48,
      height: 48,
      alignment: Alignment.center,
      decoration: decoracion,
      child: Text(
        lectura.opcion,
        // La letra crece con el texto del sistema hasta donde cabe en la burbuja.
        textScaler: MediaQuery.textScalerOf(context).clamp(maxScaleFactor: 1.3),
        style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: colorLetra,
              fontWeight: FontWeight.w700,
            ),
      ),
    );
  }
}

/// Retícula de puntos del visor OMR, decorativa.
class _PintorReticula extends CustomPainter {
  const _PintorReticula();

  @override
  void paint(Canvas canvas, Size size) {
    final pincel = Paint()..color = QColores.cian.withValues(alpha: 0.14);
    const paso = 14.0;
    for (var x = paso / 2; x < size.width; x += paso) {
      for (var y = paso / 2; y < size.height; y += paso) {
        canvas.drawCircle(Offset(x, y), 1, pincel);
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _Veredictos extends StatelessWidget {
  const _Veredictos({required this.veredictos, required this.enFila, required this.alDecidir});

  final List<Veredicto> veredictos;
  final bool enFila;
  final ValueChanged<Veredicto> alDecidir;

  @override
  Widget build(BuildContext context) {
    final botones = [
      for (final v in veredictos) _BotonVeredicto(veredicto: v, alPresionar: () => alDecidir(v)),
    ];

    if (enFila) {
      // Misma altura para los tres aunque uno parta su texto en dos líneas.
      return IntrinsicHeight(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            for (var i = 0; i < botones.length; i++) ...[
              if (i > 0) const SizedBox(width: QEspacios.sm),
              Expanded(child: botones[i]),
            ],
          ],
        ),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (var i = 0; i < botones.length; i++) ...[
          if (i > 0) const SizedBox(height: QEspacios.sm),
          botones[i],
        ],
      ],
    );
  }
}

/// Botón de veredicto. Los tres tienen el mismo peso visual a propósito: si uno fuera el botón
/// principal, la pantalla estaría sugiriendo la lectura de la máquina, que es justo lo que el
/// docente debe juzgar. El color va solo en el ícono y el texto dice el efecto en la nota.
class _BotonVeredicto extends StatelessWidget {
  const _BotonVeredicto({required this.veredicto, required this.alPresionar});

  final Veredicto veredicto;
  final VoidCallback alPresionar;

  @override
  Widget build(BuildContext context) {
    final (icono, color) = iconoVeredicto(veredicto.tipo);
    return OutlinedButton(
      onPressed: alPresionar,
      style: OutlinedButton.styleFrom(
        minimumSize: const Size(48, 56),
        padding: const EdgeInsets.symmetric(horizontal: QEspacios.md, vertical: QEspacios.sm),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icono, size: 20, color: color),
          const SizedBox(width: QEspacios.sm),
          Flexible(
            child: Text(
              etiquetaVeredicto(veredicto),
              textAlign: TextAlign.center,
              semanticsLabel: descripcionVeredicto(veredicto),
            ),
          ),
        ],
      ),
    );
  }
}

/// Las decisiones tomadas en esta visita, con la nota antes y después. Sirve para deshacer
/// cuando el aviso inferior ya se fue, y deja a la vista que la nota sí cambió.
class RegistroDecisiones extends StatelessWidget {
  const RegistroDecisiones({
    super.key,
    required this.decisiones,
    required this.nombreDe,
    required this.alDeshacer,
  });

  final List<DecisionRevision> decisiones;
  final String Function(CasoRevision caso) nombreDe;
  final VoidCallback alDeshacer;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return QTarjeta(
      padding: const EdgeInsets.all(QEspacios.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const Icon(Icons.history_outlined, size: 20, color: QColores.textoSuave),
              const SizedBox(width: QEspacios.sm),
              Expanded(child: Text('Decisiones de esta visita', style: textos.titleSmall)),
            ],
          ),
          const SizedBox(height: QEspacios.xs),
          Text(
            'Se pierden al recargar la página: esta vista de ejemplo no guarda nada.',
            style: textos.bodySmall,
          ),
          const SizedBox(height: QEspacios.sm),
          for (final d in decisiones) _FilaDecision(decision: d, nombre: nombreDe(d.caso)),
          Align(
            alignment: AlignmentDirectional.centerEnd,
            child: TextButton.icon(
              onPressed: alDeshacer,
              icon: const Icon(Icons.undo_outlined),
              label: const Text('Deshacer la última'),
            ),
          ),
        ],
      ),
    );
  }
}

class _FilaDecision extends StatelessWidget {
  const _FilaDecision({required this.decision, required this.nombre});

  final DecisionRevision decision;
  final String nombre;

  @override
  Widget build(BuildContext context) {
    final (icono, color) = iconoVeredicto(decision.veredicto.tipo);
    final antes = formatearNota(decision.notaAntes);
    final despues = formatearNota(decision.notaDespues);
    final nota = decision.notaAntes == decision.notaDespues
        ? 'nota se mantiene en $antes'
        : 'nota de $antes a $despues';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: QEspacios.xs),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icono, size: 18, color: color),
          const SizedBox(width: QEspacios.sm),
          Expanded(
            child: Text(
              '$nombre · pregunta ${decision.caso.pregunta}: '
              '${resumenVeredicto(decision.veredicto)}, $nota.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }
}
