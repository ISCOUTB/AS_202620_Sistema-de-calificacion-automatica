import 'package:flutter/material.dart';

import 'servicio_salud.dart' as servicio;

const nombreSistema = 'Sistema de Calificación OMR';

class PantallaInicio extends StatefulWidget {
  const PantallaInicio({super.key, this.verificarSalud = servicio.verificarSalud});

  final Future<bool> Function() verificarSalud;

  @override
  State<PantallaInicio> createState() => _PantallaInicioState();
}

class _PantallaInicioState extends State<PantallaInicio> {
  late final Future<bool> _saludFutura;

  @override
  void initState() {
    super.initState();
    _saludFutura = widget.verificarSalud();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text(nombreSistema)),
      body: Center(
        child: FutureBuilder<bool>(
          future: _saludFutura,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const CircularProgressIndicator();
            }
            final conectado = snapshot.data ?? false;
            return Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(nombreSistema, style: TextStyle(fontSize: 24)),
                const SizedBox(height: 16),
                Text(
                  conectado
                      ? 'Conectado al backend'
                      : 'No se pudo conectar al backend',
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}
