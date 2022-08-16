#Importacion de la librerias
from PyQt5 import QtWidgets, QtGui
from components import Database as db
from py_ui import Share as Parent
import json

# Clase que ilustra un horario compartido
class Share:
    def __init__(self, subject_id, section_id):
        self.id = int(subject_id)
        self.section_id = int(section_id)
        self.shareId = False
        self.shareMembersText = False
        # Nueva instancia de diálogo
        self.dialog = dialog = QtWidgets.QDialog()
        # Se inicializa cuadro de diálogo personalizado
        self.parent = parent = Parent.Ui_Dialog()
        # Se agrega clase padre al cuadro de diálogo personalizado
        parent.setupUi(dialog)
        # Conectando el widget de horario con el modelo de horario personalizado
        self.setSharings()
        parent.btnFinish.clicked.connect(self.finish)
        parent.btnCancel.clicked.connect(self.dialog.close)
        dialog.exec_()
    # Método que obtiene data de la Clase Sharing
    def getShareData(self):
        return tuple([self.shareId, self.shareMembersText])
    #
    def setSharings(self):
        self.tree = tree = self.parent.treeSections
        self.model = model = QtGui.QStandardItemModel()
        model.setHorizontalHeaderLabels(['ID', 'Sections', 'SectionID'])
        tree.setModel(model)
        tree.setColumnHidden(0, True)
        tree.setColumnHidden(2, True)
        model.itemChanged.connect(lambda item: self.toggleSharing(item))
        conn = db.getConnection()
        cursor = conn.cursor()
        # Obtiene secciones con clases mutuas
        if self.section_id:
            cursor.execute('SELECT id, name, subjects FROM sections WHERE active = 1 AND id != ?', [self.section_id])
        else:
            cursor.execute('SELECT id, name, subjects FROM sections WHERE active = 1')
        sections = cursor.fetchall()
        cursor.execute('SELECT id, sections FROM sharings WHERE subjectId = ? AND final = 1', [self.id])
        sharings = cursor.fetchall()
        sharedSections = list(set([section for sectionGroup in list(
            map(lambda sharing: list(map(lambda id: int(id), json.loads(sharing[1]))), sharings)) for section in
                                   sectionGroup]))
        sharings = dict(sharings)
        conn.close()
        sectionDict = {}
        for section in sections:
            sectionDict[section[0]] = section[1]
            if self.id not in list(map(lambda id: int(id), json.loads(section[2]))) or section[0] in sharedSections:
                continue
            id = QtGui.QStandardItem()
            id.setEditable(False)
            sectionList = QtGui.QStandardItem(section[1])
            sectionList.setEditable(False)
            sectionID = QtGui.QStandardItem(str(section[0]))
            sectionID.setEditable(False)
            self.model.appendRow([id, sectionList, sectionID])
        for key, value in sharings.items():
            sectionIDList = list(map(lambda id: int(id), json.loads(value)))
            if self.section_id in sectionIDList:
                continue
            id = QtGui.QStandardItem(str(key))
            sectionList = QtGui.QStandardItem(', '.join(list(map(lambda id: sectionDict[id], sectionIDList))))
            sectionList.setEditable(False)
            sectionID = QtGui.QStandardItem(','.join(map(str, sectionIDList)))
            self.model.appendRow([id, sectionList, sectionID])
     # Método para editar/eliminar secciones con clases mutuas
    def finish(self):
        if not self.tree.selectedIndexes():
            return False
        shareId = self.model.item(self.tree.selectedIndexes()[0].row()).text()
        shareId = False if not shareId else shareId
        conn = db.getConnection()
        cursor = conn.cursor()
        if not shareId:
            cursor.execute('INSERT INTO sharings (subjectId, sections) VALUES (?, ?)', [self.id, json.dumps(
                [self.section_id, self.model.item(self.tree.selectedIndexes()[0].row(), 2).text()])])
            self.shareId = cursor.lastrowid
        else:
            subjectID = self.model.item(self.tree.selectedIndexes()[0].row(), 2).text().split(',')
            subjectID.append(self.section_id)
            cursor.execute('UPDATE sharings SET sections = ? WHERE id = ?', [json.dumps(subjectID), shareId])
            self.shareId = shareId
        conn.commit()
        conn.close()
        self.shareMembersText = self.model.item(self.tree.selectedIndexes()[0].row(), 1).text()
        self.dialog.close()
