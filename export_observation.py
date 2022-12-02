# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ExportObservation
                                 A QGIS plugin
 This plugin ...
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2022-11-27
        git sha              : $Format:%H$
        copyright            : (C) 2022 by Sergio Costa
        email                : sergio.costa@ufma.br
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QTableWidgetItem, QTableWidget, QCheckBox, QComboBox, QLineEdit, QFileDialog

from qgis.core import QgsProject, Qgis

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .export_observation_dialog import ExportObservationDialog
import os.path

import uuid 

from functools import partial

import re



plugin_dir = os.path.dirname(__file__)

try:
    import pip
except:
    exec(open(os.path.join(plugin_dir, "get_pip.py")).read())
    import pip
    # just in case the included version is old
    pip.main(['install','--upgrade','pip'])

try:
    import simpot
except:
    pip.main(['install', 'simpot'])

try:
    import rdflib
except:
    pip.main(['install', 'rdflib'])


from rdflib import Namespace, Literal, URIRef,RDF, Graph

from rdflib.namespace import DC, FOAF

from simpot import serialize_to_rdf, serialize_to_rdf_file, RdfsClass, BNamespace, graph


namespaces = {
    'cell': (Namespace("http://purl.org/ontology/dbcells/cells"), 'ttl'),
    #'geo' : (Namespace ("http://www.opengis.net/ont/geosparql"), 'xml'),
    'sdmx' : (Namespace ("http://purl.org/linked-data/sdmx/2009/dimension"), 'ttl'),
    'amz' : (Namespace ("http://purl.org/ontology/dbcells/amazon"), "ttl")
}


AMZ =  namespaces['amz'][0]
CELL = namespaces['cell'][0]
SDMX = namespaces['sdmx'][0]
#GEO = namespaces['geo'][0]

QB = Namespace ("http://purl.org/linked-data/cube/")

def validade_url(s):
    if (type(s) != str ):
        return False

    regex = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    return (re.match(regex, s) is not None) 


def parse_ifs(value):
  if value is None:
      return ""
  try:
      n = int(value)
      return n
  except:
      try: 
        n = float (value)
        return n
      except:
        return value


class Observation ():
    

    
    @RdfsClass(QB.Observation,"http://www.dbcells.org/amazon/observations/")
    @BNamespace('qb', QB)
    @BNamespace('amz', AMZ)
    @BNamespace('sdmx', SDMX)
    @BNamespace('cell', CELL)
    def __init__(self, dict):
        self.id = dict["obs_id"] # problema com os ids
        dict.pop("obs_id")

        for key in dict:
            #print (dict[key], key)
            if (validade_url(dict[key])): # talvez deveria ver pelo schema
                setattr(self, key, URIRef(dict[key]))    
            else:
                setattr(self, key, Literal(dict[key]))


