"""Limita la CPU de un proceso y muestrea la CPU y la memoria, sin Docker.

Repite en una máquina sin Docker los límites de `deploy/compose.lab.yaml` que usó la medición del
6-nov: el worker con 0,25 CPU y la API con 0,5. Hace lo mismo que `cpulimit`: en cada período de
100 ms deja correr el proceso la fracción indicada y lo detiene el resto (SIGSTOP y SIGCONT). La
memoria no se limita: se mide, para compararla con el tope. VmRSS cuenta también las páginas de las
bibliotecas (NumPy y OpenCV), que se leen del disco y el kernel puede soltar; RssAnon es la memoria
propia del proceso, la que no se puede soltar, y es la que se compara con el tope.

Cada 2 s escribe en la salida estándar una línea JSON con la CPU de cada proceso (en fracción de un
núcleo), su memoria residente y la CPU de toda la máquina. El archivo lo elige quien la llama, con
una redirección: así el script no recibe ninguna ruta por la línea de comandos (SonarCloud, S8707).

    python limitar.py worker:<pid>:0.25 api:<pid>:0.5 > muestras.jsonl
"""

import argparse
import json
import os
import signal
import sys
import threading
import time

PERIODO_S = 0.1
TICKS = os.sysconf("SC_CLK_TCK")


def limitar(pid: int, fraccion: float, parar: threading.Event) -> None:
    corre, detenido = PERIODO_S * fraccion, PERIODO_S * (1 - fraccion)
    try:
        while not parar.is_set():
            os.kill(pid, signal.SIGCONT)
            time.sleep(corre)
            os.kill(pid, signal.SIGSTOP)
            time.sleep(detenido)
    except ProcessLookupError:
        return
    finally:
        try:
            os.kill(pid, signal.SIGCONT)
        except ProcessLookupError:
            pass


def cpu_del_proceso(pid: int) -> float:
    with open(f"/proc/{pid}/stat") as archivo:
        campos = archivo.read().rsplit(")", 1)[1].split()
    return (int(campos[11]) + int(campos[12])) / TICKS  # utime + stime, en segundos


def memoria(pid: int) -> dict[str, float]:
    datos = {}
    with open(f"/proc/{pid}/status") as archivo:
        for linea in archivo:
            if linea.startswith(("VmRSS:", "VmHWM:", "RssAnon:", "RssFile:")):
                datos[linea.split(":")[0]] = round(int(linea.split()[1]) / 1024, 1)  # MiB
    return datos


def cpu_de_la_maquina() -> tuple[int, int]:
    with open("/proc/stat") as archivo:
        valores = [int(v) for v in archivo.readline().split()[1:]]
    return sum(valores), valores[3] + valores[4]  # total, ocioso + espera de disco


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("procesos", nargs="+", help="nombre:pid:fraccion")
    args = parser.parse_args()
    procesos = [(n, int(p), float(f)) for n, p, f in (x.split(":") for x in args.procesos)]
    parar = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: parar.set())
    hilos = [threading.Thread(target=limitar, args=(p, f, parar), daemon=True)
             for _, p, f in procesos]
    for hilo in hilos:
        hilo.start()
    nucleos = os.cpu_count() or 1
    antes = {n: cpu_del_proceso(p) for n, p, _ in procesos}
    maquina_antes, t_antes = cpu_de_la_maquina(), time.monotonic()
    salida = sys.stdout
    while not parar.wait(2):
        ahora, t = {}, time.monotonic()
        muestra = {"t": round(time.time(), 1)}
        try:
            for nombre, pid, _ in procesos:
                ahora[nombre] = cpu_del_proceso(pid)
                muestra[nombre] = {"cpu": round((ahora[nombre] - antes[nombre]) / (t - t_antes), 3),
                                   **memoria(pid)}
        except (FileNotFoundError, ProcessLookupError):
            break
        maquina = cpu_de_la_maquina()
        total, ocioso = maquina[0] - maquina_antes[0], maquina[1] - maquina_antes[1]
        muestra["maquina_cpu"] = round(1 - ocioso / total, 3) if total else 0.0
        muestra["nucleos"] = nucleos
        salida.write(json.dumps(muestra) + "\n")
        salida.flush()
        antes, maquina_antes, t_antes = ahora, maquina, t
    parar.set()
    for hilo in hilos:
        hilo.join(1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
