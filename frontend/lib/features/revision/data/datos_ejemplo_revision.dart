/// Datos de ejemplo de la revisión manual (RF-03 y RF-08).
///
/// La detección de marcas (A-02) y la calificación (A-03) todavía no existen en el backend, así
/// que la pantalla se alimenta de aquí. Los nombres y los códigos son inventados (RNF-12): las
/// hojas y las notas son datos de estudiantes, y un ejemplo no debe exponer a nadie real.
///
/// Cada cifra que la pantalla muestra (conteos de los filtros, aprobados, promedio, nota
/// tentativa) se calcula a partir de estas listas, para que nunca se contradigan entre sí.
library;

/// Confianza mínima, en porcentaje, para que una marca se asigne sola. Por debajo, la marca va a
/// revisión manual. Es un valor supuesto (riesgo R-04) que se calibrará con hojas reales.
const umbralConfianza = 70;

/// Nota mínima aprobatoria, en décimas (3,0).
const corteAprobacionDecimas = 30;

/// Nota máxima, en décimas (5,0).
const notaMaximaDecimas = 50;

/// Un examen calificado sobre una escala de 0,0 a 5,0.
class ExamenEjemplo {
  const ExamenEjemplo({
    required this.nombre,
    required this.asignatura,
    required this.puntosTotales,
  });

  final String nombre;
  final String asignatura;
  final double puntosTotales;

  /// Nota en décimas (42 es 4,2). Se trabaja con enteros para que el redondeo y la comparación
  /// con el corte de 3,0 no dependan de errores de coma flotante.
  int notaEnDecimas(double puntos) =>
      (puntos * notaMaximaDecimas / puntosTotales).round().clamp(0, notaMaximaDecimas);
}

/// Parcial de ejemplo: 15 preguntas, diez de peso 1,0 y cinco de peso 0,5, que suman 12,5 puntos.
/// Con esa escala una pregunta de peso 1,0 mueve la nota 0,4, que es lo que muestra el diseño
/// («4,2 / 5,0» y «4,6 si se acepta A»).
const examenEjemplo = ExamenEjemplo(
  nombre: 'Parcial 2',
  asignatura: 'Cálculo diferencial',
  puntosTotales: 12.5,
);

class EstudianteEjemplo {
  const EstudianteEjemplo({
    required this.nombres,
    required this.apellidos,
    required this.codigo,
    required this.puntos,
    required this.confianzaOmr,
  });

  final String nombres;
  final String apellidos;
  final String codigo;

  /// Puntos ya asegurados. Si el estudiante tiene una marca en revisión, esa pregunta no suma
  /// aquí: la nota tentativa nunca da por buena una marca dudosa.
  final double puntos;

  /// La confianza más baja entre todas las marcas leídas en su hoja, en porcentaje.
  final int confianzaOmr;

  String get nombreCompleto => '$nombres $apellidos';

  /// Iniciales del primer nombre y el primer apellido, para el avatar (nunca una foto).
  String get iniciales => '${nombres[0]}${apellidos[0]}';
}

/// Lo que el lector OMR vio en una burbuja.
enum TipoMarca {
  vacia('Vacía', 'vacía'),
  tenue('Tenue', 'marca tenue'),
  borron('Borrón', 'borrón'),
  completa('Marcada', 'marca completa');

  const TipoMarca(this.etiqueta, this.descripcion);

  /// Texto corto bajo la burbuja.
  final String etiqueta;

  /// Texto para lectores de pantalla, dentro de una frase.
  final String descripcion;
}

class LecturaBurbuja {
  const LecturaBurbuja(this.opcion, this.tipo, [this.confianza]);

  final String opcion;
  final TipoMarca tipo;

  /// Probabilidad, en porcentaje, de que la marca sea una respuesta intencional. Nula si la
  /// burbuja está vacía.
  final int? confianza;

  bool get tieneMarca => tipo != TipoMarca.vacia;
}

