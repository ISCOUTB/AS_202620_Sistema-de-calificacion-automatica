import 'package:flutter/material.dart';

import 'pantalla_inicio.dart';

void main() {
  runApp(const App());
}

class App extends StatelessWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: nombreSistema,
      home: const PantallaInicio(),
    );
  }
}
