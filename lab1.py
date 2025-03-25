import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPlainTextEdit, QSplitter, QAction, QFileDialog,
    QMessageBox, QToolBar, QWidget, QVBoxLayout, QTextEdit
)
from PyQt5.QtGui import QPainter, QTextFormat, QColor, QIcon, QKeyEvent
from PyQt5.QtCore import Qt, QSize

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor
    def sizeHint(self):
        return QSize(self.codeEditor.lineNumberAreaWidth(), 0)
    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)

class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.updateLineNumberAreaWidth(0)
        self.setUndoRedoEnabled(True)
        self.lastKeyEvent = None
    def keyPressEvent(self, event):
        if event.text() != "" or event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            self.lastKeyEvent = QKeyEvent(event.type(), event.key(), event.modifiers(),
                                          event.text(), event.isAutoRepeat(), event.count())
        super().keyPressEvent(event)
    def lineNumberAreaWidth(self):
        digits = 1
        max_lines = max(1, self.blockCount())
        while max_lines >= 10:
            max_lines //= 10
            digits += 1
        space = 3 + self.fontMetrics().width('9') * digits
        return space
    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)
    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)
    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height())
    def highlightCurrentLine(self):
        extraSelections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor(Qt.yellow).lighter(160)
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)
    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), Qt.lightGray)
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(Qt.black)
                painter.drawText(0, top, self.lineNumberArea.width()-2, self.fontMetrics().height(),
                                 Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            blockNumber += 1

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.currentFile = None
        self.lastAction = None
        self.initUI()
    def initUI(self):
        self.setWindowTitle("Лабораторная работа №1: Текстовый редактор")
        self.textEdit = CodeEditor()
        self.textEdit.document().modificationChanged.connect(self.onModificationChanged)
        self.resultArea = QPlainTextEdit()
        self.resultArea.setReadOnly(True)
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.textEdit)
        splitter.addWidget(self.resultArea)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        centralWidget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(splitter)
        centralWidget.setLayout(layout)
        self.setCentralWidget(centralWidget)
        self.createActions()
        self.createMenus()
        self.createToolBar()
        self.textEdit.document().setModified(False)
        self.resize(1600, 1200)
        self.setMinimumSize(400, 300)
        self.statusBar().setSizeGripEnabled(True)
    def createActions(self):
        self.newAct = QAction("Создать", self)
        self.newAct.triggered.connect(self.newDocument)
        self.newAct.setIcon(QIcon("icons/new.png"))
        self.openAct = QAction("Открыть", self)
        self.openAct.triggered.connect(self.openDocument)
        self.openAct.setIcon(QIcon("icons/open.png"))
        self.saveAct = QAction("Сохранить", self)
        self.saveAct.triggered.connect(self.saveDocument)
        self.saveAct.setIcon(QIcon("icons/save.png"))
        self.saveAsAct = QAction("Сохранить как", self)
        self.saveAsAct.triggered.connect(self.saveDocumentAs)
        self.exitAct = QAction("Выход", self)
        self.exitAct.triggered.connect(self.exitApplication)
        self.undoAct = QAction("Отменить", self)
        self.undoAct.triggered.connect(self.textEdit.undo)
        self.undoAct.setIcon(QIcon("icons/undo.png"))
        self.redoAct = QAction("Повторить", self)
        self.redoAct.triggered.connect(self.repeatLastAction)
        self.redoAct.setIcon(QIcon("icons/redo.png"))
        self.cutAct = QAction("Вырезать", self)
        self.cutAct.triggered.connect(lambda: self._recordAction(self.textEdit.cut))
        self.cutAct.setIcon(QIcon("icons/cut.png"))
        self.copyAct = QAction("Копировать", self)
        self.copyAct.triggered.connect(lambda: self._recordAction(self.textEdit.copy))
        self.copyAct.setIcon(QIcon("icons/copy.png"))
        self.pasteAct = QAction("Вставить", self)
        self.pasteAct.triggered.connect(lambda: self._recordAction(self.textEdit.paste))
        self.pasteAct.setIcon(QIcon("icons/paste.png"))
        self.deleteAct = QAction("Удалить", self)
        self.deleteAct.triggered.connect(lambda: self._recordAction(self.deleteText))
        self.selectAllAct = QAction("Выделить все", self)
        self.selectAllAct.triggered.connect(self.textEdit.selectAll)
        self.helpAct = QAction("Вызов справки", self)
        self.helpAct.triggered.connect(self.showHelp)
        self.helpAct.setIcon(QIcon("icons/help.png"))
        self.aboutAct = QAction("О программе", self)
        self.aboutAct.triggered.connect(self.showAbout)
        self.aboutAct.setIcon(QIcon("icons/about.png"))
        self.syntaxAct = QAction("Запуск синтаксического анализатора", self)
        self.syntaxAct.triggered.connect(self.runSyntaxAnalyzer)
        self.syntaxAct.setIcon(QIcon("icons/syntax.png"))
    def createMenus(self):
        fileMenu = self.menuBar().addMenu("Файл")
        fileMenu.addAction(self.newAct)
        fileMenu.addAction(self.openAct)
        fileMenu.addAction(self.saveAct)
        fileMenu.addAction(self.saveAsAct)
        fileMenu.addSeparator()
        fileMenu.addAction(self.exitAct)
        editMenu = self.menuBar().addMenu("Правка")
        editMenu.addAction(self.undoAct)
        editMenu.addAction(self.redoAct)
        editMenu.addSeparator()
        editMenu.addAction(self.cutAct)
        editMenu.addAction(self.copyAct)
        editMenu.addAction(self.pasteAct)
        editMenu.addAction(self.deleteAct)
        editMenu.addSeparator()
        editMenu.addAction(self.selectAllAct)
        helpMenu = self.menuBar().addMenu("Справка")
        helpMenu.addAction(self.helpAct)
        helpMenu.addAction(self.aboutAct)
    def createToolBar(self):
        toolbar = QToolBar("Панель инструментов", self)
        toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        toolbar.addAction(self.newAct)
        toolbar.addAction(self.openAct)
        toolbar.addAction(self.saveAct)
        toolbar.addSeparator()
        toolbar.addAction(self.undoAct)
        toolbar.addAction(self.redoAct)
        toolbar.addSeparator()
        toolbar.addAction(self.copyAct)
        toolbar.addAction(self.cutAct)
        toolbar.addAction(self.pasteAct)
        toolbar.addSeparator()
        toolbar.addAction(self.syntaxAct)
        toolbar.addSeparator()
        toolbar.addAction(self.helpAct)
        toolbar.addAction(self.aboutAct)
    def onModificationChanged(self, modified):
        filename = self.currentFile if self.currentFile else "Безымянный документ"
        if modified:
            self.setWindowTitle("* " + filename + " - Лабораторная работа №1")
        else:
            self.setWindowTitle(filename + " - Лабораторная работа №1")
    def maybeSave(self):
        if self.textEdit.document().isModified():
            ret = QMessageBox.question(self, "Сохранить изменения?",
                                       "Документ был изменён. Сохранить изменения?",
                                       QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if ret == QMessageBox.Yes:
                return self.saveDocument()
            elif ret == QMessageBox.Cancel:
                return False
        return True
    def _recordAction(self, action):
        action()
        self.lastAction = action
    def newDocument(self):
        if not self.maybeSave():
            return
        self.textEdit.clear()
        self.textEdit.document().setModified(False)
        self.currentFile = None
        self.onModificationChanged(False)
        self.resultArea.clear()
        self.resultArea.appendPlainText("Создан новый документ.")
    def openDocument(self):
        if not self.maybeSave():
            return
        filename, _ = QFileDialog.getOpenFileName(self, "Открыть файл", "", "Текстовые файлы (*.txt);;Все файлы (*.*)")
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.textEdit.setPlainText(content)
                self.currentFile = filename
                self.textEdit.document().setModified(False)
                self.onModificationChanged(False)
                self.resultArea.appendPlainText(f"Файл '{filename}' успешно открыт.")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка открытия файла", f"Не удалось открыть файл:\n{e}")
    def saveDocument(self):
        if self.currentFile is None:
            return self.saveDocumentAs()
        try:
            with open(self.currentFile, 'w', encoding='utf-8') as f:
                f.write(self.textEdit.toPlainText())
            self.textEdit.document().setModified(False)
            self.onModificationChanged(False)
            self.resultArea.appendPlainText(f"Файл '{self.currentFile}' успешно сохранён.")
            return True
        except Exception as e:
            QMessageBox.warning(self, "Ошибка сохранения файла", f"Не удалось сохранить файл:\n{e}")
            return False
    def saveDocumentAs(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Сохранить как", "", "Текстовые файлы (*.txt);;Все файлы (*.*)")
        if filename:
            self.currentFile = filename
            return self.saveDocument()
        return False
    def exitApplication(self):
        if not self.maybeSave():
            return
        self.close()
    def deleteText(self):
        cursor = self.textEdit.textCursor()
        if cursor.hasSelection():
            cursor.removeSelectedText()
    def showHelp(self):
        help_text = (
            "Справка по функциям текстового редактора:\n\n"
            "Файл:\n"
            "  Создать - Создание нового документа.\n"
            "  Открыть - Открытие существующего текстового файла.\n"
            "  Сохранить - Сохранение текущего документа (если документ не сохранён, вызывается 'Сохранить как').\n"
            "  Сохранить как - Сохранение документа под новым именем.\n"
            "  Выход - Выход из программы (с предложением сохранить изменения, если они были внесены).\n\n"
            "Правка:\n"
            "  Отменить - Отмена последнего действия.\n"
            "  Повторить - Повтор последнего изменения (redo).\n"
            "  Вырезать - Вырезание выделенного фрагмента текста.\n"
            "  Копировать - Копирование выделенного фрагмента текста.\n"
            "  Вставить - Вставка скопированного/вырезанного текста.\n"
            "  Удалить - Удаление выделенного фрагмента текста.\n"
            "  Выделить все - Выделение всего текста в редакторе.\n\n"
            "Справка:\n"
            "  Вызов справки - Вывод справочной информации по функциям редактора.\n"
            "  О программе - Вывод информации о программе."
        )
        QMessageBox.information(self, "Справка", help_text)
    def showAbout(self):
        about_text = (
            "Текстовый редактор\n"
            "Лабораторная работа №1\n\n"
        )
        QMessageBox.information(self, "О программе", about_text)
    def runSyntaxAnalyzer(self):
        self.resultArea.appendPlainText("Запуск синтаксического анализатора: Функция не реализована.")
    def repeatLastAction(self):
        if self.lastAction is not None:
            self.lastAction()
            self.resultArea.appendPlainText("Повтор последнего действия выполнен (действие из lastAction).")
        elif self.textEdit.lastKeyEvent is not None:
            event = self.textEdit.lastKeyEvent
            if event.key() == Qt.Key_Backspace:
                cursor = self.textEdit.textCursor()
                cursor.deletePreviousChar()
                self.textEdit.setTextCursor(cursor)
            elif event.key() == Qt.Key_Delete:
                cursor = self.textEdit.textCursor()
                cursor.deleteChar()
                self.textEdit.setTextCursor(cursor)
            elif event.text() != "":
                self.textEdit.insertPlainText(event.text())
            self.resultArea.appendPlainText("Повтор последнего действия выполнен (клавиатурное событие).")
        else:
            self.resultArea.appendPlainText("Нет действий для повтора.")
    def closeEvent(self, event):
        if self.maybeSave():
            event.accept()
        else:
            event.ignore()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())
