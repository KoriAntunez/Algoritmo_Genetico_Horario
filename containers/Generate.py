#Importación de libreria
from PyQt5 import QtCore, QtWidgets
from components import Database as db, ResourceTracker, ScheduleParser, ScenarioComposer, GeneticAlgorithm
from py_ui import Generate as Parent
from sqlite3 import Binary
from numpy import mean
import pickle
import copy

##Función principal que declara todos los elementos que se van a usar en las otras funciones
class Generate:
    def __init__(self):
        self.totalResource = {
            'cpu': [],
            'memoria': []
        }
        self.tick = 0
        self.data = {
            'resultados': [],
            'aulas': [],
            'instructores': [],
            'secciones': [],
            'reuniones': [],
            'materias': []
        }
        self.topChromosomes = []
        self.meta = []
        self.preview = True
        self.sectionKeys = []
        composer = ScenarioComposer.ScenarioComposer()
        composer = composer.getScenarioData()
        self.data.update(composer)
        self.dialog = dialog = QtWidgets.QDialog(parent=None)
        # Initialize custom dialog
        self.parent = parent = Parent.Ui_Dialog()
        # Add parent to custom dialog
        parent.setupUi(dialog)
        dialog.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowTitleHint | QtCore.Qt.CustomizeWindowHint)
        self.time = QtCore.QTime(0, 0)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updateTime)
        self.timer.start(1000)
        self.running = True
        self.table = parent.tableSchedule
        parent.btnPause.clicked.connect(self.togglePause)
        parent.btnStop.clicked.connect(self.stopOperation)
        parent.chkPreview.clicked.connect(self.togglePreview)
        parent.cmbSection.clear()
        for section, details in self.data['secciones'].items():
            self.sectionKeys.append(section)
            parent.cmbSection.addItem(details[0])
        parent.cmbSection.currentIndexChanged.connect(self.changePreview)
        self.startWorkers()
        dialog.exec_()

# Función Muestra la opción de vista previa
    def togglePreview(self, state):
        self.preview = not state
# Funcion que detalla la generación resumen 
    def togglePause(self):
        self.toggleState()
        self.parent.btnPause.setText('Generación en pausa' if self.running else 'Generacion resumen')
#Función donde se activa la generación del horario
    def toggleState(self, state=None):
        self.running = (not self.running) if state is None else state
        self.resourceWorker.running = self.running
        self.geneticAlgorithm.running = self.running
#Funcion donde se da inicio a los trabajadores
    def startWorkers(self):
        self.resourceWorker = ResourceTrackerWorker()
        self.resourceWorker.signal.connect(self.updateResource)
        self.resourceWorker.start()
        self.geneticAlgorithm = GeneticAlgorithm.GeneticAlgorithm(self.data)
        self.geneticAlgorithm.statusSignal.connect(self.updateStatus)
        self.geneticAlgorithm.detailsSignal.connect(self.updateDetails)
        self.geneticAlgorithm.dataSignal.connect(self.updateView)
        self.geneticAlgorithm.operationSignal.connect(self.updateOperation)
        self.geneticAlgorithm.start()
#Función donde se actualiza el estado
    def updateStatus(self, status):
        self.parent.lblStatus.setText('Status: {}'.format(status))
#Funcion donde se actualizan los detalles
    def updateDetails(self, details):
        self.parent.boxGen.setTitle('Generation #{}'.format(details[0]))
        self.parent.lblPopulation.setText('Population: {}'.format(details[1]))
        self.parent.lblMutation.setText('Mutation Rate: {}%'.format(details[2]))
        self.parent.lblFitness.setText('Average Fitness: {}%'.format(details[3]))
        self.parent.lblPreviousFitness.setText('Previous Average Fitness: {}%'.format(details[4]))
        self.parent.lblHighestFitness.setText('Highest Fitness: {}%'.format(details[5]))
        self.parent.lblLowestFitness.setText('Lowest Fitness: {}%'.format(details[6]))
#Función donde se actualiza la vista en base a los cromosomas ingresados
    def updateView(self, chromosomes):
        chromosomes.reverse()
        self.topChromosomes = copy.deepcopy(chromosomes)
        self.changePreview(self.parent.cmbSection.currentIndex())
