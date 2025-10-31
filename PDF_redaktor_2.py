import sys
import os
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLabel, QSlider, QFileDialog,
                             QLineEdit, QToolBar, QStatusBar, QMessageBox)
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPixmap, QImage, QPainter, QWheelEvent, QMouseEvent
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter


class PDFViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.pdf_document = None
        self.current_page = 0
        self.total_pages = 0
        self.scale_factor = 1.0
        self.zoom_step = 0.2
        self.min_zoom = 0.3
        self.max_zoom = 5.0
        self.drag_start = None
        self.pan_offset = [0, 0]
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('PDF Viewer - 30 лет опыта в действии!')
        self.setGeometry(100, 100, 1200, 800)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Создаем toolbar
        self.createToolbar()
        
        # Область просмотра
        self.viewer_widget = PDFViewerWidget(self)
        main_layout.addWidget(self.viewer_widget)
        
        # Создаем status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.updateStatusBar()
        
    def createToolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Кнопка открытия файла
        open_btn = QPushButton('Открыть PDF')
        open_btn.clicked.connect(self.openFile)
        toolbar.addWidget(open_btn)
        
        # Кнопка сохранения
        save_btn = QPushButton('Сохранить как...')
        save_btn.clicked.connect(self.saveFile)
        toolbar.addWidget(save_btn)
        
        toolbar.addSeparator()
        
        # Навигация по страницам
        prev_btn = QPushButton('← Пред.')
        prev_btn.clicked.connect(self.prevPage)
        toolbar.addWidget(prev_btn)
        
        self.page_label = QLabel('Страница: 0/0')
        toolbar.addWidget(self.page_label)
        
        next_btn = QPushButton('След. →')
        next_btn.clicked.connect(self.nextPage)
        toolbar.addWidget(next_btn)
        
        toolbar.addSeparator()
        
        # Масштабирование
        zoom_out_btn = QPushButton('Уменьшить -')
        zoom_out_btn.clicked.connect(self.zoomOut)
        toolbar.addWidget(zoom_out_btn)
        
        self.zoom_label = QLabel('100%')
        toolbar.addWidget(self.zoom_label)
        
        zoom_in_btn = QPushButton('Увеличить +')
        zoom_in_btn.clicked.connect(self.zoomIn)
        toolbar.addWidget(zoom_in_btn)
        
        # Слайдер масштабирования
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(30)
        self.zoom_slider.setMaximum(500)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.zoomSliderChanged)
        toolbar.addWidget(self.zoom_slider)
        
        # Кнопка сброса масштаба и панорамирования
        reset_btn = QPushButton('Сброс')
        reset_btn.clicked.connect(self.resetView)
        toolbar.addWidget(reset_btn)
        
    def openFile(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть PDF файл", "", "PDF Files (*.pdf)")
        
        if file_path:
            try:
                # Закрываем предыдущий документ
                if self.pdf_document:
                    self.pdf_document.close()
                
                self.pdf_document = fitz.open(file_path)
                self.total_pages = len(self.pdf_document)
                self.current_page = 0
                self.scale_factor = 1.0
                self.pan_offset = [0, 0]
                self.zoom_slider.setValue(100)
                
                self.updateDisplay()
                self.updateStatusBar()
                
                self.status_bar.showMessage(f'Файл открыт: {os.path.basename(file_path)}')
                
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл: {str(e)}")
    
    def saveFile(self):
        if not self.pdf_document:
            QMessageBox.warning(self, "Предупреждение", "Нет открытого PDF файла")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить PDF как", "", "PDF Files (*.pdf)")
        
        if file_path:
            try:
                # Создаем копию документа
                new_doc = fitz.open()
                new_doc.insert_pdf(self.pdf_document)
                new_doc.save(file_path)
                new_doc.close()
                
                self.status_bar.showMessage(f'Файл сохранен: {os.path.basename(file_path)}')
                QMessageBox.information(self, "Успех", "Файл успешно сохранен!")
                
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл: {str(e)}")
    
    def prevPage(self):
        if self.pdf_document and self.current_page > 0:
            self.current_page -= 1
            self.pan_offset = [0, 0]  # Сбрасываем панорамирование при смене страницы
            self.updateDisplay()
            self.updateStatusBar()
    
    def nextPage(self):
        if self.pdf_document and self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.pan_offset = [0, 0]  # Сбрасываем панорамирование при смене страницы
            self.updateDisplay()
            self.updateStatusBar()
    
    def zoomIn(self):
        new_scale = self.scale_factor + self.zoom_step
        if new_scale <= self.max_zoom:
            self.scale_factor = new_scale
            self.updateZoomControls()
            self.updateDisplay()
    
    def zoomOut(self):
        new_scale = self.scale_factor - self.zoom_step
        if new_scale >= self.min_zoom:
            self.scale_factor = new_scale
            self.updateZoomControls()
            self.updateDisplay()
    
    def zoomSliderChanged(self, value):
        self.scale_factor = value / 100.0
        self.updateZoomControls()
        self.updateDisplay()
    
    def updateZoomControls(self):
        self.zoom_label.setText(f'{int(self.scale_factor * 100)}%')
        self.zoom_slider.setValue(int(self.scale_factor * 100))
    
    def resetView(self):
        self.scale_factor = 1.0
        self.pan_offset = [0, 0]
        self.updateZoomControls()
        self.updateDisplay()
    
    def updateDisplay(self):
        if self.pdf_document and 0 <= self.current_page < self.total_pages:
            self.viewer_widget.update()
    
    def updateStatusBar(self):
        if self.pdf_document:
            self.page_label.setText(f'Страница: {self.current_page + 1}/{self.total_pages}')
            self.status_bar.showMessage(f'Страница {self.current_page + 1} из {self.total_pages} | Масштаб: {int(self.scale_factor * 100)}%')
        else:
            self.page_label.setText('Страница: 0/0')
            self.status_bar.showMessage('Готов')


class PDFViewerWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setMouseTracking(True)
        self.dragging = False
        self.last_mouse_pos = None
        
    def paintEvent(self, event):
        if not self.parent.pdf_document:
            return
            
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.white)
        
        try:
            # Получаем страницу
            page = self.parent.pdf_document[self.parent.current_page]
            
            # Создаем матрицу для рендеринга с учетом масштаба
            mat = fitz.Matrix(self.parent.scale_factor, self.parent.scale_factor)
            pix = page.get_pixmap(matrix=mat)
            
            # Конвертируем в QImage
            img_data = pix.samples
            qimage = QImage(img_data, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            
            # Рассчитываем позицию для отрисовки с учетом панорамирования
            x_offset = self.parent.pan_offset[0] + (self.width() - pix.width) // 2
            y_offset = self.parent.pan_offset[1] + (self.height() - pix.height) // 2
            
            # Рисуем изображение
            painter.drawImage(x_offset, y_offset, qimage)
            
        except Exception as e:
            painter.drawText(self.rect(), Qt.AlignCenter, f"Ошибка отображения: {str(e)}")
    
    def wheelEvent(self, event: QWheelEvent):
        if event.angleDelta().y() > 0:
            self.parent.zoomIn()
        else:
            self.parent.zoomOut()
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.last_mouse_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging and self.last_mouse_pos:
            delta = event.pos() - self.last_mouse_pos
            self.parent.pan_offset[0] += delta.x()
            self.parent.pan_offset[1] += delta.y()
            self.last_mouse_pos = event.pos()
            self.update()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.setCursor(Qt.ArrowCursor)


def main():
    app = QApplication(sys.argv)
    
    # Устанавливаем стиль для более современного вида
    app.setStyle('Fusion')
    
    viewer = PDFViewer()
    viewer.show()
    
    # Показываем сообщение при запуске
    viewer.status_bar.showMessage('Готов к работе. Откройте PDF файл через меню "Открыть PDF"')
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()