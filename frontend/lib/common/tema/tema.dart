import 'package:flutter/material.dart';

import 'tokens.dart';

/// Familia tipográfica de toda la interfaz. Va empaquetada en `assets/fuentes/` (licencia OFL)
/// para que el sitio no dependa de Google Fonts al cargar.
const familiaTexto = 'PlusJakartaSans';

/// Familia para fórmulas, identificadores de trabajo y códigos.
const familiaMono = 'JetBrainsMono';

/// Estilos que el tema de Material no cubre.
abstract final class QTexto {
  /// Cifras de métricas: tabulares, para que no bailen cuando cambian.
  static const cifraGrande = TextStyle(
    fontFamily: familiaTexto,
    fontSize: 40,
    height: 1.1,
    fontWeight: FontWeight.w700,
    letterSpacing: -0.8,
    color: QColores.texto,
    fontFeatures: [FontFeature.tabularFigures()],
  );

  static const cifra = TextStyle(
    fontFamily: familiaTexto,
    fontSize: 24,
    height: 1.2,
    fontWeight: FontWeight.w700,
    letterSpacing: -0.36,
    color: QColores.texto,
    fontFeatures: [FontFeature.tabularFigures()],
  );

  /// Etiqueta pequeña en mayúsculas, para estados y encabezados de bloque. Se usa con mesura:
  /// una por bloque como mucho.
  static const etiqueta = TextStyle(
    fontFamily: familiaTexto,
    fontSize: 11,
    height: 1.4,
    fontWeight: FontWeight.w700,
    letterSpacing: 0.6,
  );

  static const formula = TextStyle(
    fontFamily: familiaMono,
    fontSize: 14,
    height: 1.5,
    color: QColores.texto,
  );

  static const codigo = TextStyle(
    fontFamily: familiaMono,
    fontSize: 12,
    height: 1.4,
    color: QColores.textoSuave,
  );
}

