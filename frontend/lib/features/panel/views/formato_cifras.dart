/// Formato de cifras del panel: coma decimal y espacio antes del signo de porcentaje, como se
/// escriben en español. Se evita el paquete `intl` para no sumar una dependencia por tres
/// funciones.
library;

/// Espacio que no se parte: «74,4 %» nunca queda con el signo solo en la línea siguiente.
const _espacioFijo = ' ';

String formatearDecimal(double valor, {int decimales = 1}) =>
    valor.toStringAsFixed(decimales).replaceAll('.', ',');

String formatearPorcentaje(num valor, {int decimales = 0}) =>
    '${formatearDecimal(valor.toDouble(), decimales: decimales)}$_espacioFijo%';

/// Variación con signo explícito, como «+0,4». El negativo usa el signo menos tipográfico.
String formatearVariacion(double valor) {
  final signo = valor > 0
      ? '+'
      : valor < 0
          ? '−'
          : '';
  return '$signo${formatearDecimal(valor.abs())}';
}
