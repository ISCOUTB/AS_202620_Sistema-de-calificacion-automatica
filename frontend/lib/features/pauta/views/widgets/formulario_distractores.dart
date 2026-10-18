import 'package:flutter/material.dart';

import '../../../../common/tema/tema.dart';
import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_chip_estado.dart';
import '../../../../common/widgets/q_tarjeta.dart';
import '../../data/datos_ejemplo_pauta.dart';
import 'aviso_tono.dart';
import 'nota_equivalencias.dart';

/// Formulario del generador: los tres campos de `POST /distractores` y el botón que lo envía.
///
/// No guarda estado propio. La pantalla es dueña de los controladores, porque elegir una
/// pregunta de la lista los llena desde afuera y el botón depende de lo escrito.
class FormularioDistractores extends StatelessWidget {
  const FormularioDistractores({
    super.key,
    required this.enunciado,
    required this.respuesta,
    required this.errorEnunciado,
    required this.errorRespuesta,
    required this.alEditarEnunciado,
    required this.alEditarRespuesta,
    required this.cantidad,
    required this.alCambiarCantidad,
    required this.pregunta,
    required this.examen,
    required this.camposCompletos,
    required this.sinConexion,
    required this.cargando,
    required this.alProponer,
  });

  /// Los límites que acepta la API: pasarlos daría un 422 que el docente no tiene por qué ver.
  static const maxEnunciado = 1000;
  static const maxRespuesta = 300;
  static const cantidadMaxima = 5;

  final TextEditingController enunciado;
  final TextEditingController respuesta;
  final String? errorEnunciado;
  final String? errorRespuesta;
  final VoidCallback alEditarEnunciado;
  final VoidCallback alEditarRespuesta;
  final int cantidad;
  final ValueChanged<int> alCambiarCantidad;

  /// La pregunta de la lista que llenó los campos, si la hay.
  final PreguntaEjemplo? pregunta;
  final ExamenEjemplo examen;

  final bool camposCompletos;
  final bool sinConexion;
  final bool cargando;

  /// Nulo cuando el botón debe quedar deshabilitado.
  final VoidCallback? alProponer;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return QTarjeta(
      child: LayoutBuilder(
        builder: (context, restricciones) {
          final angosto = restricciones.maxWidth < 480;
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _Origen(pregunta: pregunta),
              const SizedBox(height: QEspacios.lg),
              const _Etiqueta('Enunciado'),
              TextField(
                key: const Key('campo-enunciado'),
                controller: enunciado,
                minLines: 3,
                maxLines: 6,
                maxLength: maxEnunciado,
                keyboardType: TextInputType.multiline,
                textCapitalization: TextCapitalization.sentences,
                onChanged: (_) => alEditarEnunciado(),
                decoration: InputDecoration(
                  hintText: 'Por ejemplo: Calcule la derivada de f(x) = x·sin(x).',
                  errorText: errorEnunciado,
                  // El contador por omisión se anuncia en inglés («characters remaining»),
                  // porque la aplicación no carga las traducciones de Material.
                  counterText: '${enunciado.text.characters.length}/$maxEnunciado',
                  semanticCounterText: _restantes(enunciado, maxEnunciado),
                ),
              ),
              const SizedBox(height: QEspacios.sm),
              const _Etiqueta('Respuesta correcta'),
              TextField(
                key: const Key('campo-respuesta'),
                controller: respuesta,
                maxLength: maxRespuesta,
                style: QTexto.formula.copyWith(fontSize: 15),
                onChanged: (_) => alEditarRespuesta(),
                decoration: InputDecoration(
                  hintText: 'Por ejemplo: sin(x) + x·cos(x)',
                  hintStyle: QTexto.formula.copyWith(color: QColores.textoTenue),
                  errorText: errorRespuesta,
                  counterText: '${respuesta.text.characters.length}/$maxRespuesta',
                  semanticCounterText: _restantes(respuesta, maxRespuesta),
                ),
              ),
              const SizedBox(height: QEspacios.sm),
              const _Etiqueta('Cantidad'),
              Align(
                alignment: AlignmentDirectional.centerStart,
                child: _SelectorCantidad(
                  cantidad: cantidad,
                  alCambiar: cargando ? null : alCambiarCantidad,
                ),
              ),
              const SizedBox(height: QEspacios.xs + 2),
              Text(
                'Por omisión, 3. El examen tiene ${examen.opciones.length} opciones '
                '(${examen.rangoOpciones}): caben ${examen.distractoresPorPregunta} '
                'distractores por pregunta.',
                style: textos.bodySmall,
              ),
              if (sinConexion) ...[
                const SizedBox(height: QEspacios.lg),
                const AvisoTono(
                  key: Key('aviso-sin-conexion'),
                  tono: QTono.advertencia,
                  icono: Icons.cloud_off_outlined,
                  titulo: 'Sin conexión con la API',
                  mensaje: 'Por ahora no es posible pedir propuestas. Puede escribir los '
                      'distractores a mano o volver a comprobar la conexión desde la barra '
                      'superior.',
                  anunciar: true,
                ),
              ],
              const SizedBox(height: QEspacios.lg),
              Align(
                alignment: AlignmentDirectional.centerStart,
                child: SizedBox(
                  width: angosto ? double.infinity : null,
                  child: FilledButton.icon(
                    key: const Key('boton-proponer'),
                    onPressed: alProponer,
                    icon: Icon(
                      cargando ? Icons.hourglass_top_outlined : Icons.auto_awesome_outlined,
                      size: 20,
                    ),
                    label: Text(cargando ? 'Pidiendo propuestas…' : 'Proponer distractores'),
                  ),
                ),
              ),
              if (!camposCompletos && !cargando) ...[
                const SizedBox(height: QEspacios.sm),
                Text(
                  'Escriba el enunciado y la respuesta correcta para pedir propuestas.',
                  style: textos.bodySmall,
                ),
              ],
              const SizedBox(height: QEspacios.lg),
              const NotaEquivalencias(),
            ],
          );
        },
      ),
    );
  }

  static String _restantes(TextEditingController controlador, int maximo) {
    final quedan = maximo - controlador.text.characters.length;
    return quedan == 1 ? 'Queda 1 carácter' : 'Quedan $quedan caracteres';
  }
}