/// El tema de la aplicación, armado con los tokens de [QColores].
ThemeData construirTema() {
  const esquema = ColorScheme(
    brightness: Brightness.light,
    primary: QColores.cobalto,
    onPrimary: Colors.white,
    primaryContainer: QColores.superficieAzulFuerte,
    onPrimaryContainer: QColores.navyProfundo,
    secondary: QColores.navy,
    onSecondary: Colors.white,
    secondaryContainer: QColores.superficieAzulMedia,
    onSecondaryContainer: QColores.navy,
    tertiary: QColores.cianTexto,
    onTertiary: Colors.white,
    error: QColores.errorTexto,
    onError: Colors.white,
    errorContainer: QColores.errorFondo,
    onErrorContainer: QColores.errorTexto,
    surface: QColores.superficie,
    onSurface: QColores.texto,
    onSurfaceVariant: QColores.textoSuave,
    surfaceContainerLowest: QColores.superficie,
    surfaceContainerLow: QColores.superficieAzul,
    surfaceContainer: QColores.superficieAzulMedia,
    surfaceContainerHigh: QColores.superficieAzulFuerte,
    outline: QColores.bordeCampo,
    outlineVariant: QColores.borde,
    shadow: QColores.navy,
    inverseSurface: QColores.navyMedio,
    onInverseSurface: Colors.white,
  );

  TextStyle estilo(double tamano, double alto, FontWeight peso, [double espaciado = 0]) =>
      TextStyle(
        fontFamily: familiaTexto,
        fontSize: tamano,
        height: alto / tamano,
        fontWeight: peso,
        letterSpacing: espaciado,
        color: QColores.texto,
      );

  final textos = TextTheme(
    displaySmall: estilo(32, 40, FontWeight.w700, -0.64),
    headlineMedium: estilo(24, 32, FontWeight.w700, -0.36),
    headlineSmall: estilo(20, 28, FontWeight.w600, -0.2),
    titleLarge: estilo(18, 24, FontWeight.w600),
    titleMedium: estilo(16, 24, FontWeight.w600),
    titleSmall: estilo(14, 20, FontWeight.w600),
    bodyLarge: estilo(16, 24, FontWeight.w400),
    bodyMedium: estilo(14, 20, FontWeight.w400),
    bodySmall: estilo(12, 16, FontWeight.w400).copyWith(color: QColores.textoSuave),
    labelLarge: estilo(14, 20, FontWeight.w600, 0.14),
    labelMedium: estilo(12, 16, FontWeight.w600, 0.24),
    labelSmall: estilo(11, 14, FontWeight.w700, 0.44),
  );

  final formaControl = RoundedRectangleBorder(
    borderRadius: BorderRadius.circular(QRadios.control),
  );

  return ThemeData(
    useMaterial3: true,
    colorScheme: esquema,
    fontFamily: familiaTexto,
    textTheme: textos,
    scaffoldBackgroundColor: QColores.fondo,
    dividerTheme: const DividerThemeData(color: QColores.borde, thickness: 1, space: 1),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: QColores.cobalto,
        foregroundColor: Colors.white,
        disabledBackgroundColor: QColores.superficieSuave,
        disabledForegroundColor: QColores.textoTenue,
        minimumSize: const Size(48, 48),
        padding: const EdgeInsets.symmetric(horizontal: QEspacios.lg),
        textStyle: textos.labelLarge,
        shape: formaControl,
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: QColores.cobaltoOscuro,
        backgroundColor: QColores.superficie,
        minimumSize: const Size(48, 48),
        padding: const EdgeInsets.symmetric(horizontal: QEspacios.lg),
        side: const BorderSide(color: QColores.bordeCampo),
        textStyle: textos.labelLarge,
        shape: formaControl,
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: QColores.cobaltoOscuro,
        minimumSize: const Size(48, 48),
        textStyle: textos.labelLarge,
        shape: formaControl,
      ),
    ),
    iconButtonTheme: IconButtonThemeData(
      style: IconButton.styleFrom(minimumSize: const Size(48, 48)),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: QColores.superficie,
      contentPadding: const EdgeInsets.symmetric(horizontal: QEspacios.md, vertical: 14),
      labelStyle: textos.bodyMedium?.copyWith(color: QColores.textoSuave),
      floatingLabelStyle: textos.labelMedium?.copyWith(color: QColores.cobaltoOscuro),
      helperStyle: textos.bodySmall,
      hintStyle: textos.bodyMedium?.copyWith(color: QColores.textoTenue),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(QRadios.control),
        borderSide: const BorderSide(color: QColores.bordeCampo),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(QRadios.control),
        borderSide: const BorderSide(color: QColores.bordeCampo),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(QRadios.control),
        borderSide: const BorderSide(color: QColores.cobalto, width: 2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(QRadios.control),
        borderSide: const BorderSide(color: QColores.errorTexto),
      ),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: QColores.superficieAzul,
      selectedColor: QColores.cobalto,
      labelStyle: textos.labelMedium,
      side: const BorderSide(color: QColores.borde),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(QRadios.pildora)),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: QColores.superficie,
      indicatorColor: QColores.superficieAzulFuerte,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      height: 68,
      labelTextStyle: WidgetStateProperty.resolveWith(
        (estados) => textos.labelMedium?.copyWith(
          color: estados.contains(WidgetState.selected)
              ? QColores.cobaltoOscuro
              : QColores.textoSuave,
        ),
      ),
      iconTheme: WidgetStateProperty.resolveWith(
        (estados) => IconThemeData(
          color: estados.contains(WidgetState.selected)
              ? QColores.cobaltoOscuro
              : QColores.textoSuave,
        ),
      ),
    ),
    navigationRailTheme: NavigationRailThemeData(
      backgroundColor: QColores.superficie,
      indicatorColor: QColores.superficieAzulFuerte,
      selectedIconTheme: const IconThemeData(color: QColores.cobaltoOscuro),
      unselectedIconTheme: const IconThemeData(color: QColores.textoSuave),
      selectedLabelTextStyle: textos.labelMedium?.copyWith(color: QColores.cobaltoOscuro),
      unselectedLabelTextStyle: textos.labelMedium?.copyWith(color: QColores.textoSuave),
    ),
    snackBarTheme: SnackBarThemeData(
      backgroundColor: QColores.navy,
      contentTextStyle: textos.bodyMedium?.copyWith(color: Colors.white),
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(QRadios.control)),
    ),
    progressIndicatorTheme: const ProgressIndicatorThemeData(
      color: QColores.cobalto,
      linearTrackColor: QColores.superficieAzulMedia,
    ),
    tooltipTheme: TooltipThemeData(
      decoration: BoxDecoration(
        color: QColores.navy,
        borderRadius: BorderRadius.circular(QRadios.control),
      ),
      textStyle: textos.bodySmall?.copyWith(color: Colors.white),
    ),
  );
}
