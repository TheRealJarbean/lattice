# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'recipe_tabEpCPKR.ui'
##
## Created by: Qt User Interface Compiler version 6.9.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QHeaderView, QLabel,
    QLayout, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QTableWidget, QTableWidgetItem, QToolButton,
    QVBoxLayout, QWidget)

class Ui_RecipeTab(object):
    def setupUi(self, RecipeTab):
        if not RecipeTab.objectName():
            RecipeTab.setObjectName(u"RecipeTab")
        RecipeTab.resize(1143, 852)
        self.verticalLayout = QVBoxLayout(RecipeTab)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.new_recipe = QPushButton(RecipeTab)
        self.new_recipe.setObjectName(u"new_recipe")

        self.horizontalLayout_6.addWidget(self.new_recipe)

        self.recipe_save = QToolButton(RecipeTab)
        self.recipe_save.setObjectName(u"recipe_save")
        icon = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentSave))
        self.recipe_save.setIcon(icon)

        self.horizontalLayout_6.addWidget(self.recipe_save)

        self.recipe_load = QToolButton(RecipeTab)
        self.recipe_load.setObjectName(u"recipe_load")
        icon1 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentOpen))
        self.recipe_load.setIcon(icon1)

        self.horizontalLayout_6.addWidget(self.recipe_load)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_6.addItem(self.horizontalSpacer)

        self.add_recipe_step = QPushButton(RecipeTab)
        self.add_recipe_step.setObjectName(u"add_recipe_step")

        self.horizontalLayout_6.addWidget(self.add_recipe_step)


        self.verticalLayout.addLayout(self.horizontalLayout_6)

        self.recipe_table = QTableWidget(RecipeTab)
        if (self.recipe_table.columnCount() < 11):
            self.recipe_table.setColumnCount(11)
        __qtablewidgetitem = QTableWidgetItem()
        self.recipe_table.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.recipe_table.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.recipe_table.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.recipe_table.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.recipe_table.setHorizontalHeaderItem(4, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.recipe_table.setHorizontalHeaderItem(5, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.recipe_table.setHorizontalHeaderItem(6, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.recipe_table.setHorizontalHeaderItem(7, __qtablewidgetitem7)
        __qtablewidgetitem8 = QTableWidgetItem()
        self.recipe_table.setHorizontalHeaderItem(8, __qtablewidgetitem8)
        __qtablewidgetitem9 = QTableWidgetItem()
        self.recipe_table.setHorizontalHeaderItem(9, __qtablewidgetitem9)
        __qtablewidgetitem10 = QTableWidgetItem()
        self.recipe_table.setHorizontalHeaderItem(10, __qtablewidgetitem10)
        if (self.recipe_table.rowCount() < 1):
            self.recipe_table.setRowCount(1)
        self.recipe_table.setObjectName(u"recipe_table")
        self.recipe_table.setStyleSheet(u"QHeaderView::section { font-weight: bold; }\n"
"QTableWidget::item { text-align: center; }\n"
"QTableWidget:disabled {\n"
"    color: black;\n"
"}\n"
"\n"
"QTableView::item:disabled {\n"
"    color: black;\n"
"}\n"
"\n"
"QComboBox:disabled {\n"
"    color: black;\n"
"}\n"
"\n"
"QHeaderView::section:disabled {\n"
"    color: black;\n"
"}")
        self.recipe_table.setAlternatingRowColors(False)
        self.recipe_table.setCornerButtonEnabled(True)
        self.recipe_table.setRowCount(1)
        self.recipe_table.horizontalHeader().setVisible(True)
        self.recipe_table.horizontalHeader().setCascadingSectionResizes(False)
        self.recipe_table.horizontalHeader().setProperty(u"showSortIndicator", False)
        self.recipe_table.horizontalHeader().setStretchLastSection(False)

        self.verticalLayout.addWidget(self.recipe_table)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        self.horizontalSpacer_7 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_7)

        self.recipe_time_monitor_label_2 = QLabel(RecipeTab)
        self.recipe_time_monitor_label_2.setObjectName(u"recipe_time_monitor_label_2")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.recipe_time_monitor_label_2.sizePolicy().hasHeightForWidth())
        self.recipe_time_monitor_label_2.setSizePolicy(sizePolicy)
        self.recipe_time_monitor_label_2.setMinimumSize(QSize(0, 0))
        self.recipe_time_monitor_label_2.setMaximumSize(QSize(150, 16777215))
        self.recipe_time_monitor_label_2.setStyleSheet(u"font: 700 12pt \"Segoe UI\";")
        self.recipe_time_monitor_label_2.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_3.addWidget(self.recipe_time_monitor_label_2)

        self.recipe_time_monitor_data = QLineEdit(RecipeTab)
        self.recipe_time_monitor_data.setObjectName(u"recipe_time_monitor_data")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.recipe_time_monitor_data.sizePolicy().hasHeightForWidth())
        self.recipe_time_monitor_data.setSizePolicy(sizePolicy1)
        self.recipe_time_monitor_data.setMinimumSize(QSize(150, 0))
        self.recipe_time_monitor_data.setMaximumSize(QSize(150, 16777215))
        self.recipe_time_monitor_data.setStyleSheet(u"font: 12pt \"Segoe UI\";")
        self.recipe_time_monitor_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.recipe_time_monitor_data.setReadOnly(True)

        self.horizontalLayout_3.addWidget(self.recipe_time_monitor_data)

        self.recipe_loop_monitor_label_2 = QLabel(RecipeTab)
        self.recipe_loop_monitor_label_2.setObjectName(u"recipe_loop_monitor_label_2")
        sizePolicy.setHeightForWidth(self.recipe_loop_monitor_label_2.sizePolicy().hasHeightForWidth())
        self.recipe_loop_monitor_label_2.setSizePolicy(sizePolicy)
        self.recipe_loop_monitor_label_2.setMinimumSize(QSize(0, 0))
        self.recipe_loop_monitor_label_2.setMaximumSize(QSize(200, 16777215))
        self.recipe_loop_monitor_label_2.setStyleSheet(u"font: 700 12pt \"Segoe UI\";")
        self.recipe_loop_monitor_label_2.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_3.addWidget(self.recipe_loop_monitor_label_2)

        self.recipe_loop_monitor_data = QLineEdit(RecipeTab)
        self.recipe_loop_monitor_data.setObjectName(u"recipe_loop_monitor_data")
        sizePolicy1.setHeightForWidth(self.recipe_loop_monitor_data.sizePolicy().hasHeightForWidth())
        self.recipe_loop_monitor_data.setSizePolicy(sizePolicy1)
        self.recipe_loop_monitor_data.setMinimumSize(QSize(50, 0))
        self.recipe_loop_monitor_data.setMaximumSize(QSize(50, 16777215))
        self.recipe_loop_monitor_data.setStyleSheet(u"font: 12pt \"Segoe UI\";")
        self.recipe_loop_monitor_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.recipe_loop_monitor_data.setReadOnly(True)

        self.horizontalLayout_3.addWidget(self.recipe_loop_monitor_data)

        self.horizontalSpacer_8 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_8)

        self.recipe_start = QPushButton(RecipeTab)
        self.recipe_start.setObjectName(u"recipe_start")
        sizePolicy1.setHeightForWidth(self.recipe_start.sizePolicy().hasHeightForWidth())
        self.recipe_start.setSizePolicy(sizePolicy1)
        self.recipe_start.setMinimumSize(QSize(300, 50))
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.recipe_start.setFont(font)
        self.recipe_start.setStyleSheet(u"background-color: rgb(0, 255, 0);")

        self.horizontalLayout_3.addWidget(self.recipe_start)

        self.recipe_pause = QPushButton(RecipeTab)
        self.recipe_pause.setObjectName(u"recipe_pause")
        self.recipe_pause.setMinimumSize(QSize(300, 50))
        self.recipe_pause.setFont(font)
        self.recipe_pause.setStyleSheet(u"background-color: rgb(255, 255, 0);")

        self.horizontalLayout_3.addWidget(self.recipe_pause)

        self.horizontalSpacer_14 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_14)


        self.verticalLayout.addLayout(self.horizontalLayout_3)


        self.retranslateUi(RecipeTab)

        QMetaObject.connectSlotsByName(RecipeTab)
    # setupUi

    def retranslateUi(self, RecipeTab):
        RecipeTab.setWindowTitle(QCoreApplication.translate("RecipeTab", u"Form", None))
        self.new_recipe.setText(QCoreApplication.translate("RecipeTab", u"New Recipe", None))
        self.recipe_save.setText("")
        self.recipe_load.setText("")
        self.add_recipe_step.setText(QCoreApplication.translate("RecipeTab", u"Add Step", None))
        ___qtablewidgetitem = self.recipe_table.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("RecipeTab", u"Action", None));
        ___qtablewidgetitem1 = self.recipe_table.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("RecipeTab", u"1", None));
        ___qtablewidgetitem2 = self.recipe_table.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("RecipeTab", u"2", None));
        ___qtablewidgetitem3 = self.recipe_table.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("RecipeTab", u"3", None));
        ___qtablewidgetitem4 = self.recipe_table.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("RecipeTab", u"4", None));
        ___qtablewidgetitem5 = self.recipe_table.horizontalHeaderItem(5)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("RecipeTab", u"5", None));
        ___qtablewidgetitem6 = self.recipe_table.horizontalHeaderItem(6)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("RecipeTab", u"6", None));
        ___qtablewidgetitem7 = self.recipe_table.horizontalHeaderItem(7)
        ___qtablewidgetitem7.setText(QCoreApplication.translate("RecipeTab", u"7", None));
        ___qtablewidgetitem8 = self.recipe_table.horizontalHeaderItem(8)
        ___qtablewidgetitem8.setText(QCoreApplication.translate("RecipeTab", u"8", None));
        ___qtablewidgetitem9 = self.recipe_table.horizontalHeaderItem(9)
        ___qtablewidgetitem9.setText(QCoreApplication.translate("RecipeTab", u"9", None));
        ___qtablewidgetitem10 = self.recipe_table.horizontalHeaderItem(10)
        ___qtablewidgetitem10.setText(QCoreApplication.translate("RecipeTab", u"10", None));
        self.recipe_time_monitor_label_2.setText(QCoreApplication.translate("RecipeTab", u"Time Remaining", None))
        self.recipe_loop_monitor_label_2.setText(QCoreApplication.translate("RecipeTab", u"     Current Iteration", None))
        self.recipe_start.setText(QCoreApplication.translate("RecipeTab", u"Start Recipe", None))
        self.recipe_pause.setText(QCoreApplication.translate("RecipeTab", u"Pause", None))
    # retranslateUi

