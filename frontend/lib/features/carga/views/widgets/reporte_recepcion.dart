import 'package:flutter/material.dart';

import '../../../../common/tema/tema.dart';
import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_chip_estado.dart';
import '../../../../common/widgets/q_panel_navy.dart';
import '../../../../common/widgets/q_tarjeta.dart';
import '../../data/servicio_carga.dart';
import '../../data/servicio_resultados.dart';
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
    this.lecturas,
    this.leyendo = false,
    this.alConsultarDeNuevo,
    this.alRevisar,
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

  /// Lo que ya se leyó de cada hoja aceptada, por `hoja_id`. Nulo si la pantalla no consulta
  /// resultados: entonces el reporte es solo el de la recepción.
  final Map<String, ResultadoDeHoja>? lecturas;

  /// Verdadero mientras la pantalla sigue preguntando por los resultados.
  final bool leyendo;

  /// Vuelve a preguntar, cuando ya se dejó de hacerlo y faltan hojas.
  final VoidCallback? alConsultarDeNuevo;

  /// Lleva a la pantalla de revisión, desde una hoja con preguntas que esperan al docente.
  final VoidCallback? alRevisar;

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

    ResultadoDeHoja? lecturaDe(HojaAceptada hoja) =>
        hoja.hojaId == null ? null : lecturas?[hoja.hojaId];
    final tarjetas = <Widget>[
      for (final archivo in resultado.rechazados)
        _TarjetaRechazo(archivo: archivo, chipAlLado: chipAlLado),
      for (final hoja in pendientes)
        _TarjetaAceptada(hoja: hoja, chipAlLado: chipAlLado, lectura: lecturaDe(hoja)),
      for (final hoja in encoladas)
        _TarjetaAceptada(
          hoja: hoja,
          chipAlLado: chipAlLado,
          lectura: lecturaDe(hoja),
          alRevisar: alRevisar,
        ),
    ];
    final lecturasDelLote = lecturas;

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
        // Solo se leen las que llegaron a la cola: una en espera no entra a la lectura.
        if (lecturasDelLote != null && encoladas.isNotEmpty) ...[
          const SizedBox(height: QEspacios.md),
          _ResumenDeLectura(
            porLeer: encoladas.length,
            lecturas: lecturasDelLote.values.toList(),
            leyendo: leyendo,
            alConsultarDeNuevo: alConsultarDeNuevo,
          ),
        ],
        if (!cuadra) ...[
          const SizedBox(height: QEspacios.md),
          AvisoCarga(
            tono: QTono.advertencia,
            icono: Icons.sync_problem_outlined,
            titulo: 'El reporte no cuadra con el lote',
            texto: 'Se enviaron ${contar(enviados, 'archivo', 'archivos')}, pero el reporte '
                'detalla $detallados.',
            detalle: 'Compare la lista con sus archivos: los que no aparezcan aquí no tienen '
                'confirmación del servidor.',
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
    final textoPendientes = contar(pendientes, 'en espera', 'en espera');
    final textoTotal = contar(total, 'archivo subido', 'archivos subidos');
    final anuncio = 'Examen $examenId. $textoTotal: $textoRecibidas'
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
                          'Examen $examenId',
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: textos.bodySmall?.copyWith(
                            color: QColores.textoSobreNavySuave,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          textoTotal,
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
                  'Los rechazados no se guardaron: corríjalos y vuelva a subirlos.',
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
  const _TarjetaAceptada({
    required this.hoja,
    required this.chipAlLado,
    this.lectura,
    this.alRevisar,
  });

  final HojaAceptada hoja;
  final bool chipAlLado;
  final VoidCallback? alRevisar;

  /// Cómo quedó la hoja después de leerla, si ya se leyó.
  final ResultadoDeHoja? lectura;

  @override
  Widget build(BuildContext context) {
    final leida = lectura;
    if (leida != null) return _tarjetaLeida(context, leida);
    final pendiente = hoja.estado == EstadoHoja.pendienteDeEncolar;
    final tono = pendiente ? QTono.advertencia : QTono.exito;
    final estado = pendiente ? 'En espera' : 'Recibida';
    final detalle = pendiente
        ? 'Quedó guardada, pero todavía no entra a la lectura. No hace falta volver a subirla.'
        : 'Se está leyendo.';

    return _TarjetaArchivo(
      anuncio: '${hoja.nombreArchivo}. $estado. $detalle',
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

  /// La hoja ya leída: su nota, lo que espera al docente o por qué no se pudo leer.
  Widget _tarjetaLeida(BuildContext context, ResultadoDeHoja leida) {
    final nota = leida.notaEnDecimas == null ? null : notaLegible(leida.notaEnDecimas!);
    final preguntas = leida.preguntasPorRevisar;
    final textoPreguntas = preguntas.isEmpty
        ? ''
        : preguntas.length == 1
            ? 'Espera su revisión la pregunta ${preguntas.first}.'
            : 'Esperan su revisión las preguntas ${_enumerar(preguntas)}.';
    final avisoCodigo = leida.codigoCompleto == false
        ? ' El código del estudiante quedó incompleto: revíselo en la hoja.'
        : '';
    final (QTono tono, IconData icono, String chip, String detalle) = switch (leida.estado) {
      EstadoDeLectura.calificada => (
          QTono.exito,
          Icons.task_alt_outlined,
          'Calificada · $nota',
          'Nota $nota de 5,0.${leida.revisada ? ' Incluye su revisión.' : ''}$avisoCodigo',
        ),
      EstadoDeLectura.enRevision => (
          QTono.advertencia,
          Icons.rate_review_outlined,
          'En revisión · $nota',
          'Nota provisional $nota. $textoPreguntas$avisoCodigo',
        ),
      EstadoDeLectura.sinClaveHabilitada => (
          QTono.advertencia,
          Icons.key_off_outlined,
          'Sin nota',
          '${_frase(motivoLegible(leida.motivo))}$avisoCodigo',
        ),
      EstadoDeLectura.ilegible => (
          QTono.error,
          Icons.image_not_supported_outlined,
          'Ilegible',
          'No se pudo leer: ${motivoLegible(leida.motivo)}. Tome la foto de nuevo y súbala.',
        ),
    };
    return _TarjetaArchivo(
      anuncio: '${hoja.nombreArchivo}. $chip. $detalle',
      riel: tono.acento,
      icono: iconoDeArchivo(hoja.nombreArchivo),
      tonoIcono: QTono.neutro,
      nombre: hoja.nombreArchivo,
      chipAlLado: chipAlLado,
      chip: QChipEstado(texto: chip, tono: tono, icono: icono),
      cuerpo: Text(
        detalle,
        style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: QColores.textoSuave),
      ),
      pie: Text('Trabajo ${hoja.trabajoId}', style: QTexto.codigo),
      accion:
          leida.estado == EstadoDeLectura.enRevision && preguntas.isNotEmpty && alRevisar != null
              ? TextButton.icon(
                  onPressed: alRevisar,
                  icon: const Icon(Icons.rate_review_outlined, size: 18),
                  label: const Text('Revisar'),
                )
              : null,
    );
  }
}

/// «el examen todavía no tiene clave» como frase: «El examen todavía no tiene clave.».
String _frase(String texto) =>
    texto.isEmpty ? texto : '${texto[0].toUpperCase()}${texto.substring(1)}.';

/// «7», «7 y 12», «3, 7 y 12».
String _enumerar(List<int> numeros) {
  if (numeros.length == 1) return '${numeros.first}';
  final antes = numeros.sublist(0, numeros.length - 1).join(', ');
  return '$antes y ${numeros.last}';
}

/// Cuántas hojas del lote ya se leyeron y cómo quedaron, mientras el worker avanza.
class _ResumenDeLectura extends StatelessWidget {
  const _ResumenDeLectura({
    required this.porLeer,
    required this.lecturas,
    required this.leyendo,
    required this.alConsultarDeNuevo,
  });

  final int porLeer;
  final List<ResultadoDeHoja> lecturas;
  final bool leyendo;
  final VoidCallback? alConsultarDeNuevo;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    int cuantas(EstadoDeLectura estado) => lecturas.where((l) => l.estado == estado).length;
    final partes = [
      if (cuantas(EstadoDeLectura.calificada) > 0)
        contar(cuantas(EstadoDeLectura.calificada), 'calificada', 'calificadas'),
      if (cuantas(EstadoDeLectura.enRevision) > 0)
        '${cuantas(EstadoDeLectura.enRevision)} en revisión',
      if (cuantas(EstadoDeLectura.sinClaveHabilitada) > 0)
        '${cuantas(EstadoDeLectura.sinClaveHabilitada)} sin nota',
      if (cuantas(EstadoDeLectura.ilegible) > 0)
        contar(cuantas(EstadoDeLectura.ilegible), 'ilegible', 'ilegibles'),
    ];
    final leidas = lecturas.length;
    final todas = leidas >= porLeer;
    final titulo = todas
        ? 'Lectura terminada: ${contar(leidas, 'hoja leída', 'hojas leídas')}'
        : 'Leídas $leidas de $porLeer';
    final detalle = partes.isEmpty
        ? (leyendo ? 'El sistema está leyendo las hojas.' : 'Todavía no hay hojas leídas.')
        : '${partes.join(' · ')}.';

    return Semantics(
      container: true,
      liveRegion: true,
      label: '$titulo. $detalle',
      child: ExcludeSemantics(
        child: QTarjeta(
          padding: const EdgeInsets.all(QEspacios.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Icon(
                    todas ? Icons.fact_check_outlined : Icons.document_scanner_outlined,
                    size: 20,
                    color: QColores.cobaltoOscuro,
                  ),
                  const SizedBox(width: QEspacios.sm),
                  Expanded(child: Text(titulo, style: textos.titleSmall)),
                  if (!todas && !leyendo && alConsultarDeNuevo != null)
                    TextButton.icon(
                      onPressed: alConsultarDeNuevo,
                      icon: const Icon(Icons.refresh_outlined, size: 18),
                      label: const Text('Consultar de nuevo'),
                    ),
                ],
              ),
              const SizedBox(height: QEspacios.xs),
              Text(detalle, style: textos.bodySmall),
              if (!todas && leyendo) ...[
                const SizedBox(height: QEspacios.sm),
                LinearProgressIndicator(
                  value: porLeer == 0 ? null : leidas / porLeer,
                  semanticsLabel: 'Leyendo las hojas',
                ),
              ],
            ],
          ),
        ),
      ),
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
    this.accion,
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

  /// Un botón al pie de la tarjeta. Va fuera de la frase que lee el lector de pantalla, para que
  /// se pueda alcanzar como botón.
  final Widget? accion;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      label: anuncio,
      child: QTarjeta(
        riel: riel,
        padding: const EdgeInsets.all(QEspacios.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            ExcludeSemantics(
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
            if (accion != null) ...[
              const SizedBox(height: QEspacios.xs),
              Align(alignment: AlignmentDirectional.centerStart, child: accion!),
            ],
          ],
        ),
      ),
    );
  }
}
