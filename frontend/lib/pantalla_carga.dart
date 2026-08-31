import 'package:flutter/material.dart';

import 'selector_archivos.dart' as selector;
import 'servicio_carga.dart';
// El mismo archivo se importa otra vez con prefijo, y no es redundancia. Dentro de la
// expresión de un valor por defecto, los nombres de los parámetros ya están en alcance: un
// `this.subirHojas = subirHojas` se resolvería al propio parámetro y no a la función, que es
// el error de compilación que ya apareció una vez con `verificarSalud` en `PantallaInicio`.
// El prefijo desambigua. Los tipos se siguen usando sin prefijo desde el import de arriba.
import 'servicio_carga.dart' as servicio;

/// Pantalla de carga de hojas escaneadas: realiza el aspecto A-01 (RF-01) del lado del docente.
///
/// No conoce el navegador ni HTTP. Recibe las dos operaciones inyectadas —elegir archivos y
/// subirlos— con el mismo patrón que `PantallaInicio` usa para `verificarSalud`, de modo que
/// las pruebas de widget puedan ejercitarla entera sin diálogo de archivos y sin backend.
class PantallaCarga extends StatefulWidget {
  const PantallaCarga({
    super.key,
    this.seleccionarArchivos = selector.seleccionarArchivos,
    this.subirHojas = servicio.subirHojas,
  });

  final Future<List<ArchivoSeleccionado>> Function() seleccionarArchivos;
  final Future<ResultadoCarga> Function(String, List<ArchivoSeleccionado>) subirHojas;

  @override
  State<PantallaCarga> createState() => _PantallaCargaState();
}

class _PantallaCargaState extends State<PantallaCarga> {
  final TextEditingController _examen = TextEditingController();
  List<ArchivoSeleccionado> _seleccionados = const [];
  ResultadoCarga? _resultado;
  String? _error;
  bool _subiendo = false;

  @override
  void dispose() {
    _examen.dispose();
    super.dispose();
  }

  bool get _puedeSubir =>
      !_subiendo && _seleccionados.isNotEmpty && _examen.text.trim().isNotEmpty;

  Future<void> _elegir() async {
    final archivos = await widget.seleccionarArchivos();
    if (!mounted || archivos.isEmpty) return;
    setState(() {
      _seleccionados = archivos;
      _resultado = null;
      _error = null;
    });
  }

  Future<void> _subir() async {
    setState(() {
      _subiendo = true;
      _resultado = null;
      _error = null;
    });

    try {
      final resultado = await widget.subirHojas(_examen.text.trim(), _seleccionados);
      if (!mounted) return;
      // Las hojas ya recibidas se sacan de la selección: dejarlas invitaría a volver a subir
      // las mismas, y el sistema no tiene forma de detectar un duplicado.
      setState(() {
        _resultado = resultado;
        _seleccionados = const [];
      });
    } on ExcepcionDeCarga catch (error) {
      if (!mounted) return;
      setState(() => _error = error.mensaje);
    } finally {
      if (mounted) setState(() => _subiendo = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Cargar hojas de un examen')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 640),
          child: ListView(
            padding: const EdgeInsets.all(24),
            children: [
              TextField(
                controller: _examen,
                onChanged: (_) => setState(() {}),
                decoration: const InputDecoration(
                  labelText: 'Identificador del examen',
                  helperText: 'Por ejemplo, CALC-2026-01',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  OutlinedButton.icon(
                    onPressed: _subiendo ? null : _elegir,
                    icon: const Icon(Icons.attach_file),
                    label: const Text('Seleccionar hojas'),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      _seleccionados.isEmpty
                          ? 'Ninguna hoja seleccionada'
                          : '${_seleccionados.length} hoja(s) seleccionada(s)',
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: _puedeSubir ? _subir : null,
                child: Text(_subiendo ? 'Subiendo…' : 'Subir al sistema'),
              ),
              if (_subiendo) ...[
                const SizedBox(height: 16),
                const LinearProgressIndicator(),
              ],
              if (_error != null) ...[
                const SizedBox(height: 24),
                _Aviso(icono: Icons.error_outline, texto: _error!),
              ],
              if (_resultado != null) ...[
                const SizedBox(height: 24),
                _Reporte(resultado: _resultado!),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _Aviso extends StatelessWidget {
  const _Aviso({required this.icono, required this.texto});

  final IconData icono;
  final String texto;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icono),
        const SizedBox(width: 8),
        Expanded(child: Text(texto)),
      ],
    );
  }
}

/// El reporte de recepción.
///
/// Muestra **siempre las dos listas**, incluso vacías, y encabeza con el total procesado. Es la
/// forma visible de la promesa de EC-07: el docente puede contar lo que subió contra lo que el
/// sistema dice haber recibido, y ningún archivo queda sin mencionar. Cada rechazo va con su
/// motivo, porque un rechazo sin explicación se parece demasiado a una pérdida.
class _Reporte extends StatelessWidget {
  const _Reporte({required this.resultado});

  final ResultadoCarga resultado;

  @override
  Widget build(BuildContext context) {
    final estilo = Theme.of(context).textTheme.titleMedium;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Se procesaron ${resultado.totalProcesados} archivo(s)', style: estilo),
        const SizedBox(height: 12),
        Text('Recibidas: ${resultado.aceptadas.length}'),
        for (final hoja in resultado.aceptadas)
          ListTile(
            dense: true,
            leading: const Icon(Icons.check_circle_outline),
            title: Text(hoja.nombreArchivo),
            subtitle: Text('En cola · trabajo ${hoja.trabajoId}'),
          ),
        const SizedBox(height: 12),
        Text('Rechazadas: ${resultado.rechazados.length}'),
        for (final archivo in resultado.rechazados)
          ListTile(
            dense: true,
            leading: const Icon(Icons.cancel_outlined),
            title: Text(archivo.nombreArchivo),
            subtitle: Text(archivo.motivo),
          ),
      ],
    );
  }
}
