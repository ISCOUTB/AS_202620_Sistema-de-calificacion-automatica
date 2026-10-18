import 'package:flutter/material.dart';

import '../../../../common/tema/tema.dart';
import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_tarjeta.dart';
import '../../data/modelos_panel.dart';

/// Tarjeta del examen activo. Toda la tarjeta abre el menú con los exámenes del periodo, así el
/// objetivo táctil es la franja completa y no solo la flecha de la derecha.
class SelectorExamen extends StatelessWidget {
  const SelectorExamen({
    super.key,
    required this.examenes,
    required this.actual,
    required this.alElegir,
  });

  final List<ExamenPanel> examenes;
  final ExamenPanel actual;
  final ValueChanged<ExamenPanel> alElegir;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    // El menú no puede pasar del ancho de la pantalla; el nombre largo del tema se parte en dos
    // líneas en vez de cortarse.
    final anchoMenu = (MediaQuery.sizeOf(context).width - 96).clamp(200.0, 440.0);

    return MenuAnchor(
      alignmentOffset: const Offset(0, QEspacios.xs),
      style: MenuStyle(
        backgroundColor: const WidgetStatePropertyAll(QColores.superficie),
        surfaceTintColor: const WidgetStatePropertyAll(Colors.transparent),
        shape: WidgetStatePropertyAll(
          RoundedRectangleBorder(borderRadius: BorderRadius.circular(QRadios.control)),
        ),
      ),
      menuChildren: [
        for (final examen in examenes)
          MenuItemButton(
            onPressed: () => alElegir(examen),
            leadingIcon: Icon(
              examen.id == actual.id ? Icons.check_outlined : null,
              size: 20,
              color: QColores.cobaltoOscuro,
            ),
            child: ConstrainedBox(
              constraints: BoxConstraints(maxWidth: anchoMenu),
              child: Padding(
                padding: const EdgeInsetsDirectional.symmetric(vertical: QEspacios.sm),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(examen.nombre, style: textos.titleSmall),
                    Text(
                      examen.tema,
                      style: textos.bodySmall,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
            ),
          ),
      ],
      builder: (context, controlador, _) => MergeSemantics(
        child: Semantics(
          button: true,
          hint: 'Cambiar de examen',
          child: QTarjeta(
            color: QColores.superficieAzul,
            padding: const EdgeInsetsDirectional.fromSTEB(
              QEspacios.sm + 4,
              QEspacios.sm + 4,
              QEspacios.sm,
              QEspacios.sm + 4,
            ),
            alPresionar: () => controlador.isOpen ? controlador.close() : controlador.open(),
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: QColores.superficieAzulFuerte,
                    borderRadius: BorderRadius.circular(QRadios.control),
                  ),
                  child: const Icon(
                    Icons.assignment_turned_in_outlined,
                    size: 22,
                    color: QColores.cobaltoOscuro,
                  ),
                ),
                const SizedBox(width: QEspacios.sm + 4),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'EXAMEN ACTIVO',
                        style: QTexto.etiqueta.copyWith(color: QColores.textoSuave),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        actual.titulo,
                        style: textos.titleMedium,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                const SizedBox(
                  width: 48,
                  height: 48,
                  child: Icon(Icons.unfold_more_outlined, color: QColores.textoSuave),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