#Funcion donde se hace cambio de la vista previa
    def changePreview(self, index):
        data = []
        if not len(self.topChromosomes) or not self.preview:
            return False
        secciones = self.topChromosomes[0][0].data['secciones']
        rawData = self.data
        materias = secciones[self.sectionKeys[index]]['details']
        for subject, details in materias.items():
            if not len(details):
                continue
            instructor = '' if not details[1] else rawData['instructores'][details[1]][0]
            data.append({'color': None, 'text': '{} \n {} \n {}'.format(rawData['materias'][subject][0],
                                                                        rawData['aulas'][details[0]][0],
                                                                        instructor),
                         'instances': [[day, details[3], details[3] + details[4]] for day in details[2]]})
        self.loadTable(data)
#Funcion donde se acrualiza la tabla del horario
    def loadTable(self, data=[]):
        self.table.reset()
        self.table.clearSpans()
        ScheduleParser.ScheduleParser(self.table, data)
#Funcion donde se actualiza la operacion
    def updateOperation(self, type):
        if type == 1:
            self.stopOperation()

#Funcion donde se actualiza el tiempo transcurrido 
    def updateTime(self):
        self.time = self.time.addSecs(1)
        self.parent.lblTime.setText('Tiempo transcurrido: {}'.format(self.time.toString('hh:mm:ss')))
#Funcion donde se paran las operaciones 
    def stopOperation(self):
        self.toggleState(False)
        self.resourceWorker.terminate()
        self.resourceWorker.runThread = False
        self.geneticAlgorithm.terminate()
        self.timer.stop()
        if len(self.topChromosomes):
            self.parent.btnStop.setText('Ver resultados')
            self.parent.btnStop.clicked.disconnect(self.stopOperation)
            self.parent.btnStop.clicked.connect(self.dialog.close)
            self.parent.lblCPU.setText('Uso de CPU: detenido')
            self.parent.lblmemoria.setText('memoria Uso: Detenido')
            self.parent.lblStatus.setText('Estado: Detenido')
            self.totalResource['cpu'] = mean(self.totalResource['cpu'])
            self.totalResource['memoria'] = mean(self.totalResource['memoria'])
            self.meta = [[chromosome[1], chromosome[0].fitnessDetails] for chromosome in
                         self.topChromosomes]
            conn = db.getConnection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO resultados (content) VALUES (?)', [Binary(
                pickle.dumps({'datos': [chromosome[0].data for chromosome in self.topChromosomes],
                              'meta': self.meta,
                              'tiempo': self.time.toString('hh:mm:ss'),
                              'recursos': self.totalResource,
                              'datos sin procesar': self.data},
                             pickle.HIGHEST_PROTOCOL))])
            conn.commit()
            conn.close()
        else:
            self.dialog.close()
#Función donde se actualizan los recursos
    def updateResource(self, resource):
        self.tick += 1
        if self.tick == 3:
            self.tick = 0
        else:
            self.totalResource['cpu'].append(resource[0])
            self.totalResource['memoria'].append(resource[1][1])
        self.parent.lblCPU.setText('CPU Usage: {}%'.format(resource[0]))
        self.parent.lblMemory.setText('Memory Usage: {}% - {} MB'.format(resource[1][0], resource[1][1]))

#Función donde se crea al trabajado de seguimiento de recursos
class ResourceTrackerWorker(QtCore.QThread):
    signal = QtCore.pyqtSignal(object)
    running = True
    runThread = True

    def __init__(self):
        super().__init__()

    def __del__(self):
        self.wait()
#Funcion donde se hacen uso de los recursos declarados
    def run(self):
        while (self.runThread):
            self.sleep(1)
            if self.running is True:
                cpu = ResourceTracker.getCPUUsage()
                memoria = ResourceTracker.getMemoryUsage()
                memoria = [ResourceTracker.getMemoryPercentage(memoria), ResourceTracker.byteToMegabyte(memoria[0])]
                self.signal.emit([cpu, memoria])
        return True
