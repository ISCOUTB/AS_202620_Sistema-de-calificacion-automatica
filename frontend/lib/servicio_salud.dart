import 'package:http/http.dart' as http;

/// URL del backend, fijada en tiempo de build con
/// `flutter build web --dart-define=BACKEND_URL=...` (Flutter web es estático:
/// no puede leer un `.env` en tiempo de ejecución).
const backendUrl = String.fromEnvironment(
  'BACKEND_URL',
  defaultValue: 'http://localhost:8000',
);

/// Consulta el endpoint de salud del backend. Devuelve true si respondió 200.
Future<bool> verificarSalud() async {
  try {
    final respuesta = await http
        .get(Uri.parse('$backendUrl/health'))
        .timeout(const Duration(seconds: 5));
    return respuesta.statusCode == 200;
  } catch (_) {
    return false;
  }
}
