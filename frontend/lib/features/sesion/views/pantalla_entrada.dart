import 'package:flutter/material.dart';

import '../../../common/api/sesion.dart';
import '../../../common/tema/tokens.dart';
import '../../../common/widgets/q_tarjeta.dart';

/// La entrada a QuantIA (A-05, ADR-0025): correo y contraseña de un docente de la lista.
///
/// Sigue el diseño que trajo el equipo, sin lo que el sistema no hace: no hay entrada con SAVIO ni
/// con Microsoft 365, ni recuperación de contraseña (la da quien administra QuantIA, en el panel
/// del servidor), y el pie no afirma una autenticación federada ni un cumplimiento legal que nadie
/// verificó. Un botón que un jurado pulsa y no hace nada se lee como una función rota.
class PantallaEntrada extends StatefulWidget {
  const PantallaEntrada({super.key, required this.alEntrar, this.aviso});

  /// Entra con lo escrito. Lanza [ExcepcionDeSesion] con el motivo si la API no deja entrar.
  final Future<void> Function(String correo, String contrasena, bool recordar) alEntrar;

  /// Por qué se volvió a la entrada, si no fue por «Salir»; por ejemplo, la sesión venció.
  final String? aviso;

  @override
  State<PantallaEntrada> createState() => _PantallaEntradaState();
}

class _PantallaEntradaState extends State<PantallaEntrada> {
  final _correo = TextEditingController();
  final _contrasena = TextEditingController();
  bool _oculta = true;
  bool _recordar = false;
  bool _entrando = false;
  String? _error;

  @override
  void dispose() {
    _correo.dispose();
    _contrasena.dispose();
    super.dispose();
  }

  Future<void> _entrar() async {
    if (_entrando) return;
    final correo = _correo.text.trim();
    final contrasena = _contrasena.text;
    final String? falta;
    if (correo.isEmpty || contrasena.isEmpty) {
      falta = 'Escriba su correo y su contraseña.';
    } else if (!correo.contains('@')) {
      falta = 'Escriba el correo completo, con @.';
    } else {
      falta = null;
    }
    if (falta != null) {
      setState(() => _error = falta);
      return;
    }
    setState(() {
      _entrando = true;
      _error = null;
    });
    try {
      await widget.alEntrar(correo, contrasena, _recordar);
    } on ExcepcionDeSesion catch (error) {
      if (mounted) setState(() => _error = error.mensaje);
    } catch (_) {
      if (mounted) setState(() => _error = 'No se pudo entrar. Vuelva a intentarlo.');
    } finally {
      if (mounted) setState(() => _entrando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final angosta = MediaQuery.sizeOf(context).width < 600;
    final aviso = widget.aviso;

    final formulario = AutofillGroup(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: _correo,
            enabled: !_entrando,
            keyboardType: TextInputType.emailAddress,
            textInputAction: TextInputAction.next,
            autocorrect: false,
            autofillHints: const [AutofillHints.email, AutofillHints.username],
            decoration: const InputDecoration(
              labelText: 'Correo institucional',
              hintText: 'profesor@utb.edu.co',
              prefixIcon: Icon(Icons.alternate_email),
            ),
          ),
          const SizedBox(height: QEspacios.md),
          TextField(
            controller: _contrasena,
            enabled: !_entrando,
            obscureText: _oculta,
            textInputAction: TextInputAction.done,
            autocorrect: false,
            enableSuggestions: false,
            autofillHints: const [AutofillHints.password],
            onSubmitted: (_) => _entrar(),
            decoration: InputDecoration(
              labelText: 'Contraseña del docente',
              prefixIcon: const Icon(Icons.lock_outline),
              suffixIcon: IconButton(
                tooltip: _oculta ? 'Mostrar la contraseña' : 'Ocultar la contraseña',
                icon: Icon(_oculta ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                onPressed: () => setState(() => _oculta = !_oculta),
              ),
            ),
          ),
          const SizedBox(height: QEspacios.sm),
          CheckboxListTile(
            value: _recordar,
            onChanged: _entrando ? null : (valor) => setState(() => _recordar = valor ?? false),
            title: Text('Recordar sesión en este dispositivo', style: textos.bodyMedium),
            controlAffinity: ListTileControlAffinity.leading,
            contentPadding: EdgeInsets.zero,
            dense: true,
          ),
          if (_error case final error?) ...[
            const SizedBox(height: QEspacios.sm),
            Semantics(
              liveRegion: true,
              child: Text(error, style: textos.bodyMedium?.copyWith(color: QColores.errorTexto)),
            ),
          ],
          const SizedBox(height: QEspacios.md),
          FilledButton.icon(
            onPressed: _entrando ? null : _entrar,
            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
            // El ícono va después del texto, como en el diseño.
            iconAlignment: IconAlignment.end,
            icon: _entrando
                ? const SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                  )
                : const Icon(Icons.arrow_forward),
            label: const Text('Iniciar sesión'),
          ),
        ],
      ),
    );

