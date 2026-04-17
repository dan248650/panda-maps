from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtGui import QPixmap
import requests
from io import BytesIO
from functools import lru_cache


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

        self.lon = 37.6
        self.lat = 55.75

        self.is_loading = False

        self.zoom_level = 10
        self.MIN_ZOOM = 0
        self.MAX_ZOOM = 20
        self.ZOOM_STEP = 1
        self.MIN_SPN = 0.001
        self.MAX_SPN = 50.0
        self.current_spn = (None, None)

        self.update_spn_from_zoom()
        self.show_map()

    def update_spn_from_zoom(self):
        t = self.zoom_level / self.MAX_ZOOM
        spn_value = self.MAX_SPN * (self.MIN_SPN / self.MAX_SPN) ** t
        self.current_spn = (spn_value, spn_value)

    @lru_cache(maxsize=30)
    def get_cached_map(self, lon, lat, spn_lon, spn_lat, zoom_level):
        url = "https://static-maps.yandex.ru/1.x/"
        params = {
            'll': f'{lon},{lat}',
            'spn': f'{spn_lon},{spn_lat}',
            'l': 'map',
            'size': '650,450'
        }
        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                return response.content
        except requests.RequestException:
            pass
        return None

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_PageUp:
            new_zoom = min(self.MAX_ZOOM, self.zoom_level + self.ZOOM_STEP)
            if new_zoom != self.zoom_level:
                self.zoom_level = new_zoom
                self.update_spn_from_zoom()
                self.show_map()

        elif event.key() == Qt.Key.Key_PageDown:
            new_zoom = max(self.MIN_ZOOM, self.zoom_level - self.ZOOM_STEP)
            if new_zoom != self.zoom_level:
                self.zoom_level = new_zoom
                self.update_spn_from_zoom()
                self.show_map()

    def show_map(self):
        if self.is_loading:
            return

        cached_data = self.get_cached_map(self.lon, self.lat, self.current_spn[0], self.current_spn[1], self.zoom_level)

        if cached_data:
            pixmap = QPixmap()
            pixmap.loadFromData(BytesIO(cached_data).getvalue())
            self.map_label.setPixmap(pixmap.scaled(650, 450, Qt.AspectRatioMode.KeepAspectRatio))
            self.setWindowTitle(f"Карта - Зум: {self.zoom_level}/{self.MAX_ZOOM} (spn: {self.current_spn[0]:.3f})")
            return
        else:
            print("Ошибка загрузки")