/// De dónde salieron los datos del formulario. Si vienen de la lista, lo dice, para que el
/// docente sepa qué pregunta va a recibir las propuestas.
class _Origen extends StatelessWidget {
  const _Origen({required this.pregunta});

  final PreguntaEjemplo? pregunta;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final p = pregunta;
    if (p == null) {
      return Text(
        'Escriba una pregunta o elija una de la lista del examen.',
        style: textos.bodyMedium?.copyWith(color: QColores.textoSuave),
      );
    }
    return Wrap(
      spacing: QEspacios.sm,
      runSpacing: QEspacios.xs,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        QChipEstado(
          texto: 'Pregunta ${p.numero} · ${p.tema}',
          tono: QTono.info,
          icono: Icons.quiz_outlined,
        ),
        Text(
          'Datos de ejemplo; puede editarlos antes de pedir.',
          style: textos.bodySmall,
        ),
      ],
    );
  }
}

/// Etiqueta de campo arriba del control: el marcador de posición desaparece al escribir y no
/// basta como nombre del campo.
class _Etiqueta extends StatelessWidget {
  const _Etiqueta(this.texto);

  final String texto;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: QEspacios.sm),
      child: Text(texto, style: Theme.of(context).textTheme.titleSmall),
    );
  }
}

/// Selector de 1 a 5 con segmentos de 48 px. Con radio de control, no de píldora.
class _SelectorCantidad extends StatelessWidget {
  const _SelectorCantidad({required this.cantidad, required this.alCambiar});

  final int cantidad;
  final ValueChanged<int>? alCambiar;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Cantidad de distractores',
      child: SegmentedButton<int>(
        key: const Key('selector-cantidad'),
        showSelectedIcon: false,
        segments: [
          for (var n = 1; n <= FormularioDistractores.cantidadMaxima; n++)
            ButtonSegment<int>(value: n, label: Text('$n')),
        ],
        selected: {cantidad},
        onSelectionChanged: alCambiar == null ? null : (valores) => alCambiar!(valores.first),
        style: SegmentedButton.styleFrom(
          minimumSize: const Size(48, 48),
          tapTargetSize: MaterialTapTargetSize.padded,
          foregroundColor: QColores.textoSuave,
          backgroundColor: QColores.superficie,
          selectedForegroundColor: QColores.cobaltoOscuro,
          selectedBackgroundColor: QColores.superficieAzulFuerte,
          side: const BorderSide(color: QColores.bordeCampo),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(QRadios.control)),
          textStyle: Theme.of(context).textTheme.labelLarge?.copyWith(
            fontFeatures: const [FontFeature.tabularFigures()],
          ),
        ),
      ),
    );
  }
}