/// Por qué una pregunta llegó a revisión.
enum MotivoRevision { marcaDudosa, dobleMarcacion }

enum TipoVeredicto { correcta, incorrecta, anulada }

/// La decisión del docente sobre una pregunta dudosa.
class Veredicto {
  const Veredicto.correcta(String this.opcion, this.puntos) : tipo = TipoVeredicto.correcta;

  const Veredicto.incorrecta(String this.opcion)
      : tipo = TipoVeredicto.incorrecta,
        puntos = 0;

  /// Anular deja la pregunta sin efecto: no suma ni resta, y la nota queda en la tentativa.
  const Veredicto.anulada()
      : tipo = TipoVeredicto.anulada,
        opcion = null,
        puntos = 0;

  final TipoVeredicto tipo;
  final String? opcion;

  /// Puntos que la decisión suma a los ya asegurados.
  final double puntos;
}

/// Una pregunta cuya lectura no alcanzó el umbral y espera la decisión del docente.
class CasoRevision {
  const CasoRevision({
    required this.id,
    required this.codigoEstudiante,
    required this.pregunta,
    required this.tema,
    required this.enunciado,
    required this.formula,
    required this.peso,
    required this.clave,
    required this.lecturas,
    required this.explicacion,
    this.motivo = MotivoRevision.marcaDudosa,
  });

  final String id;
  final String codigoEstudiante;
  final int pregunta;
  final String tema;
  final String enunciado;
  final String formula;
  final double peso;

  /// Respuesta correcta según la clave que registró el docente.
  final String clave;
  final List<LecturaBurbuja> lecturas;

  /// La alerta en lenguaje claro: qué se ve en la hoja, sin cifras de sensor.
  final String explicacion;
  final MotivoRevision motivo;

  /// La confianza del caso es la de su lectura más fuerte: ni siquiera esa alcanza el umbral.
  int get confianza => lecturas.fold(0, (mayor, l) {
        final c = l.confianza ?? 0;
        return c > mayor ? c : mayor;
      });

  /// Las opciones entre las que el docente decide: solo las que tienen alguna marca.
  List<LecturaBurbuja> get candidatas => [
        for (final l in lecturas)
          if (l.tieneMarca) l,
      ];

  /// Los veredictos posibles, en el orden en que se ofrecen: una opción por cada marca y, al
  /// final, anular.
  List<Veredicto> get veredictos => [
        for (final l in candidatas)
          l.opcion == clave ? Veredicto.correcta(l.opcion, peso) : Veredicto.incorrecta(l.opcion),
        const Veredicto.anulada(),
      ];

  /// El veredicto que suma puntos, si alguna de las marcas coincide con la clave.
  Veredicto? get veredictoCorrecto {
    for (final v in veredictos) {
      if (v.tipo == TipoVeredicto.correcta) return v;
    }
    return null;
  }
}

/// Una decisión ya tomada, con la nota antes y después para poder contarla y deshacerla.
class DecisionRevision {
  const DecisionRevision({
    required this.caso,
    required this.veredicto,
    required this.notaAntes,
    required this.notaDespues,
  });

  final CasoRevision caso;
  final Veredicto veredicto;
  final int notaAntes;
  final int notaDespues;
}

/// Desempeño que acompaña la nota en la lista.
enum Desempeno {
  excelente('Excelente'),
  bueno('Bueno'),
  aprobado('Aprobado'),
  reprobado('Reprobado'),
  porRevisar('Por revisar');

  const Desempeno(this.etiqueta);

  final String etiqueta;

  static Desempeno de(int notaDecimas, {required bool pendiente}) {
    if (pendiente) return Desempeno.porRevisar;
    if (notaDecimas >= 45) return Desempeno.excelente;
    if (notaDecimas >= 40) return Desempeno.bueno;
    if (notaDecimas >= corteAprobacionDecimas) return Desempeno.aprobado;
    return Desempeno.reprobado;
  }
}

