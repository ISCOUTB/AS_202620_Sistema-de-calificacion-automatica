import 'package:flutter/material.dart';

import '../../../common/tema/tokens.dart';
import '../data/datos_ejemplo_revision.dart';

/// Formatos de la revisión, con coma decimal como se escriben las notas en Colombia.
///
/// Viven en la carpeta de la pantalla y no en `lib/common/` porque, por ahora, solo los usa esta
/// vista; si otra pantalla los necesita, se mueven.
String formatearNota(int decimas) => '${decimas ~/ 10},${decimas % 10}';

String formatearDecimal(double valor) => valor.toStringAsFixed(1).replaceAll('.', ',');

String formatearPorcentaje(int valor) => '$valor %';

/// Texto del botón de cada veredicto, como lo pide el diseño.
String etiquetaVeredicto(Veredicto v) => switch (v.tipo) {
      TipoVeredicto.correcta => '${v.opcion} · Correcta (+${formatearDecimal(v.puntos)})',
      TipoVeredicto.incorrecta => '${v.opcion} · Incorrecta (0,0)',
      TipoVeredicto.anulada => 'Anular · sin efecto',
    };

/// Lo mismo, dicho completo para un lector de pantalla: «A punto Correcta» no se entiende.
String descripcionVeredicto(Veredicto v) => switch (v.tipo) {
      TipoVeredicto.correcta =>
        'Aceptar ${v.opcion}: respuesta correcta, suma ${formatearDecimal(v.puntos)} punto',
      TipoVeredicto.incorrecta => 'Tomar ${v.opcion}: respuesta incorrecta, no suma puntos',
      TipoVeredicto.anulada => 'Anular la pregunta: no suma ni resta puntos',
    };

/// Resumen corto de una decisión, para el registro de la sesión.
String resumenVeredicto(Veredicto v) => switch (v.tipo) {
      TipoVeredicto.correcta => '${v.opcion} correcta',
      TipoVeredicto.incorrecta => '${v.opcion} incorrecta',
      TipoVeredicto.anulada => 'anulada',
    };

/// Ícono y color de cada veredicto. El color solo acompaña: el texto dice lo mismo.
(IconData, Color) iconoVeredicto(TipoVeredicto tipo) => switch (tipo) {
      TipoVeredicto.correcta => (Icons.check_circle_outline, QColores.exitoTexto),
      TipoVeredicto.incorrecta => (Icons.cancel_outlined, QColores.errorTexto),
      TipoVeredicto.anulada => (Icons.block_outlined, QColores.textoSuave),
    };

/// Círculo con las iniciales del estudiante. El diseño de Stitch usaba fotos; aquí no, porque
/// las hojas y las notas son datos personales (RNF-12) y un ejemplo no debe sugerir lo contrario.
class AvatarIniciales extends StatelessWidget {
  const AvatarIniciales({super.key, required this.iniciales, this.tamano = 40});

  final String iniciales;
  final double tamano;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final estilo = tamano >= 48 ? textos.titleMedium : textos.labelLarge;
    return ExcludeSemantics(
      child: Container(
        width: tamano,
        height: tamano,
        alignment: Alignment.center,
        decoration: const BoxDecoration(
          color: QColores.superficieAzulFuerte,
          shape: BoxShape.circle,
        ),
        // Sin escalar: es decorativo (el nombre completo va al lado) y no debe salirse del círculo.
        child: Text(
          iniciales,
          textScaler: TextScaler.noScaling,
          style: estilo?.copyWith(color: QColores.navy),
        ),
      ),
    );
  }
}