    return Scaffold(
      backgroundColor: QColores.fondo,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: EdgeInsets.all(angosta ? QEspacios.md : QEspacios.xl),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const _Encabezado(),
                  const SizedBox(height: QEspacios.xl),
                  Text(
                    'Bienvenido a QuantIA',
                    style: textos.headlineMedium?.copyWith(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: QEspacios.lg),
                  if (aviso != null) ...[
                    _Aviso(texto: aviso),
                    const SizedBox(height: QEspacios.md),
                  ],
                  QTarjeta(
                    padding: EdgeInsets.all(angosta ? QEspacios.md : QEspacios.lg),
                    child: formulario,
                  ),
                  const SizedBox(height: QEspacios.lg),
                  Text(
                    'QuantIA · UTB · Cálculo diferencial',
                    textAlign: TextAlign.center,
                    style: textos.bodySmall?.copyWith(color: QColores.textoTenue),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// La marca de QuantIA, la misma de la barra superior, y para quién es el portal.
class _Encabezado extends StatelessWidget {
  const _Encabezado();

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    // En un teléfono angosto el rótulo baja a la línea siguiente en vez de apretar la marca.
    return Wrap(
      alignment: WrapAlignment.spaceBetween,
      crossAxisAlignment: WrapCrossAlignment.center,
      spacing: QEspacios.md,
      runSpacing: QEspacios.sm,
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: QColores.cobalto,
                borderRadius: BorderRadius.circular(QRadios.control),
              ),
              child: const Icon(Icons.document_scanner_outlined, color: Colors.white, size: 22),
            ),
            const SizedBox(width: QEspacios.sm + 4),
            Text('QuantIA', style: textos.titleLarge?.copyWith(fontWeight: FontWeight.w700)),
          ],
        ),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: QColores.superficieAzulMedia,
            borderRadius: BorderRadius.circular(QRadios.pildora),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(color: QColores.cobalto, shape: BoxShape.circle),
              ),
              const SizedBox(width: 6),
              Text(
                'Portal docente UTB',
                style: textos.labelSmall?.copyWith(color: QColores.textoSuave),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _Aviso extends StatelessWidget {
  const _Aviso({required this.texto});

  final String texto;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(QEspacios.md),
      decoration: BoxDecoration(
        color: QColores.advertenciaFondo,
        borderRadius: BorderRadius.circular(QRadios.control),
      ),
      child: Row(
        children: [
          const Icon(Icons.schedule, color: QColores.advertenciaTexto, size: 20),
          const SizedBox(width: QEspacios.sm),
          Expanded(
            child: Semantics(
              liveRegion: true,
              child: Text(
                texto,
                style: Theme.of(context)
                    .textTheme
                    .bodyMedium
                    ?.copyWith(color: QColores.advertenciaTexto),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