/// Un estudiante tal como se muestra en la lista: su nota actual y su estado de revisión.
class FilaEstudiante {
  const FilaEstudiante({
    required this.estudiante,
    required this.notaDecimas,
    required this.pendiente,
    required this.dobleMarcacion,
  });

  final EstudianteEjemplo estudiante;
  final int notaDecimas;

  /// Tiene al menos una marca dudosa sin resolver: su nota es tentativa.
  final bool pendiente;

  /// Su hoja tuvo una pregunta con dos respuestas marcadas, resuelta o no.
  final bool dobleMarcacion;

  /// La lectura quedó por debajo del umbral y un docente ya la resolvió.
  bool get revisadaAMano => !pendiente && estudiante.confianzaOmr < umbralConfianza;

  Desempeno get desempeno => Desempeno.de(notaDecimas, pendiente: pendiente);
}

/// Cifras del grupo, calculadas solo sobre las notas definitivas: una nota tentativa no entra al
/// promedio hasta que el docente resuelve su marca dudosa.
class ResumenNotas {
  const ResumenNotas(this.notas);

  /// Notas definitivas, en décimas.
  final List<int> notas;

  int get calificados => notas.length;

  int get aprobados => notas.where((n) => n >= corteAprobacionDecimas).length;

  int get reprobados => calificados - aprobados;

  int get porcentajeAprobados =>
      calificados == 0 ? 0 : (aprobados * 100 / calificados).round();

  /// Promedio en décimas, sin redondear.
  double get promedioDecimas =>
      calificados == 0 ? 0 : notas.fold<int>(0, (suma, n) => suma + n) / calificados;

  /// Cuántos estudiantes tienen cada nota, para el histograma.
  Map<int, int> get conteoPorNota {
    final conteo = <int, int>{};
    for (final n in notas) {
      conteo[n] = (conteo[n] ?? 0) + 1;
    }
    return conteo;
  }
}

/// El estado de la revisión: los datos de ejemplo más las decisiones tomadas en esta visita.
///
/// Es inmutable: decidir o deshacer devuelven una sesión nueva, y la pantalla solo la
/// reemplaza. Nada de esto se guarda; al recargar la página vuelve al ejemplo inicial.
class SesionRevision {
  const SesionRevision({
    required this.examen,
    required this.estudiantes,
    required this.casos,
    this.decisiones = const [],
  });

  factory SesionRevision.ejemplo() => const SesionRevision(
        examen: examenEjemplo,
        estudiantes: estudiantesEjemplo,
        casos: casosEjemplo,
      );

  final ExamenEjemplo examen;
  final List<EstudianteEjemplo> estudiantes;
  final List<CasoRevision> casos;
  final List<DecisionRevision> decisiones;

  bool _resuelto(CasoRevision caso) => decisiones.any((d) => d.caso.id == caso.id);

  List<CasoRevision> get pendientes => [
        for (final c in casos)
          if (!_resuelto(c)) c,
      ];

  EstudianteEjemplo estudianteDe(CasoRevision caso) =>
      estudiantes.firstWhere((e) => e.codigo == caso.codigoEstudiante);

  double puntosDe(EstudianteEjemplo estudiante) => decisiones
      .where((d) => d.caso.codigoEstudiante == estudiante.codigo)
      .fold(estudiante.puntos, (suma, d) => suma + d.veredicto.puntos);

  int notaDe(EstudianteEjemplo estudiante) => examen.notaEnDecimas(puntosDe(estudiante));

  /// La nota que tendría el estudiante del [caso] si el docente elige [veredicto] (RF-08).
  int notaCon(CasoRevision caso, Veredicto veredicto) =>
      examen.notaEnDecimas(puntosDe(estudianteDe(caso)) + veredicto.puntos);

  bool estaPendiente(EstudianteEjemplo estudiante) =>
      pendientes.any((c) => c.codigoEstudiante == estudiante.codigo);

  bool tuvoDobleMarcacion(EstudianteEjemplo estudiante) => casos.any(
        (c) => c.codigoEstudiante == estudiante.codigo && c.motivo == MotivoRevision.dobleMarcacion,
      );

