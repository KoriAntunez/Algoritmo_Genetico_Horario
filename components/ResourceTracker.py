import os
import psutil # módulo que provee una interfaz para obtener información de un determinado proceso y su utilización del sistema.


def getCPUUsage():
    return psutil.cpu_percent(1) #método se usa para devolver la utilización actual de la CPU en todo el sistema como un porcentaje.


def getMemoryUsage():
    return [psutil.Process(os.getpid()).memory_info()[0], psutil.virtual_memory()[0]]
    # proporciona el uso de la memoria del sistema en bytes

def getMemoryPercentage(memoryUsage):
    return round((memoryUsage[0] / memoryUsage[1]) * 100, 2) #Obtiene el porcentaje de uso de la memoria


def byteToMegabyte(byte):
    return round(byte / 1048576, 2)
