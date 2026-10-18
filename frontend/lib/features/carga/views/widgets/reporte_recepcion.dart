import 'package:flutter/material.dart';

import '../../../../common/tema/tema.dart';
import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_chip_estado.dart';
import '../../../../common/widgets/q_panel_navy.dart';
import '../../../../common/widgets/q_tarjeta.dart';
import '../../data/servicio_carga.dart';
import 'aviso_carga.dart';
import 'formato_carga.dart';

/// El reporte de recepción: la forma visible de la promesa de EC-07, que ninguna hoja desaparece
/// sin aviso.
///
/// Encabeza con el total procesado y los conteos, **siempre los dos aunque alguno sea cero**, para
/// que el docente pueda contar lo que subió contra lo que el sistema dice haber recibido. Debajo va
/// una tarjeta por archivo. Los rechazos van primero porque son los únicos que le piden algo al
/// docente; después las pendientes de encolar, y al final las que ya están en cola.
///
/// Del diseño de Stitch se quitaron los textos técnicos que la API no devuelve («Magic Bytes:
/// 89 50 4E 47», «volumen seguro UTB», «Redis»): inventarlos haría pasar por medición lo que es
/// decoración.
class ReporteRecepcion extends StatelessWidget {
  const ReporteRecepcion({
    super.key,
    required this.resultado,
    required this.examenId,
    required this.enviados,
    required this.ancho,
    this.claveCabecera,
  });

  final ResultadoCarga resultado;

  /// El examen al que se subió el lote. El modelo de respuesta no lo conserva, así que la
  /// pantalla pasa el que envió.
  final String examenId;

  /// Cuántos archivos salieron de este navegador en la petición.
  final int enviados;

  /// Ancho disponible. Las tarjetas lo reciben de aquí y no de un `LayoutBuilder` propio porque
  /// [QTarjeta] con riel mide su alto con `IntrinsicHeight`, que un `LayoutBuilder` no admite.
  final double ancho;

  /// Marca la cabecera para que la pantalla pueda llevarla a la vista cuando llega el reporte.
  final Key? claveCabecera;

  @override
  Widget build(BuildContext context) {
    final pendientes = [
      for (final hoja in resultado.aceptadas)
        if (hoja.estado == EstadoHoja.pendienteDeEncolar) hoja,
    ];
    final encoladas = [
      for (final hoja in resultado.aceptadas)
        if (hoja.estado == EstadoHoja.encolada) hoja,
    ];
    final detallados = resultado.aceptadas.length + resultado.rechazados.length;

    // La comprobación del lado del docente. El backend ya garantiza que aceptadas y rechazadas
    // suman lo recibido; aquí se compara además con lo que este navegador envió, que es el único
    // punto del sistema que conoce las dos cifras. Si no cuadran, un archivo se perdió en algún
    // tramo, y eso es justo lo que EC-07 no admite que pase en silencio.
    final cuadra = resultado.totalProcesados == enviados && detallados == enviados;
    final chipAlLado = ancho >= 520;

    final tarjetas = <Widget>[
      for (final archivo in resultado.rechazados)
        _TarjetaRechazo(archivo: archivo, chipAlLado: chipAlLado),
      for (final hoja in pendientes) _TarjetaAceptada(hoja: hoja, chipAlLado: chipAlLado),
      for (final hoja in encoladas) _TarjetaAceptada(hoja: hoja, chipAlLado: chipAlLado),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        KeyedSubtree(
          key: claveCabecera,
          child: _Cabecera(
            resultado: resultado,
            examenId: examenId,
            pendientes: pendientes.length,
          ),
        ),
        if (!cuadra) ...[
          const SizedBox(height: QEspacios.md),
          AvisoCarga(
            tono: QTono.advertencia,
            icono: Icons.sync_problem_outlined,
            titulo: 'El reporte no cuadra con el lote',
            texto: 'Se enviaron ${contar(enviados, 'archivo', 'archivos')}, pero el reporte '
                'detalla $detallados.',
            detalle: 'Compare la lista con sus archivos: los que no aparezcan aquí no tienen '
                'confirmación de la API.',
          ),
        ],
        if (tarjetas.isNotEmpty) ...[
          const SizedBox(height: QEspacios.md),
          // Seleccionable para que el docente pueda copiar un motivo o el identificador de un
          // trabajo: en la web, el texto de Flutter no se puede seleccionar por defecto.
          SelectionArea(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (var i = 0; i < tarjetas.length; i++) ...[
                  if (i > 0) const SizedBox(height: QEspacios.sm + 4),
                  tarjetas[i],
                ],
              ],
            ),
          ),
        ],
      ],
    );
  }
}