class ExportObservation:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'ExportObservation_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&DBCells')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

        self.concepts = []
        self.fields_name = []

        self.load_vocabularies()

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('ExportObservation', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/export_observation/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'&Export Observation'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&Export Observation'),
                action)
            self.iface.removeToolBarIcon(action)


    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = ExportObservationDialog()


        self.dlg.buttonLoad.clicked.connect(self.load_fill)
        self.dlg.buttonTTL.clicked.connect(self.output_file)
        self.dlg.buttonBox.accepted.connect(self.saveFile)

        self.dlg.button_load_layer.clicked.connect(self.load_fields)
        self.fill_table(0)

        self.dlg.tableAttributes.cellActivated.connect(self.cell_activate)

        layers_names = []
        for layer in QgsProject.instance().mapLayers().values():
            layers_names.append(layer.name())
            self.dlg.comboLayer.addItem(layer.name())

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

    def load_fields(self):
        self.layer = QgsProject.instance().mapLayersByName(self.dlg.comboLayer.currentText())[0]
        self.fields_name = []

        fields = self.layer.fields()
        for field in fields:
            self.fields_name.append(field.name())

        self.fill_table(0)

        self.iface.messageBar().pushMessage(
            "Success", "Load Layer fields",
            level=Qgis.Success, duration=3
        )
    
    def attributes_combo(self):
        comboBox = QComboBox()
        for attr in self.fields_name:
            comboBox.addItem(attr)
        return comboBox



    def load_vocabulary(self, prefix, namespace, format):
        g = Graph()
        g.parse(namespace, format=format)
        q = """
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX owl: <http://www.w3.org/2002/07/owl#>

            SELECT ?p
            WHERE 
            {
               { ?p rdf:type owl:DatatypeProperty} UNION
               { ?p rdf:type owl:ObjectProperty} UNION
               { ?p rdf:type rdf:Property}    
            }
        """

        # Apply the query to the graph and iterate through results
        
        i = len(self.concepts) # o inicial para adicionar no table attributues

        for r in g.query(q):
            attr = r["p"].split("#") 
            name = prefix+":"+attr[1]
            self.concepts.append(name)


    def load_fill(self):
        #namespace = "http://purl.org/ontology/dbcells/cells#"
        format = self.dlg.comboFormat.currentText()
        namespace = self.dlg.lineURL.text()
        prefix = self.dlg.linePrefix.text()
        start = len (self.concepts)
        self.load_vocabulary(prefix, namespace, format)
        self.fill_table(start)

    def fill_table (self, start):
        self.dlg.tableAttributes.setRowCount(len(self.concepts))
        self.dlg.tableAttributes.setColumnCount(3)
        self.dlg.tableAttributes.setHorizontalHeaderLabels(["Concept", "Type", "Value"])


        for c in self.concepts[start:]:
            self.dlg.tableAttributes.setCellWidget(start, 0, QCheckBox( c))
            comboBox = QComboBox()
            comboBox.textActivated.connect(partial(self.combo_changed, start))
            comboBox.addItem("Constant Value")
            comboBox.addItem("Layer Attribute")
            self.dlg.tableAttributes.setCellWidget(start, 1, comboBox)
            self.dlg.tableAttributes.setCellWidget(start, 2, QLineEdit())
            #self.dlg.tableAttributes.setCellWidget(start, 1, self.attributes_combo())
            start += 1

    def load_vocabularies(self):
        for key, value in namespaces.items():
            self.load_vocabulary(key, str(value[0]), value[1])

    def cell_activate (self, row, column):
        print (row, column)

 

    def combo_changed(self,row, s):
        if (s == "Layer Attribute"):
            self.dlg.tableAttributes.setCellWidget(row, 2, self.attributes_combo())
        else:
            self.dlg.tableAttributes.setCellWidget(row, 2, QLineEdit())

        
    def output_file (self):
        self.file_name=str(QFileDialog.getSaveFileName(caption="Defining output file", filter="Terse RDF Triple Language(*.ttl)")[0])
        self.dlg.lineTTL.setText(self.file_name)


    def saveFile(self):

        saveAttrs = {}
        save_constants = {}
        for row in range(self.dlg.tableAttributes.rowCount()): 
            check = self.dlg.tableAttributes.cellWidget(row, 0) 
            if check.isChecked():
                rdf_attr = check.text()
                rdf = rdf_attr.split(":")
                rdf_attr = rdf[1]
                namespace = namespaces[rdf[0]][0]

                combo_type = self.dlg.tableAttributes.cellWidget(row, 1)

                if (combo_type.currentText() == "Layer Attribute"):
                    combo = self.dlg.tableAttributes.cellWidget(row, 2)
                    attribute = combo.currentText()
                    saveAttrs[attribute] = rdf_attr
                    setattr(Observation,attribute, namespace[rdf_attr])
                else:
                    line_edit = self.dlg.tableAttributes.cellWidget(row, 2)
                    save_constants[rdf_attr] = parse_ifs(line_edit.text())
                    setattr(Observation,rdf_attr, namespace[rdf_attr])

                #print(Observation,attribute, rdf[0],  namespace, rdf_attr)
                

        # verificar se existe um self.layer

        if self.dlg.checkSelected.isChecked():
            features = self.layer.selectedFeatures() 
        else:
            features = self.layer.getFeatures()

        observations = []
        #print (saveAttrs)
        for feature in features:

            obs = {
                "obs_id": str(uuid.uuid4())
            }


            for key in saveAttrs:
                obs[key] = feature[key]
            
            for key in save_constants:
                obs[key] = save_constants[key]
     
            observations.append (obs)
        
        fileName = self.dlg.lineTTL.text()
        self.iface.messageBar().pushMessage(
            "Success", "Output file written at " + fileName,
            level=Qgis.Success, duration=3
        )

        serialize_to_rdf_file(observations, Observation, fileName)
        
        

