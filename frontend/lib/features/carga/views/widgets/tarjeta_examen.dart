import 'package:flutter/material.dart';

import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_tarjeta.dart';
import '../../data/servicio_examenes.dart';

/// El examen al que van las hojas.
///
/// Con la lista de exámenes que tienen clave (`GET /examenes`), el docente elige el suyo en un
/// desplegable: escribir el identificador de memoria hacía que una letra mal puesta mandara las
/// hojas a un examen sin clave, y nadie lo notaba hasta ver «Sin nota». En una pantalla ancha se
/// puede escribir para filtrar la lista; en el teléfono solo se elige, sin abrir el teclado.
///
/// Sin la lista, porque no se pudo cargar o porque la pantalla no recibió el servicio, queda el
/// campo de texto.
class TarjetaExamen extends StatelessWidget {
  const TarjetaExamen({
    super.key,
    required this.controlador,
    required this.habilitada,
    required this.compacta,
    this.examenes,
    this.cargando = false,
    this.alReintentar,
  });

  final TextEditingController controlador;

  /// Falso mientras se sube un lote: cambiar el examen a mitad de camino no cambiaría el destino
  /// de lo que ya va en camino, y solo confundiría.
  final bool habilitada;

  /// Menos relleno en columnas angostas, donde cada píxel de ancho cuenta.
  final bool compacta;

  /// Los exámenes con clave. Nula si no hay lista: entonces el examen se escribe.
  final List<ExamenConClave>? examenes;

  /// Mientras se pide la lista.
  final bool cargando;

  /// Vuelve a pedir la lista. Solo llega cuando no se pudo cargar.
  final VoidCallback? alReintentar;

  @override
  Widget build(BuildContext context) {
    return QTarjeta(
      padding: EdgeInsets.all(compacta ? QEspacios.md : QEspacios.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (cargando)
            const TextField(
              enabled: false,
              decoration: InputDecoration(
                labelText: 'Cargando los exámenes…',
                prefixIcon: Icon(Icons.assignment_outlined),
              ),
            )
          else if (examenes case final lista?)
            _Lista(
              controlador: controlador,
              examenes: lista,
              habilitada: habilitada,
              // En un teléfono, tocar el campo abriría el teclado encima de la lista.
              conFiltro: MediaQuery.sizeOf(context).width >= 600,
            )
          else
            TextField(
              controller: controlador,
              enabled: habilitada,
              autocorrect: false,
              textInputAction: TextInputAction.done,
              decoration: InputDecoration(
                labelText: 'Examen',
                hintText: 'Por ejemplo, CALC-2026-02',
                helperText: alReintentar == null
                    ? null
                    : 'No se pudo cargar la lista. Escriba el nombre exacto.',
                prefixIcon: const Icon(Icons.assignment_outlined),
                suffixIcon: alReintentar == null
                    ? null
                    : IconButton(
                        tooltip: 'Volver a cargar la lista',
                        onPressed: habilitada ? alReintentar : null,
                        icon: const Icon(Icons.refresh_outlined),
                      ),
              ),
            ),
        ],
      ),
    );
  }
}

/// Lo que coincide con lo escrito, o todos si nada coincide.
List<DropdownMenuEntry<String>> _filtrar(List<DropdownMenuEntry<String>> entradas, String filtro) {
  final buscado = filtro.trim().toLowerCase();
  final coinciden = [
    for (final entrada in entradas)
      if (entrada.label.toLowerCase().contains(buscado)) entrada,
  ];
  return coinciden.isEmpty ? entradas : coinciden;
}

/// El examen elegido de la lista, sin importar mayúsculas: «prototipo-r05» es PROTOTIPO-R05.
/// Nulo si lo escrito no es un examen de la lista.
ExamenConClave? examenElegido(String escrito, List<ExamenConClave> examenes) {
  final texto = escrito.trim();
  for (final examen in examenes) {
    if (examen.examenId == texto) return examen;
  }
  for (final examen in examenes) {
    if (examen.examenId.toLowerCase() == texto.toLowerCase()) return examen;
  }
  return null;
}

class _Lista extends StatelessWidget {
  const _Lista({
    required this.controlador,
    required this.examenes,
    required this.habilitada,
    required this.conFiltro,
  });

  final TextEditingController controlador;
  final List<ExamenConClave> examenes;
  final bool habilitada;
  final bool conFiltro;

  @override
  Widget build(BuildContext context) {
    final escrito = controlador.text.trim().toLowerCase();
    final elegido = examenElegido(controlador.text, examenes);
    final sinCoincidencias = escrito.isNotEmpty &&
        !examenes.any((examen) => examen.examenId.toLowerCase().contains(escrito));

    final String? ayuda;
    if (examenes.isEmpty) {
      ayuda = 'Todavía no hay exámenes con clave.';
    } else if (elegido != null && !elegido.habilitada) {
      ayuda = 'Su clave no está habilitada: las hojas quedarán sin nota.';
    } else {
      ayuda = null;
    }

    return DropdownMenu<String>(
      controller: controlador,
      enabled: habilitada && examenes.isNotEmpty,
      expandedInsets: EdgeInsets.zero,
      requestFocusOnTap: conFiltro,
      enableFilter: conFiltro,
      // Si lo escrito no coincide con ninguno, se ven todos: un menú vacío no ayuda a corregir.
      filterCallback: conFiltro ? _filtrar : null,
      menuHeight: 320,
      label: const Text('Examen'),
      hintText: 'Elija el examen',
      leadingIcon: const Icon(Icons.assignment_outlined),
      helperText: ayuda,
      errorText: sinCoincidencias ? 'No hay un examen con ese nombre.' : null,
      dropdownMenuEntries: [
        for (final examen in examenes)
          DropdownMenuEntry(
            value: examen.examenId,
            label: examen.examenId,
            trailingIcon: examen.habilitada
                ? null
                : Text(
                    'Sin habilitar',
                    style: Theme.of(context)
                        .textTheme
                        .bodySmall
                        ?.copyWith(color: QColores.advertenciaTexto),
                  ),
          ),
      ],
    );
  }
}
