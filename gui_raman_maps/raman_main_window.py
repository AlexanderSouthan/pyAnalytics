# -*- coding: utf-8 -*-

import sys
import pickle
from PyQt5.QtWidgets import (QApplication, QMainWindow, QComboBox, QWidget,
                             QLineEdit, QFileDialog, QGridLayout, QHBoxLayout,
                             QVBoxLayout, QLabel, QAction, QDesktopWidget, 
                             QActionGroup, QMenu, QListWidget,
                             QAbstractItemView, QErrorMessage)

from raman_import_window import raman_import_window
from raman_visualization_window import raman_visualization_window
from raman_preprocessing_window import raman_preprocessing_window
# from hplc_calibration_window import hplc_calibration_window
# from hplc_visualization_window import hplc_visualization_window
# from pyAnalytics.hplc_prediction import hplc_prediction


class main_window(QMainWindow):

    def __init__(self):
        super().__init__()
        self.init_window()
        self.define_widgets()
        self.position_widgets()
        self.connect_event_handlers()

        self.init_datasets()

    def init_window(self):
        self.setGeometry(500, 500, 1200, 100)  # xPos, yPos, width, heigth
        self.center()  # center function is defined below
        self.setWindowTitle('Raman data analysis')

        self.statusBar().showMessage('Welcome')
        menubar = self.menuBar()
        file_menu = menubar.addMenu('&File')
        visualize_menu = menubar.addMenu('&Visualize')
        preprocess_menu = menubar.addMenu('&Preprocessing')
        calibration_menu = menubar.addMenu('&Calibration')
        analysis_menu = menubar.addMenu('&Analyze data')

        import_dataset_action = QAction('Import dataset', self)
        import_dataset_action.setShortcut('Ctrl+I')
        import_dataset_action.setStatusTip('Import dataset')
        import_dataset_action.triggered.connect(self.open_import_window)

        open_dataset_action = QAction('Open dataset from file', self)
        open_dataset_action.setShortcut('Ctrl+O')
        open_dataset_action.setStatusTip('Open dataset from file')
        open_dataset_action.triggered.connect(self.open_dataset)

        save_dataset_action = QAction('Save dataset to file', self)
        save_dataset_action.setShortcut('Ctrl+S')
        save_dataset_action.setStatusTip('Save dataset to file')
        save_dataset_action.triggered.connect(self.save_dataset)
        
        close_datasets_action = QAction('Unload all datasets', self)
        close_datasets_action.setStatusTip('Unload all datasets')
        close_datasets_action.triggered.connect(self.init_datasets)

        file_menu.addAction(import_dataset_action)
        file_menu.addAction(open_dataset_action)
        file_menu.addAction(save_dataset_action)
        file_menu.addAction(close_datasets_action)

        spectra_visualization_action = QAction('Show spectrum plots', self)
        spectra_visualization_action.setStatusTip(
            'Open spectrum visulization tool')
        spectra_visualization_action.triggered.connect(
            self.open_visulization_window)

        visualize_menu.addAction(spectra_visualization_action)

        preprocessing_action = QAction('Spectrum preprocessing', self)
        preprocessing_action.setStatusTip('Spectrum preprocessing')
        preprocessing_action.triggered.connect(self.open_preprocessing_window)

        preprocess_menu.addAction(preprocessing_action)

        # elugram_viewer_action = QAction('2D elugram viewer', self)
        # elugram_viewer_action.triggered.connect(self.open_elugram_window)

        # spectrum_viewer_action = QAction('2D spectrum viewer', self)
        # spectrum_viewer_action.triggered.connect(self.open_spectrum_window)

        # visualize_menu.addAction(elugram_viewer_action)
        # visualize_menu.addAction(spectrum_viewer_action)

        # calibration_viewer_action = QAction('Calibration wizard', self)
        # calibration_viewer_action.triggered.connect(
        #     self.open_calibration_window)

        # calibration_menu.addAction(calibration_viewer_action)

        # simple_cls_action = QAction('Simple cls analysis', self)
        # simple_cls_action.triggered.connect(
        #     self.analyze_dataset)
        
        # analysis_menu.addAction(simple_cls_action)

        self.container0 = QWidget(self)
        self.setCentralWidget(self.container0)

        self.grid_container = QGridLayout()
        self.container0.setLayout(self.grid_container)

    def define_widgets(self):
        self.dataset_selection_label = QLabel('<b>Active dataset</b>')
        self.dataset_selection_combo = QComboBox()

    def position_widgets(self):
        self.dataset_selection_layout = QVBoxLayout()
        self.dataset_selection_layout.addWidget(self.dataset_selection_label)
        self.dataset_selection_layout.addWidget(self.dataset_selection_combo)
        self.dataset_selection_layout.addStretch(1)

        self.hplc_data_selection_layout = QHBoxLayout()
        self.hplc_data_selection_layout.addLayout(
            self.dataset_selection_layout)
        self.hplc_data_selection_layout.addStretch(1)

        self.grid_container.addLayout(
            self.hplc_data_selection_layout, 0, 1, 1, 1)

    def connect_event_handlers(self):
        self.dataset_selection_combo.currentIndexChanged.connect(
            self.update_windows)
        # self.calibration_selection_list.itemClicked.connect(self.set_active_calibrations)

    def init_datasets(self):
        self.raman_datasets = {}
        self.raman_file_names = {}

        self.dataset_selection_combo.clear()

    def open_import_window(self):
        self.raman_import_window = raman_import_window(self)
        self.raman_import_window.show()

    def open_visulization_window(self):
        if len(self.raman_datasets) > 0:
            self.raman_visualization_window = raman_visualization_window(
                self.active_dataset())
            self.raman_visualization_window.show()
        else:
            error_message = QErrorMessage()
            error_message.showMessage('No active dataset available to '
                                      'visualize!')
            error_message.exec_()

    def open_preprocessing_window(self):
        if len(self.raman_datasets) > 0:
            self.raman_preprocessing_window = raman_preprocessing_window(
                self.active_dataset())
            self.raman_preprocessing_window.show()
        else:
            error_message = QErrorMessage()
            error_message.showMessage('No active dataset available to '
                                      'preprocess!')
            error_message.exec_()

    def active_dataset(self):
        active_dataset = self.raman_datasets[
            self.dataset_selection_combo.currentText()]

        return active_dataset

    def update_windows(self):
        try:
            self.raman_visualization_window.replace_data(self.active_dataset())
        except:
            pass
        try:
            self.raman_baseline_window.update_data(self.active_dataset())
        except:
            pass

    def open_dataset(self):
        file_type = 'Raman dataset file (*.raman)'
        file_name, _ = QFileDialog.getOpenFileName(
            self, 'Open Raman dataset file', filter=file_type)
        dataset_name = file_name.split('/')[-1]

        if file_name != '':
            with open(file_name, 'rb') as filehandle:
                self.raman_datasets[dataset_name] = pickle.load(filehandle)

            self.raman_file_names[dataset_name] = self.raman_datasets[
                dataset_name].file_names

            dataset_names = [
                self.dataset_selection_combo.itemText(i)
                for i in range(self.dataset_selection_combo.count())]

            if dataset_name not in dataset_names:
                self.dataset_selection_combo.addItem(dataset_name)

    def save_dataset(self):
        curr_dataset = self.dataset_selection_combo.currentText()

        file_type = 'Raman dataset file (*.raman)'
        file_name, _ = QFileDialog.getSaveFileName(
            self, 'Save active Raman dataset file', curr_dataset + '.raman',
            filter=file_type)

        if file_name != '':
            with open(file_name, 'wb') as filehandle:
                pickle.dump(self.raman_datasets[curr_dataset], filehandle)


    def center(self):  # centers object on screen
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


app = QApplication(sys.argv)
   
window = main_window()

window.show()
#app.exec_()
sys.exit(app.exec_())
   


