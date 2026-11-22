import 'package:flutter/material.dart';

import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_chip_estado.dart';
import '../../../../common/widgets/q_tarjeta.dart';
import '../../data/preparacion_de_hojas.dart';
import '../../data/servicio_carga.dart';
import 'formato_carga.dart';

/// Zona de selección: el botón que abre el diálogo de archivos, en el celular también el de la
/// cámara, el resumen del lote y la lista de lo elegido, con la opción de quitar un archivo antes
/// de subirlo.
///
/// Frente al diseño de Stitch falta a propósito la invitación a arrastrar archivos: no existe en
/// esta versión (el selector es `file_picker`), y una zona que invita a soltar archivos que luego
/// no recibe se siente rota. El botón de la cámara del diseño sí está, como «Tomar foto», y solo
/// aparece en pantallas táctiles: en el computador abriría el mismo diálogo de archivos.
class ZonaSeleccion extends StatelessWidget {
  const ZonaSeleccion({
    super.key,
    required this.archivos,
    required this.habilitada,
    required this.compacta,
    required this.alSeleccionar,
    required this.alQuitar,
    required this.alQuitarTodos,
    this.alTomarFoto,
  });

  final List<ArchivoSeleccionado> archivos;

  /// Falso mientras se sube un lote: lo que va en camino ya no se puede quitar ni ampliar.
  final bool habilitada;

  /// Columna angosta: menos relleno y el botón a todo el ancho, al alcance del pulgar.
  final bool compacta;

  final VoidCallback alSeleccionar;
  final ValueChanged<int> alQuitar;
  final VoidCallback alQuitarTodos;

  /// Abre la cámara para una foto. Nulo fuera de una pantalla táctil, y entonces no hay botón.
  final VoidCallback? alTomarFoto;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final botones = [
      // La cámara va primero: en el celular, lo normal es tomar la foto en el momento.
      if (alTomarFoto != null)
        OutlinedButton.icon(
          onPressed: habilitada ? alTomarFoto : null,
          icon: const Icon(Icons.photo_camera_outlined),
          label: const Text('Tomar foto'),
        ),
      OutlinedButton.icon(
        onPressed: habilitada ? alSeleccionar : null,
        icon: const Icon(Icons.folder_open_outlined),
        label: const Text('Seleccionar archivos'),
      ),
    ];

    return QTarjeta(
      padding: EdgeInsets.all(compacta ? QEspacios.md : QEspacios.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: EdgeInsets.symmetric(
              horizontal: compacta ? QEspacios.md : QEspacios.lg,
              vertical: QEspacios.lg,
            ),
            decoration: BoxDecoration(
              color: QColores.superficieAzul,
              borderRadius: BorderRadius.circular(QRadios.control),
              border: Border.all(color: QColores.superficieAzulFuerte),
            ),
            child: Column(
              children: [
                Container(
                  width: 56,
                  height: 56,
                  decoration: const BoxDecoration(
                    color: QColores.superficieAzulFuerte,
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.cloud_upload_outlined,
                    size: 28,
                    color: QColores.cobaltoOscuro,
                  ),
                ),
                const SizedBox(height: QEspacios.sm + 4),
                Text(
                  'Seleccione las fotos o los escaneos',
                  style: textos.titleLarge,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: QEspacios.xs),
                Text(
                  'Puede elegir varias a la vez.',
                  style: textos.bodyMedium?.copyWith(color: QColores.textoSuave),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: QEspacios.md),
                if (compacta)
                  for (final (i, boton) in botones.indexed) ...[
                    if (i > 0) const SizedBox(height: QEspacios.sm),
                    SizedBox(width: double.infinity, child: boton),
                  ]
                else
                  Wrap(
                    alignment: WrapAlignment.center,
                    spacing: QEspacios.sm,
                    runSpacing: QEspacios.sm,
                    children: botones,
                  ),
              ],
            ),
          ),
          if (archivos.isNotEmpty) ...[
            const SizedBox(height: QEspacios.md),
            _ResumenLote(archivos: archivos),
            const SizedBox(height: QEspacios.sm + 4),
            _ListaArchivos(archivos: archivos, alQuitar: habilitada ? alQuitar : null),
            if (archivos.length > 1)
              Align(
                alignment: AlignmentDirectional.centerEnd,
                child: TextButton.icon(
                  onPressed: habilitada ? alQuitarTodos : null,
                  icon: const Icon(Icons.clear_all_outlined),
                  label: const Text('Quitar todos'),
                ),
              ),
          ],
        ],
      ),
    );
  }
}

/// «4 archivos seleccionados» y su peso total. Es región viva: al quitar un archivo, el lector de
/// pantalla anuncia la nueva cuenta, que es la única confirmación de que el archivo salió.
class _ResumenLote extends StatelessWidget {
  const _ResumenLote({required this.archivos});

  final List<ArchivoSeleccionado> archivos;

  @override
  Widget build(BuildContext context) {
    final cuenta = contar(archivos.length, 'archivo seleccionado', 'archivos seleccionados');
    final total = describirTamano(
      archivos.fold<int>(0, (suma, archivo) => suma + archivo.contenido.length),
    );
    return Semantics(
      container: true,
      liveRegion: true,
      label: '$cuenta, $total en total',
      child: ExcludeSemantics(
        child: Row(
          children: [
            const Icon(Icons.folder_outlined, size: 18, color: QColores.cobaltoOscuro),
            const SizedBox(width: QEspacios.sm),
            Expanded(
              child: Text(
                cuenta,
                style: Theme.of(context)
                    .textTheme
                    .labelLarge
                    ?.copyWith(color: QColores.cobaltoOscuro),
              ),
            ),
            const SizedBox(width: QEspacios.sm),
            QChipEstado(texto: '$total en total'),
          ],
        ),
      ),
    );
  }
}

class _ListaArchivos extends StatelessWidget {
  const _ListaArchivos({required this.archivos, required this.alQuitar});

  final List<ArchivoSeleccionado> archivos;

  /// Nulo mientras se sube: los botones de quitar quedan deshabilitados.
  final ValueChanged<int>? alQuitar;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border.all(color: QColores.borde),
        borderRadius: BorderRadius.circular(QRadios.control),
      ),
      child: Column(
        children: [
          for (var i = 0; i < archivos.length; i++) ...[
            if (i > 0) const Divider(),
            Padding(
              padding: const EdgeInsetsDirectional.fromSTEB(
                QEspacios.sm + 4,
                QEspacios.xs,
                QEspacios.xs,
                QEspacios.xs,
              ),
              child: Row(
                children: [
                  Icon(
                    iconoDeArchivo(archivos[i].nombre),
                    size: 20,
                    color: QColores.textoSuave,
                  ),
                  const SizedBox(width: QEspacios.sm + 4),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          archivos[i].nombre,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: textos.titleSmall,
                        ),
                        Text(
                          describirTamano(archivos[i].contenido.length),
                          style: textos.bodySmall,
                        ),
                        if (tienePocaResolucion(archivos[i]))
                          Text(
                            'Poca resolución: puede quedar ilegible',
                            style: textos.bodySmall?.copyWith(color: QColores.advertenciaTexto),
                          ),
                      ],
                    ),
                  ),
                  IconButton(
                    tooltip: 'Quitar ${archivos[i].nombre} de la selección',
                    onPressed: alQuitar == null ? null : () => alQuitar!(i),
                    color: QColores.textoSuave,
                    icon: const Icon(Icons.close_outlined),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}