/// Cabecera navy del reporte: el total y los conteos, con una sola frase para el lector de
/// pantalla, que la anuncia al aparecer.
class _Cabecera extends StatelessWidget {
  const _Cabecera({
    required this.resultado,
    required this.examenId,
    required this.pendientes,
  });

  final ResultadoCarga resultado;
  final String examenId;
  final int pendientes;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final recibidas = resultado.aceptadas.length;
    final rechazadas = resultado.rechazados.length;
    final total = resultado.totalProcesados;

    final textoRecibidas = contar(recibidas, 'recibida', 'recibidas');
    final textoRechazadas = contar(rechazadas, 'rechazada', 'rechazadas');
    final textoPendientes = contar(pendientes, 'pendiente de encolar', 'pendientes de encolar');
    final anuncio = 'Reporte de recepción del examen $examenId. '
        'Se procesaron ${contar(total, 'archivo', 'archivos')}: $textoRecibidas'
        '${pendientes > 0 ? ', de ellas $textoPendientes' : ''}, y $textoRechazadas.';

    return Semantics(
      container: true,
      liveRegion: true,
      label: anuncio,
      child: ExcludeSemantics(
        child: QPanelNavy(
          padding: const EdgeInsets.all(QEspacios.md + 4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: QColores.textoSobreNavy.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(QRadios.control),
                    ),
                    child: const Icon(Icons.fact_check_outlined, size: 22),
                  ),
                  const SizedBox(width: QEspacios.sm + 4),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Reporte de recepción · $examenId',
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: textos.bodySmall?.copyWith(
                            color: QColores.textoSobreNavySuave,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'Se procesaron $total archivo(s)',
                          style: textos.titleMedium?.copyWith(
                            color: QColores.textoSobreNavy,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: QEspacios.md),
              Wrap(
                spacing: QEspacios.sm,
                runSpacing: QEspacios.sm,
                children: [
                  QChipEstado(
                    texto: textoRecibidas,
                    tono: recibidas > 0 ? QTono.exito : QTono.neutro,
                    icono: Icons.check_circle_outlined,
                  ),
                  QChipEstado(
                    texto: textoRechazadas,
                    tono: rechazadas > 0 ? QTono.error : QTono.neutro,
                    icono: Icons.cancel_outlined,
                  ),
                  if (pendientes > 0)
                    QChipEstado(
                      texto: textoPendientes,
                      tono: QTono.advertencia,
                      icono: Icons.schedule_outlined,
                    ),
                ],
              ),
              if (rechazadas > 0) ...[
                const SizedBox(height: QEspacios.sm + 4),
                Text(
                  'Los archivos rechazados no se guardaron: corríjalos y vuelva a '
                  'seleccionarlos para subirlos.',
                  style: textos.bodySmall?.copyWith(color: QColores.textoSobreNavySuave),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Una hoja aceptada: en cola, o guardada y pendiente de encolar.
///
/// La pendiente va en naranja y no en rojo porque no es un error ni una pérdida (ADR-0006): la
/// hoja ya está almacenada y en la bitácora. Si se mostrara como falla, el docente la volvería
/// a subir y quedaría duplicada. El texto no promete un reintento automático: todavía no existe
/// (consumir las pendientes de la bitácora es trabajo de A-02).
class _TarjetaAceptada extends StatelessWidget {
  const _TarjetaAceptada({required this.hoja, required this.chipAlLado});

  final HojaAceptada hoja;
  final bool chipAlLado;

  @override
  Widget build(BuildContext context) {
    final pendiente = hoja.estado == EstadoHoja.pendienteDeEncolar;
    final tono = pendiente ? QTono.advertencia : QTono.exito;
    final estado = pendiente ? 'Pendiente de encolar' : 'En cola · ${idCorto(hoja.trabajoId)}';
    final detalle = pendiente
        ? 'Recibida y guardada. Su trabajo no llegó a la cola y queda registrado como '
            'pendiente; no hace falta volver a subirla.'
        : 'Recibida. Su trabajo quedó en la cola de procesamiento.';

    return _TarjetaArchivo(
      anuncio: '${hoja.nombreArchivo}. ${pendiente ? 'Pendiente de encolar' : 'En cola'}. '
          '$detalle',
      riel: tono.acento,
      icono: iconoDeArchivo(hoja.nombreArchivo),
      tonoIcono: QTono.neutro,
      nombre: hoja.nombreArchivo,
      chipAlLado: chipAlLado,
      chip: QChipEstado(
        texto: estado,
        tono: tono,
        icono: pendiente ? Icons.schedule_outlined : Icons.check_circle_outlined,
      ),
      cuerpo: Text(
        detalle,
        style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: QColores.textoSuave),
      ),
      pie: Text('Trabajo ${hoja.trabajoId}', style: QTexto.codigo),
    );
  }
}

/// Un archivo rechazado, con el motivo tal como lo redacta la API para el docente.
class _TarjetaRechazo extends StatelessWidget {
  const _TarjetaRechazo({required this.archivo, required this.chipAlLado});

  final ArchivoRechazado archivo;
  final bool chipAlLado;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return _TarjetaArchivo(
      anuncio: '${archivo.nombreArchivo}. Rechazada. Motivo: ${archivo.motivo}',
      riel: QTono.error.acento,
      icono: Icons.warning_amber_outlined,
      tonoIcono: QTono.error,
      nombre: archivo.nombreArchivo,
      chipAlLado: chipAlLado,
      chip: const QChipEstado(
        texto: 'Rechazada',
        tono: QTono.error,
        icono: Icons.cancel_outlined,
      ),
      cuerpo: Container(
        padding: const EdgeInsets.all(QEspacios.sm + 4),
        decoration: BoxDecoration(
          color: QColores.superficieSuave,
          borderRadius: BorderRadius.circular(QRadios.control),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Motivo', style: textos.labelMedium?.copyWith(color: QColores.textoSuave)),
            const SizedBox(height: 2),
            Text(archivo.motivo, style: textos.bodyMedium),
          ],
        ),
      ),
    );
  }
}

/// La forma común de las tarjetas del reporte: riel de estado, ícono, nombre, chip y cuerpo.
///
/// El chip va a la derecha del nombre cuando hay ancho y debajo cuando no, para que un nombre
/// largo de escáner no quede reducido a tres letras en un teléfono. La tarjeta entera se lee como
/// una sola frase, porque el ícono y el riel no dicen nada a un lector de pantalla.
class _TarjetaArchivo extends StatelessWidget {
  const _TarjetaArchivo({
    required this.anuncio,
    required this.riel,
    required this.icono,
    required this.tonoIcono,
    required this.nombre,
    required this.chip,
    required this.chipAlLado,
    required this.cuerpo,
    this.pie,
  });

  final String anuncio;
  final Color riel;
  final IconData icono;
  final QTono tonoIcono;
  final String nombre;
  final Widget chip;
  final bool chipAlLado;
  final Widget cuerpo;
  final Widget? pie;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      label: anuncio,
      child: ExcludeSemantics(
        child: QTarjeta(
          riel: riel,
          padding: const EdgeInsets.all(QEspacios.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: tonoIcono.fondo,
                      borderRadius: BorderRadius.circular(QRadios.control),
                    ),
                    child: Icon(icono, size: 20, color: tonoIcono.texto),
                  ),
                  const SizedBox(width: QEspacios.sm + 4),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Padding(
                          padding: const EdgeInsets.only(top: QEspacios.sm),
                          child: Text(
                            nombre,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.titleSmall,
                          ),
                        ),
                        if (!chipAlLado) ...[
                          const SizedBox(height: QEspacios.sm),
                          chip,
                        ],
                      ],
                    ),
                  ),
                  if (chipAlLado) ...[
                    const SizedBox(width: QEspacios.sm),
                    Padding(
                      padding: const EdgeInsets.only(top: QEspacios.xs + 2),
                      child: chip,
                    ),
                  ],
                ],
              ),
              const SizedBox(height: QEspacios.sm + 4),
              cuerpo,
              if (pie != null) ...[
                const SizedBox(height: QEspacios.sm),
                pie!,
              ],
            ],
          ),
        ),
      ),
    );
  }
}