  List<FilaEstudiante> get filas => [
        for (final e in estudiantes)
          FilaEstudiante(
            estudiante: e,
            notaDecimas: notaDe(e),
            pendiente: estaPendiente(e),
            dobleMarcacion: tuvoDobleMarcacion(e),
          ),
      ];

  ResumenNotas get resumen => ResumenNotas([
        for (final f in filas)
          if (!f.pendiente) f.notaDecimas,
      ]);

  SesionRevision decidir(CasoRevision caso, Veredicto veredicto) {
    final decision = DecisionRevision(
      caso: caso,
      veredicto: veredicto,
      notaAntes: notaDe(estudianteDe(caso)),
      notaDespues: notaCon(caso, veredicto),
    );
    return _con([...decisiones, decision]);
  }

  SesionRevision deshacer() =>
      decisiones.isEmpty ? this : _con(decisiones.sublist(0, decisiones.length - 1));

  SesionRevision _con(List<DecisionRevision> nuevas) => SesionRevision(
        examen: examen,
        estudiantes: estudiantes,
        casos: casos,
        decisiones: List.unmodifiable(nuevas),
      );
}

/// Las tres marcas dudosas del ejemplo. Cada una muestra un tipo de ambigüedad distinto: una
/// respuesta cambiada a medio borrar, dos respuestas marcadas y una marca tan tenue que define
/// si el estudiante aprueba.
const casosEjemplo = <CasoRevision>[
  CasoRevision(
    id: 'caso-1',
    codigoEstudiante: 'T00063218',
    pregunta: 5,
    tema: 'Regla de la cadena',
    enunciado: 'Calcule la derivada de',
    formula: 'f(x) = ln(cos(x))',
    peso: 1.0,
    clave: 'A',
    lecturas: [
      LecturaBurbuja('A', TipoMarca.tenue, 58),
      LecturaBurbuja('B', TipoMarca.vacia),
      LecturaBurbuja('C', TipoMarca.borron, 42),
      LecturaBurbuja('D', TipoMarca.vacia),
    ],
    explicacion:
        'Hay una marca tenue en A y un borrón en C, como si el estudiante hubiera cambiado de '
        'respuesta.',
  ),
  CasoRevision(
    id: 'caso-2',
    codigoEstudiante: 'T00061547',
    pregunta: 8,
    tema: 'Regla del producto',
    enunciado: 'Calcule la derivada de',
    formula: 'g(x) = x²·e^x',
    peso: 1.0,
    clave: 'B',
    lecturas: [
      LecturaBurbuja('A', TipoMarca.vacia),
      LecturaBurbuja('B', TipoMarca.completa, 64),
      LecturaBurbuja('C', TipoMarca.vacia),
      LecturaBurbuja('D', TipoMarca.completa, 61),
    ],
    explicacion:
        'Hay dos marcas completas, en B y en D. Con dos respuestas marcadas no se puede saber '
        'cuál quiso dejar el estudiante.',
    motivo: MotivoRevision.dobleMarcacion,
  ),
  CasoRevision(
    id: 'caso-3',
    codigoEstudiante: 'T00064090',
    pregunta: 12,
    tema: 'Límites trigonométricos',
    enunciado: 'Calcule el límite',
    formula: 'lím (x→0) sen(3x) / x',
    peso: 1.0,
    clave: 'C',
    lecturas: [
      LecturaBurbuja('A', TipoMarca.borron, 31),
      LecturaBurbuja('B', TipoMarca.vacia),
      LecturaBurbuja('C', TipoMarca.tenue, 49),
      LecturaBurbuja('D', TipoMarca.vacia),
    ],
    explicacion: 'Hay una marca muy tenue en C y un borrón en A.',
  ),
];

