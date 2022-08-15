#Importacion de librerias
from PyQt5 import QtWidgets
from components import Settings, Database as db, ScheduleParser
from py_ui import Result as Parent
import pickle
import json
import csv
import copy

#Clase donde se detalla los resultados de la vista
class ResultViewer:
    def __init__(self):
        self.dialog = dialog = QtWidgets.QDialog()
        # Initialize custom dialog
        self.parent = parent = Parent.Ui_Dialog()
        # Add parent to custom dialog
        parent.setupUi(dialog)
        self.table = self.parent.tableResult
        self.run = True
        self.settings = Settings.getSettings()
        self.result = { 'data': [] }
        self.getLastResult()
        if self.run:
            self.parseResultDetails()
            self.connectWidgets()
            self.updateTable(0)
            dialog.exec_()
    #Función donde se obtienen los ultimos resultados generados
    def getLastResult(self):
        conn = db.getConnection()
        cursor = conn.cursor()
        cursor.execute('SELECT content FROM results WHERE id = (SELECT MAX(id) FROM results)')
        result = cursor.fetchone()
        conn.close()
        if result:
            self.result = pickle.loads(result[0])
        else:
            messageBox = QtWidgets.QMessageBox()
            messageBox.setWindowTitle('No hay datos')
            messageBox.setIcon(QtWidgets.QMessageBox.Information)
            messageBox.setText('Tu no has generado una solucion aun!')
            messageBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            messageBox.exec_()
            self.run = False
    #Funcion donde se detallan  los resultados obtenidos de la generacion del horario
    def parseResultDetails(self):
        if not len(self.result['data']):
            return False
        result = self.result
        self.rawData = copy.deepcopy(result['rawData'])
        self.parent.lblTime.setText('Generacion de tiempo: {}'.format(result['time']))
        self.parent.lblCPU.setText('Promedio de CPU usada: {}%'.format(round(result['resource']['cpu']), 2))
        self.parent.lblMemory.setText('Promedio de memoria usada: {} MB'.format(round(result['resource']['memory']), 2))
        self.updateEntries(0)
        self.updateDetails(0)
    #Funcion donde se configura la conexion con lo widgets
    def connectWidgets(self):
        self.parent.cmbChromosome.currentIndexChanged.connect(self.updateDetails)
        self.parent.cmbCategory.currentIndexChanged.connect(self.updateEntries)
        self.parent.cmbEntry.currentIndexChanged.connect(self.updateTable)
        self.parent.btnExport.clicked.connect(self.export)
    #Funcion donde se actualizan los detalles de la configuracion
    def updateDetails(self, index):
        parent = self.parent
        meta = self.result['meta'][index]
        parent.lblFit.setText('Total Ajuste: {}%'.format(meta[0]))
        parent.lblSbj.setText('Cursos ubicados: {}%'.format(meta[1][0]))
        parent.lblSecRest.setText('Resto de sección: {}%'.format(meta[1][2]))
        parent.lblSecIdle.setText('Tiempo de inactividad de la sección: {}%'.format(meta[1][4]))
        parent.lblInstrRest.setText('Descanso del instructor: {}%'.format(meta[1][3]))
        parent.lblInstrLoad.setText('Carga de instructores: {}%'.format(meta[1][6]))
        parent.lblLunch.setText('Pausa para almorzar: {}%'.format(meta[1][1]))
        parent.lblMeet.setText('Patrón de reunión: {}%'.format(meta[1][5]))
        parent.cmbCategory.setCurrentIndex(0)
        parent.cmbEntry.setCurrentIndex(0)
        self.updateEntries(0)
        self.updateTable(0)
    #Funcion donde se actualizan las entradas a la generación de los horarios
    def updateEntries(self, index):
        if index == 0:
            key = 'secciones'
        elif index == 1:
            key = 'aulas'
        else:
            key = 'instructores'
        self.entryKeys = []
        self.changingKeys = True
        self.parent.cmbEntry.clear()
        for id, entry in self.rawData[key].items():
            self.entryKeys.append(id)
            self.parent.cmbEntry.addItem(entry[0])
        self.changingKeys = False
        self.updateTable(self.parent.cmbEntry.currentIndex())
    #Funciones donde se pueden actualizar tablas
    def updateTable(self, index):
        if self.changingKeys:
            return False
        chromosome = self.result['data'][self.parent.cmbChromosome.currentIndex()]
        category = self.parent.cmbCategory.currentIndex()
        # {secId: {'details': {sbjId: [roomId, instructorId, [day/s], startingTS, length]}}}
        secciones = chromosome['secciones']
        rawData = self.rawData
        data = []
        # Section
        if category == 0:
            subjects = sections[self.entryKeys[index]]['details']
            for subject, details in subjects.items():
                if not len(details):
                    continue
                instructor = '' if not details[1] else rawData['instructores'][details[1]][0]
                data.append({'color': None, 'text': '{} \n {} \n {}'.format(rawData['subjects'][subject][2],
                                                                            rawData['aulas'][details[0]][0],
                                                                            instructor),
                             'instances': [[day, details[3], details[3] + details[4]] for day in details[2]]})
        # Room
        elif category == 1:
            for section, details in sections.items():
                for subject, subjectDetail in details['details'].items():
                    if not len(subjectDetail):
                        continue
                    if subjectDetail[0] != self.entryKeys[index]:
                        continue
                    instructor = '' if not subjectDetail[1] else rawData['instructores'][subjectDetail[1]][0]
                    data.append({'color': None, 'text': '{} \n {} \n {}'.format(rawData['subjects'][subject][2],
                                                                                rawData['secciones'][section][0],
                                                                                instructor),
                                 'instances': [[day, subjectDetail[3], subjectDetail[3] + subjectDetail[4]] for day in
                                               subjectDetail[2]]})
        # Instructor
        else:
            for section, details in sections.items():
                for subject, subjectDetail in details['details'].items():
                    if not len(subjectDetail):
                        continue
                    if subjectDetail[1] != self.entryKeys[index]:
                        continue
                    data.append({'color': None, 'text': '{} \n {} \n {}'.format(rawData['subjects'][subject][2],
                                                                                rawData['aulas'][subjectDetail[0]][0],
                                                                                rawData['secciones'][section][0]),
                                 'instances': [[day, subjectDetail[3], subjectDetail[3] + subjectDetail[4]] for day in
                                               subjectDetail[2]]})
        self.loadTable(data)
    #Funcion donde cargamos la tabla
    def loadTable(self, data=[]):
        self.table.reset()
        self.table.clearSpans()
        ScheduleParser.ScheduleParser(self.table, data)
    #Funcion donde se exporta la carga de horarios
    def export(self):
        directory = QtWidgets.QFileDialog().getExistingDirectory(None, 'Seleccionar directorio para exportar')
        if not directory:
            return False
        with open('timeslots.json') as json_file:
            timeslots = json.load(json_file)['timeslots']
        fieldnames = ['Tiempo', 'Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado']
        rawData = self.rawData
        chromosome = self.result['data'][self.parent.cmbChromosome.currentIndex()]
        # Create schedule for sections
        with open('{}/sections_schedule.csv'.format(directory), 'w', newline='') as file:
            writer = csv.writer(file, dialect='excel')
            for section, subjects in chromosome['secciones'].items():
                writer.writerow([self.rawData['secciones'][section][0]])
                writer.writerow(fieldnames)
                schedule = [['' for j in range(6)] for i in
                            range(self.settings['ending_time'] - self.settings['starting_time'] + 1)]
                for subject, details in subjects['details'].items():
                    if not len(details):
                        continue
                    instructor = '' if not details[1] else rawData['instructores'][details[1]][0]
                    for timeslot in range(details[3], details[3] + details[4]):
                        for day in details[2]:
                            schedule[timeslot][day] = '{} - {} - {}'.format(rawData['subjects'][subject][2],
                                                                            rawData['aulas'][details[0]][0],
                                                                            instructor)
                for timeslot in range(self.settings['starting_time'], self.settings['ending_time'] + 1):
                    writer.writerow([timeslots[timeslot], *schedule[timeslot - self.settings['starting_time']]])
                writer.writerow([''])
        # Create schedule for instructors
        with open('{}/instructors_schedule.csv'.format(directory), 'w', newline='') as file:
            writer = csv.writer(file, dialect='excel')
            for instructor in rawData['instructores'].keys():
                writer.writerow([rawData['instructores'][instructor][0]])
                writer.writerow(fieldnames)
                schedule = [['' for j in range(6)] for i in
                            range(self.settings['ending_time'] - self.settings['starting_time'] + 1)]
                for section, subjects in chromosome['secciones'].items():
                    for subject, details in subjects['details'].items():
                        if not len(details) or details[1] != instructor:
                            continue
                        for timeslot in range(details[3], details[3] + details[4]):
                            for day in details[2]:
                                schedule[timeslot][day] = '{} - {} - {}'.format(rawData['subjects'][subject][2],
                                                                                rawData['aulas'][details[0]][0],
                                                                                rawData['secciones'][section][0])
                    for timeslot in range(self.settings['starting_time'], self.settings['ending_time'] + 1):
                        writer.writerow([timeslots[timeslot], *schedule[timeslot - self.settings['starting_time']]])
                writer.writerow([''])
        # Create schedule for rooms
        with open('{}/rooms_schedule.csv'.format(directory), 'w', newline='') as file:
            writer = csv.writer(file, dialect='excel')
            for room in rawData['rooms'].keys():
                writer.writerow([rawData['rooms'][room][0]])
                writer.writerow(fieldnames)
                schedule = [['' for j in range(6)] for i in
                            range(self.settings['ending_time'] - self.settings['starting_time'] + 1)]
                for section, subjects in chromosome['secciones'].items():
                    for subject, details in subjects['details'].items():
                        if not len(details) or details[0] != room:
                            continue
                        instructor = '' if not details[1] else rawData['instructores'][details[1]][0]
                        for timeslot in range(details[3], details[3] + details[4]):
                            for day in details[2]:
                                schedule[timeslot][day] = '{} - {} - {}'.format(rawData['subjects'][subject][2],
                                                                                rawData['secciones'][section][0],
                                                                                instructor)
                for timeslot in range(self.settings['starting_time'], self.settings['ending_time'] + 1):
                    writer.writerow([timeslots[timeslot], *schedule[timeslot - self.settings['starting_time']]])
                writer.writerow([''])
