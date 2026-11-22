import 'package:http/http.dart' as http;

/// El cliente HTTP de los servicios de la API cuando hay inicio de sesión (ADR-0025): agrega el
/// token en cada petición y, si la API responde 401, avisa que la sesión ya no vale.
///
/// Los servicios ya recibían un `http.Client` para las pruebas, así que ninguno cambió: la sesión
/// entra por aquí, en un solo lugar, y no hay forma de que un servicio nuevo se olvide del token
/// si se arma en `ServiciosApp.reales`. La respuesta del 401 sigue su camino, y el servicio la
/// traduce a su mensaje como cualquier otro error; el aviso es lo que lleva a la entrada.
class ClienteConSesion extends http.BaseClient {
  ClienteConSesion({required this.token, required this.alVencer, http.Client? interno})
      : _interno = interno ?? http.Client();

  /// El token vigente en el momento de cada petición, o null si no hay sesión.
  final String? Function() token;

  final void Function() alVencer;
  final http.Client _interno;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest peticion) async {
    final vigente = token();
    if (vigente != null) peticion.headers['Authorization'] = 'Bearer $vigente';
    final respuesta = await _interno.send(peticion);
    if (respuesta.statusCode == 401) alVencer();
    return respuesta;
  }

  @override
  void close() => _interno.close();
}
