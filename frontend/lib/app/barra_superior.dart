import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../common/api/servicio_salud.dart';
import '../common/tema/tokens.dart';

/// Barra superior institucional: la marca y el estado real de la conexión con la API.
///
/// El diseño original mostraba notificaciones y el perfil de un profesor. No están: el sistema
/// todavía no tiene cuentas (A-05) ni notificaciones, y una campana o un nombre inventados se
/// leerían como funciones que existen. Lo que sí es real, y útil, es saber si la API responde.
class BarraSuperior extends StatelessWidget implements PreferredSizeWidget {
  const BarraSuperior({super.key, required this.estado, required this.alReintentar});

  final ValueListenable<EstadoApi> estado;
  final VoidCallback alReintentar;

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
              ],
            ),
          ),
        ),
      ),
    );
  }
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
      EstadoApi.conectada => ('API conectada', Icons.cloud_done_outlined, const Color(0xFF6EE7B7)),
      EstadoApi.sinConexion => ('Sin conexión con la API', Icons.cloud_off_outlined, const Color(0xFFFDBA74)),
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
