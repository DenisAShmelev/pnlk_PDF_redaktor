import sys
import os
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QSlider, QSpinBox, QToolBar, 
                             QAction, QFileDialog, QColorDialog, QMessageBox,
                             QWidget, QSplitter, QListWidget, QTextEdit)
from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QFont, QIcon
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter


class PDFViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        # Инициализируем атрибуты перед вызовом initUI
        self.current_file = None
        self.doc = None
        self.current_page = 0
        self.zoom_factor = 1.0
        self.drawing = False
        self.last_point = QPoint()
        self.annotations = []
        self.current_tool = "pan"  # "pan", "pencil", "text"
        self.pen_color = QColor(255, 0, 0)
        self.pen_width = 3
        self.text_annotations = []
        
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("PDF Viewer with Annotations")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter for sidebar and main view
        splitter = QSplitter(Qt.Horizontal)
        
        # Sidebar for tools and annotations list
        self.create_sidebar(splitter)
        
        # Main view area
        self.create_main_view(splitter)
        
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)
        
        # Create menu bar
        self.create_menubar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
    def create_sidebar(self, parent):
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        
        # Tools section
        tools_label = QLabel("Tools")
        tools_label.setFont(QFont("Arial", 12, QFont.Bold))
        sidebar_layout.addWidget(tools_label)
        
        # Tool buttons
        pan_btn = QPushButton("Pan Tool")
        pan_btn.clicked.connect(lambda: self.set_tool("pan"))
        sidebar_layout.addWidget(pan_btn)
        
        pencil_btn = QPushButton("Pencil")
        pencil_btn.clicked.connect(lambda: self.set_tool("pencil"))
        sidebar_layout.addWidget(pencil_btn)
        
        text_btn = QPushButton("Text")
        text_btn.clicked.connect(lambda: self.set_tool("text"))
        sidebar_layout.addWidget(text_btn)
        
        # Color selection
        color_btn = QPushButton("Choose Color")
        color_btn.clicked.connect(self.choose_color)
        sidebar_layout.addWidget(color_btn)
        
        # Pen width
        pen_width_layout = QHBoxLayout()
        pen_width_layout.addWidget(QLabel("Pen Width:"))
        self.pen_width_spin = QSpinBox()
        self.pen_width_spin.setRange(1, 20)
        self.pen_width_spin.setValue(self.pen_width)
        self.pen_width_spin.valueChanged.connect(self.set_pen_width)
        pen_width_layout.addWidget(self.pen_width_spin)
        sidebar_layout.addLayout(pen_width_layout)
        
        # Annotations list
        sidebar_layout.addWidget(QLabel("Annotations:"))
        self.annotations_list = QListWidget()
        sidebar_layout.addWidget(self.annotations_list)
        
        # Clear annotations button
        clear_btn = QPushButton("Clear All Annotations")
        clear_btn.clicked.connect(self.clear_annotations)
        sidebar_layout.addWidget(clear_btn)
        
        sidebar_layout.addStretch()
        parent.addWidget(sidebar_widget)
        
    def create_main_view(self, parent):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # Navigation controls
        nav_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton("Previous")
        self.prev_btn.clicked.connect(self.prev_page)
        nav_layout.addWidget(self.prev_btn)
        
        self.page_label = QLabel("Page: 0/0")
        nav_layout.addWidget(self.page_label)
        
        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self.next_page)
        nav_layout.addWidget(self.next_btn)
        
        # Page navigation spinbox
        nav_layout.addWidget(QLabel("Go to:"))
        self.page_spin = QSpinBox()
        self.page_spin.valueChanged.connect(self.go_to_page)
        nav_layout.addWidget(self.page_spin)
        
        # Zoom controls
        nav_layout.addWidget(QLabel("Zoom:"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(25, 400)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.zoom_changed)
        nav_layout.addWidget(self.zoom_slider)
        
        self.zoom_label = QLabel("100%")
        nav_layout.addWidget(self.zoom_label)
        
        main_layout.addLayout(nav_layout)
        
        # PDF display area
        self.pdf_label = QLabel()
        self.pdf_label.setAlignment(Qt.AlignCenter)
        self.pdf_label.setStyleSheet("border: 1px solid gray;")
        self.pdf_label.setMinimumSize(400, 600)
        main_layout.addWidget(self.pdf_label)
        
        # Text input for text annotations
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Enter text for annotation...")
        self.text_input.setMaximumHeight(100)
        self.text_input.hide()
        main_layout.addWidget(self.text_input)
        
        parent.addWidget(main_widget)
        
    def create_menubar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        open_action = QAction('Open', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction('Save As...', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        print_action = QAction('Print', self)
        print_action.setShortcut('Ctrl+P')
        print_action.triggered.connect(self.print_file)
        file_menu.addAction(print_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu('View')
        
        zoom_in_action = QAction('Zoom In', self)
        zoom_in_action.setShortcut('Ctrl++')
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction('Zoom Out', self)
        zoom_out_action.setShortcut('Ctrl+-')
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)
        
        reset_zoom_action = QAction('Reset Zoom', self)
        reset_zoom_action.setShortcut('Ctrl+0')
        reset_zoom_action.triggered.connect(self.reset_zoom)
        view_menu.addAction(reset_zoom_action)
        
    def create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        open_btn = QAction("Open", self)
        open_btn.triggered.connect(self.open_file)
        toolbar.addAction(open_btn)
        
        save_btn = QAction("Save As", self)
        save_btn.triggered.connect(self.save_file)
        toolbar.addAction(save_btn)
        
        toolbar.addSeparator()
        
        zoom_in_btn = QAction("Zoom In", self)
        zoom_in_btn.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_btn)
        
        zoom_out_btn = QAction("Zoom Out", self)
        zoom_out_btn.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_btn)
        
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open PDF File", "", "PDF Files (*.pdf)")
        
        if file_path:
            try:
                self.doc = fitz.open(file_path)
                self.current_file = file_path
                self.current_page = 0
                self.zoom_factor = 1.0
                self.zoom_slider.setValue(100)
                self.annotations = []
                self.text_annotations = []
                self.update_annotations_list()
                self.update_page_controls()
                self.display_page()
                self.statusBar().showMessage(f"Opened: {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open file: {str(e)}")
    
    def save_file(self):
        if not self.doc:
            QMessageBox.warning(self, "Warning", "No PDF file is open.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Save PDF File", "", "PDF Files (*.pdf)")
        
        if file_path:
            try:
                # Apply annotations to the PDF
                self.apply_annotations_to_pdf()
                self.doc.save(file_path)
                self.statusBar().showMessage(f"Saved as: {os.path.basename(file_path)}")
                QMessageBox.information(self, "Success", "File saved successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file: {str(e)}")
    
    def apply_annotations_to_pdf(self):
        """Apply drawings and text annotations to the PDF document"""
        if not self.doc:
            return
            
        # For this example, we'll just save the original PDF
        # In a real implementation, you would use PyMuPDF to add annotations
        # to the PDF pages based on the drawings and text
        
        # This is a placeholder for the annotation logic
        print("Applying annotations to PDF...")
    
    def display_page(self):
        if not self.doc:
            return
            
        try:
            page = self.doc[self.current_page]
            mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
            pix = page.get_pixmap(matrix=mat)
            
            img_data = pix.tobytes("ppm")
            image = QImage()
            image.loadFromData(img_data)
            
            pixmap = QPixmap.fromImage(image)
            
            # Create a painter to draw annotations
            painter = QPainter(pixmap)
            
            # Draw pencil annotations
            for annotation in self.annotations:
                if annotation['page'] == self.current_page and annotation['type'] == 'pencil':
                    pen = QPen(annotation['color'], annotation['width'])
                    painter.setPen(pen)
                    for i in range(1, len(annotation['points'])):
                        painter.drawLine(annotation['points'][i-1], annotation['points'][i])
            
            # Draw text annotations
            for text_ann in self.text_annotations:
                if text_ann['page'] == self.current_page:
                    font = QFont("Arial", 12)
                    painter.setFont(font)
                    painter.setPen(QPen(text_ann['color']))
                    painter.drawText(text_ann['position'], text_ann['text'])
            
            painter.end()
            
            self.pdf_label.setPixmap(pixmap)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not display page: {str(e)}")
    
    def update_page_controls(self):
        if self.doc:
            total_pages = len(self.doc)
            self.page_label.setText(f"Page: {self.current_page + 1}/{total_pages}")
            self.page_spin.setRange(1, total_pages)
            self.page_spin.setValue(self.current_page + 1)
            self.prev_btn.setEnabled(self.current_page > 0)
            self.next_btn.setEnabled(self.current_page < total_pages - 1)
    
    def prev_page(self):
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self.display_page()
            self.update_page_controls()
    
    def next_page(self):
        if self.doc and self.current_page < len(self.doc) - 1:
            self.current_page += 1
            self.display_page()
            self.update_page_controls()
    
    def go_to_page(self, page_num):
        if self.doc and 1 <= page_num <= len(self.doc):
            self.current_page = page_num - 1
            self.display_page()
            self.update_page_controls()
    
    def zoom_changed(self, value):
        self.zoom_factor = value / 100.0
        self.zoom_label.setText(f"{value}%")
        if self.doc:
            self.display_page()
    
    def zoom_in(self):
        current_value = self.zoom_slider.value()
        if current_value < self.zoom_slider.maximum():
            self.zoom_slider.setValue(current_value + 10)
    
    def zoom_out(self):
        current_value = self.zoom_slider.value()
        if current_value > self.zoom_slider.minimum():
            self.zoom_slider.setValue(current_value - 10)
    
    def reset_zoom(self):
        self.zoom_slider.setValue(100)
    
    def set_tool(self, tool):
        self.current_tool = tool
        if tool == "text":
            self.text_input.show()
        else:
            self.text_input.hide()
        self.statusBar().showMessage(f"Tool: {tool.capitalize()}")
    
    def choose_color(self):
        color = QColorDialog.getColor(self.pen_color, self, "Choose Pen Color")
        if color.isValid():
            self.pen_color = color
    
    def set_pen_width(self, width):
        self.pen_width = width
    
    def clear_annotations(self):
        self.annotations = [ann for ann in self.annotations if ann['page'] != self.current_page]
        self.text_annotations = [ann for ann in self.text_annotations if ann['page'] != self.current_page]
        self.update_annotations_list()
        self.display_page()
    
    def update_annotations_list(self):
        self.annotations_list.clear()
        page_annotations = [ann for ann in self.annotations if ann['page'] == self.current_page]
        page_texts = [ann for ann in self.text_annotations if ann['page'] == self.current_page]
        
        for ann in page_annotations:
            self.annotations_list.addItem(f"Drawing ({len(ann['points'])} points)")
        
        for text_ann in page_texts:
            self.annotations_list.addItem(f"Text: {text_ann['text'][:30]}...")
    
    def mousePressEvent(self, event):
        if (event.button() == Qt.LeftButton and self.pdf_label.underMouse() and 
            self.doc and self.current_tool in ["pencil", "text"]):
            
            pos = self.pdf_label.mapFrom(self, event.pos())
            
            # Проверяем, что есть pixmap для работы
            if not self.pdf_label.pixmap():
                return
                
            pixmap_rect = self.pdf_label.pixmap().rect()
            label_rect = self.pdf_label.rect()
            
            # Calculate the offset to center the pixmap
            x_offset = (label_rect.width() - pixmap_rect.width()) // 2
            y_offset = (label_rect.height() - pixmap_rect.height()) // 2
            
            # Adjust position relative to the pixmap
            adjusted_pos = QPoint(pos.x() - x_offset, pos.y() - y_offset)
            
            # Проверяем, что клик внутри изображения
            if not pixmap_rect.contains(adjusted_pos):
                return
            
            if self.current_tool == "pencil":
                self.drawing = True
                self.last_point = adjusted_pos
                self.annotations.append({
                    'type': 'pencil',
                    'page': self.current_page,
                    'color': self.pen_color,
                    'width': self.pen_width,
                    'points': [adjusted_pos]
                })
            
            elif self.current_tool == "text":
                text = self.text_input.toPlainText().strip()
                if text:
                    self.text_annotations.append({
                        'type': 'text',
                        'page': self.current_page,
                        'text': text,
                        'color': self.pen_color,
                        'position': adjusted_pos
                    })
                    self.text_input.clear()
                    self.display_page()
                    self.update_annotations_list()
    
    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.LeftButton and self.drawing and 
            self.current_tool == "pencil" and self.pdf_label.underMouse() and
            self.pdf_label.pixmap()):
            
            pos = self.pdf_label.mapFrom(self, event.pos())
            pixmap_rect = self.pdf_label.pixmap().rect()
            label_rect = self.pdf_label.rect()
            
            x_offset = (label_rect.width() - pixmap_rect.width()) // 2
            y_offset = (label_rect.height() - pixmap_rect.height()) // 2
            
            adjusted_pos = QPoint(pos.x() - x_offset, pos.y() - y_offset)
            
            # Проверяем, что движение внутри изображения
            if not pixmap_rect.contains(adjusted_pos):
                return
            
            if self.annotations:
                self.annotations[-1]['points'].append(adjusted_pos)
                self.last_point = adjusted_pos
                self.display_page()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            self.update_annotations_list()
    
    def print_file(self):
        if not self.doc:
            QMessageBox.warning(self, "Warning", "No PDF file is open.")
            return
            
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        
        if dialog.exec_() == QPrintDialog.Accepted:
            # This is a simplified print implementation
            # In a real application, you would render each page to the printer
            QMessageBox.information(self, "Print", "Print functionality would be implemented here.")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PDF Viewer with Annotations")
    
    viewer = PDFViewer()
    viewer.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()