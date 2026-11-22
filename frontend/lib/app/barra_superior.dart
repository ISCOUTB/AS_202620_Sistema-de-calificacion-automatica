import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../common/api/servicio_salud.dart';
import '../common/tema/tokens.dart';

/// Barra superior institucional: la marca, el estado real de la conexión con la API y, con una
/// sesión abierta, quién entró y el botón para salir.
///
/// El diseño original mostraba notificaciones y el perfil de un profesor. Las notificaciones no
/// están: el sistema no las tiene, y una campana inventada se leería como una función que existe.
/// Del perfil queda lo que es real desde ADR-0025: el correo con que se entró. En un teléfono se
/// esconde y queda solo el botón de salir, para no quitarle espacio al estado de la API.
class BarraSuperior extends StatelessWidget implements PreferredSizeWidget {
  const BarraSuperior({
    super.key,
    required this.estado,
    required this.alReintentar,
    this.correo,
    this.alSalir,
  });

  final ValueListenable<EstadoApi> estado;
  final VoidCallback alReintentar;

  /// El correo de la sesión abierta; sin él no se muestra.
  final String? correo;

  /// Cierra la sesión, después de confirmarlo en un cuadro; sin él no hay botón para salir.
  final VoidCallback? alSalir;

  @override
  Size get preferredSize => const Size.fromHeight(64);

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final angosta = MediaQuery.sizeOf(context).width < 600;
    return Material(
      color: QColores.navy,
      child: SafeArea(
        bottom: false,
        child: SizedBox(
          height: 64,
          child: Padding(
            padding: const EdgeInsetsDirectional.symmetric(horizontal: QEspacios.md),
            child: Row(
              children: [
                const _Marca(),
                const SizedBox(width: QEspacios.sm + 4),
                // Expanded y con recorte: en un teléfono angosto, o con el texto agrandado, el
                // nombre cede espacio antes que el estado de la API, que es la información útil.
                Expanded(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'QuantIA',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: textos.titleLarge?.copyWith(
                          color: QColores.textoSobreNavy,
                          fontWeight: FontWeight.w700,
                          height: 1.1,
                        ),
                      ),
                      Text(
                        'UTB · Cálculo diferencial',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: textos.bodySmall?.copyWith(color: QColores.textoSobreNavySuave),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: QEspacios.md),
                ValueListenableBuilder<EstadoApi>(
                  valueListenable: estado,
                  builder: (context, valor, _) => _EstadoConexion(
                    estado: valor,
                    compacto: angosta,
                    alReintentar: alReintentar,
                  ),
                ),
                if (correo case final correo? when !angosta) ...[
                  const SizedBox(width: QEspacios.md),
                  ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 220),
                    child: Text(
                      correo,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: textos.bodySmall?.copyWith(color: QColores.textoSobreNavySuave),
                    ),
                  ),
                ],
                if (alSalir case final alSalir?) ...[
                  const SizedBox(width: QEspacios.xs),
                  IconButton(
                    tooltip: 'Cerrar sesión',
                    onPressed: () async {
                      if (await _confirmarCierre(context)) alSalir();
                    },
                    icon: const Icon(Icons.logout, color: QColores.textoSobreNavy),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Pregunta antes de cerrar la sesión: el botón está junto al estado de la API, y un toque por
/// error sacaba al docente y le hacía perder lo que no había guardado. Cancelar o tocar fuera del
/// cuadro lo deja como estaba.
Future<bool> _confirmarCierre(BuildContext context) async {
  final confirmado = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: const Text('¿Cerrar sesión?'),
      content: const Text(
        'Tendrá que volver a entrar con su correo y su contraseña. Lo que no se haya guardado, '
        'como las fotos elegidas en Carga o lo elegido en Revisión, se pierde.',
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          onPressed: () => Navigator.of(context).pop(true),
          child: const Text('Cerrar sesión'),
        ),
      ],
    ),
  );
  return confirmado ?? false;
}

class _Marca extends StatelessWidget {
  const _Marca();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 36,
      height: 36,
      decoration: BoxDecoration(
        color: QColores.cobalto,
        borderRadius: BorderRadius.circular(QRadios.control),
      ),
      child: const Icon(Icons.document_scanner_outlined, color: Colors.white, size: 20),
    );
  }
}

/// El estado de la API, con texto e ícono (el color solo no alcanza) y la opción de volver a
/// comprobar cuando no hay conexión.
class _EstadoConexion extends StatelessWidget {
  const _EstadoConexion({
    required this.estado,
    required this.compacto,
    required this.alReintentar,
  });

  final EstadoApi estado;
  final bool compacto;
  final VoidCallback alReintentar;

  @override
  Widget build(BuildContext context) {
    final (texto, icono, color) = switch (estado) {
      EstadoApi.verificando => ('Comprobando conexión', Icons.sync, QColores.textoSobreNavySuave),
      EstadoApi.conectada => ('Conectado', Icons.cloud_done_outlined, const Color(0xFF6EE7B7)),
      EstadoApi.sinConexion => ('Sin conexión', Icons.cloud_off_outlined, const Color(0xFFFDBA74)),
    };
    final estilo = Theme.of(context).textTheme.labelMedium?.copyWith(color: color);

    final contenido = Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icono, size: 18, color: color),
        if (!compacto) ...[
          const SizedBox(width: QEspacios.sm),
          Text(texto, style: estilo),
        ],
      ],
    );

    return Semantics(
      label: texto,
      liveRegion: true,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Tooltip(message: texto, child: contenido),
          if (estado == EstadoApi.sinConexion)
            IconButton(
              tooltip: 'Volver a comprobar la conexión',
              onPressed: alReintentar,
              icon: const Icon(Icons.refresh, color: QColores.textoSobreNavy),
            ),
        ],
      ),
    );
  }
}
