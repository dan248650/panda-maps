from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
import requests
from io import BytesIO


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Карта")
        self.setGeometry(100, 100, 650, 500)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        self.map_label = QLabel()
        self.map_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.map_label)

        self.show_map()

    def show_map(self):
        lon = 37.6
        lat = 55.75

        spn_lon = 0.1
        spn_lat = 0.1

        url = "https://static-maps.yandex.ru/1.x/"

        params = {
            'll': f'{lon},{lat}',
            'spn': f'{spn_lon},{spn_lat}',
            'l': 'map',
            'size': '650,450'
        }

        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(BytesIO(response.content).getvalue())
                self.map_label.setPixmap(pixmap.scaled(650, 450, Qt.AspectRatioMode.KeepAspectRatio))
            else:
                self.map_label.setText(f"Ошибка загрузки карты: {response.status_code}")
        except Exception as e:
            self.map_label.setText(f"Ошибка: {str(e)}")