/// Los 43 estudiantes del parcial. Los tres primeros tienen una marca en revisión; el resto ya
/// está calificado. Nombres y códigos ficticios.
const estudiantesEjemplo = <EstudianteEjemplo>[
  EstudianteEjemplo(nombres: 'Valeria', apellidos: 'Montes Arrieta', codigo: 'T00063218', puntos: 10.5, confianzaOmr: 58),
  EstudianteEjemplo(nombres: 'Andrés Felipe', apellidos: 'Caraballo', codigo: 'T00061547', puntos: 8.0, confianzaOmr: 64),
  EstudianteEjemplo(nombres: 'Laura Daniela', apellidos: 'Pájaro Ruiz', codigo: 'T00064090', puntos: 6.5, confianzaOmr: 49),
  EstudianteEjemplo(nombres: 'Juan Camilo', apellidos: 'Herazo', codigo: 'T00062733', puntos: 12.0, confianzaOmr: 97),
  EstudianteEjemplo(nombres: 'Mariana', apellidos: 'Cuesta Villalba', codigo: 'T00063905', puntos: 12.5, confianzaOmr: 100),
  EstudianteEjemplo(nombres: 'Santiago', apellidos: 'Ospino Torres', codigo: 'T00060418', puntos: 11.5, confianzaOmr: 94),
  EstudianteEjemplo(nombres: 'Isabella', apellidos: 'Marimón Puello', codigo: 'T00064412', puntos: 11.5, confianzaOmr: 99),
  EstudianteEjemplo(nombres: 'Carlos Andrés', apellidos: 'Cabarcas Julio', codigo: 'T00061876', puntos: 11.0, confianzaOmr: 91),
  EstudianteEjemplo(nombres: 'María José', apellidos: 'Llerena Bolaño', codigo: 'T00062254', puntos: 11.0, confianzaOmr: 96),
  EstudianteEjemplo(nombres: 'Nicolás', apellidos: 'Simancas Pertuz', codigo: 'T00063561', puntos: 11.0, confianzaOmr: 88),
  EstudianteEjemplo(nombres: 'Daniela', apellidos: 'Fortich Olier', codigo: 'T00060937', puntos: 10.5, confianzaOmr: 98),
  EstudianteEjemplo(nombres: 'Luis Fernando', apellidos: 'Martelo Díaz', codigo: 'T00064728', puntos: 10.5, confianzaOmr: 93),
  EstudianteEjemplo(nombres: 'Camila Andrea', apellidos: 'Barrios Tous', codigo: 'T00061203', puntos: 10.5, confianzaOmr: 90),
  EstudianteEjemplo(nombres: 'Alejandro', apellidos: 'Rodelo Payares', codigo: 'T00062980', puntos: 10.5, confianzaOmr: 85),
  EstudianteEjemplo(nombres: 'Sofía', apellidos: 'Batista Amador', codigo: 'T00063342', puntos: 10.0, confianzaOmr: 97),
  EstudianteEjemplo(nombres: 'Diego Alejandro', apellidos: 'Guerrero Polo', codigo: 'T00060655', puntos: 10.0, confianzaOmr: 92),
  EstudianteEjemplo(nombres: 'Natalia', apellidos: 'Zúñiga Cassiani', codigo: 'T00064186', puntos: 10.0, confianzaOmr: 99),
  EstudianteEjemplo(nombres: 'Jorge Luis', apellidos: 'Pacheco Rangel', codigo: 'T00061724', puntos: 10.0, confianzaOmr: 87),
  EstudianteEjemplo(nombres: 'Paula Andrea', apellidos: 'Navarro Ballestas', codigo: 'T00062419', puntos: 10.0, confianzaOmr: 95),
  EstudianteEjemplo(nombres: 'Kevin', apellidos: 'Mercado Daza', codigo: 'T00063077', puntos: 9.5, confianzaOmr: 82),
  EstudianteEjemplo(nombres: 'Ana María', apellidos: 'Benítez Orozco', codigo: 'T00060291', puntos: 9.5, confianzaOmr: 96),
  EstudianteEjemplo(nombres: 'Miguel Ángel', apellidos: 'Romero Castilla', codigo: 'T00064533', puntos: 9.5, confianzaOmr: 90),
  EstudianteEjemplo(nombres: 'Valentina', apellidos: 'Ricardo Gaviria', codigo: 'T00061458', puntos: 9.5, confianzaOmr: 94),
  EstudianteEjemplo(nombres: 'Samuel', apellidos: 'Contreras Rhenals', codigo: 'T00062806', puntos: 9.5, confianzaOmr: 79),
  EstudianteEjemplo(nombres: 'Manuela', apellidos: 'Castillo Ahumada', codigo: 'T00063629', puntos: 9.0, confianzaOmr: 98),
  EstudianteEjemplo(nombres: 'Esteban', apellidos: 'Mendoza Lambis', codigo: 'T00060874', puntos: 9.0, confianzaOmr: 91),
  EstudianteEjemplo(nombres: 'Juliana', apellidos: 'Puerta Ochoa', codigo: 'T00064315', puntos: 9.0, confianzaOmr: 86),
  EstudianteEjemplo(nombres: 'David Santiago', apellidos: 'Bello Acosta', codigo: 'T00061932', puntos: 9.0, confianzaOmr: 93),
  EstudianteEjemplo(nombres: 'Melissa', apellidos: 'Teherán Correa', codigo: 'T00062561', puntos: 8.5, confianzaOmr: 97),
  EstudianteEjemplo(nombres: 'José Daniel', apellidos: 'Banquez Cervantes', codigo: 'T00063194', puntos: 8.5, confianzaOmr: 74),
  EstudianteEjemplo(nombres: 'Karen Lorena', apellidos: 'Villadiego Paternina', codigo: 'T00060512', puntos: 8.5, confianzaOmr: 89),
  EstudianteEjemplo(nombres: 'Óscar Iván', apellidos: 'Montero Altamar', codigo: 'T00064871', puntos: 8.5, confianzaOmr: 92),
  EstudianteEjemplo(nombres: 'Luisa Fernanda', apellidos: 'Royero Meza', codigo: 'T00061369', puntos: 8.0, confianzaOmr: 95),
  EstudianteEjemplo(nombres: 'Mateo', apellidos: 'Gutiérrez Anaya', codigo: 'T00062147', puntos: 8.0, confianzaOmr: 88),
  EstudianteEjemplo(nombres: 'Ximena', apellidos: 'Padilla Blanco', codigo: 'T00063786', puntos: 8.0, confianzaOmr: 99),
  EstudianteEjemplo(nombres: 'Felipe', apellidos: 'Hoyos Coneo', codigo: 'T00060163', puntos: 7.5, confianzaOmr: 81),
  EstudianteEjemplo(nombres: 'Tatiana', apellidos: 'Escorcia Marrugo', codigo: 'T00064657', puntos: 7.5, confianzaOmr: 94),
  EstudianteEjemplo(nombres: 'Julián David', apellidos: 'Ortiz Cantillo', codigo: 'T00061085', puntos: 7.5, confianzaOmr: 72),
  EstudianteEjemplo(nombres: 'Angie Paola', apellidos: 'Sierra Lora', codigo: 'T00062692', puntos: 7.0, confianzaOmr: 90),
  EstudianteEjemplo(nombres: 'Brayan Estiven', apellidos: 'Garcés Ospina', codigo: 'T00063453', puntos: 7.0, confianzaOmr: 84),
  EstudianteEjemplo(nombres: 'Gabriela', apellidos: 'Jiménez Tovar', codigo: 'T00060749', puntos: 6.5, confianzaOmr: 77),
  EstudianteEjemplo(nombres: 'Emmanuel', apellidos: 'Narváez Cohen', codigo: 'T00064264', puntos: 6.0, confianzaOmr: 93),
  EstudianteEjemplo(nombres: 'Sara Lucía', apellidos: 'Peñaloza Arango', codigo: 'T00061611', puntos: 5.0, confianzaOmr: 86),
];
