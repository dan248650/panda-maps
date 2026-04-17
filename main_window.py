from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget,
                             QLabel, QComboBox, QHBoxLayout)
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

        main_layout = QVBoxLayout(central_widget)

        top_layout = QHBoxLayout()

        theme_label = QLabel("Тема карты:")
        top_layout.addWidget(theme_label)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Светлая", "Тёмная"])
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        self.theme_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        top_layout.addWidget(self.theme_combo)

        top_layout.addStretch()

        main_layout.addLayout(top_layout)

        self.map_label = QLabel()
        self.map_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.map_label)

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
        self.current_theme = "light"

        self.MIN_LON = -180.0
        self.MAX_LON = 180.0
        self.MIN_LAT = -90.0
        self.MAX_LAT = 90.0

        self.update_spn_from_zoom()
        self.show_map()

    def change_theme(self, theme_name: str):
        if theme_name == "Светлая":
            self.current_theme = "light"
        else:
            self.current_theme = "dark"

        self.get_cached_map.cache_clear()

        self.show_map()

    def update_spn_from_zoom(self):
        t = self.zoom_level / self.MAX_ZOOM
        spn_value = self.MAX_SPN * (self.MIN_SPN / self.MAX_SPN) ** t
        self.current_spn = (spn_value, spn_value)

    @lru_cache(maxsize=30)
    def get_cached_map(self, lon, lat, spn_lon, spn_lat, zoom_level, theme):
        url = "https://static-maps.yandex.ru/1.x/"

        if theme == "light":
            theme = "map"
        else:
            theme = "sat"

        params = {
            'll': f'{lon},{lat}',
            'spn': f'{spn_lon},{spn_lat}',
            'l': theme,
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

        elif event.key() == Qt.Key.Key_Up:
            shift = self.current_spn[1] * 0.8
            self.lat = min(self.MAX_LAT - self.current_spn[1] * 0.5, self.lat + shift)
            self.show_map()

        elif event.key() == Qt.Key.Key_Down:
            shift = self.current_spn[1] * 0.8
            self.lat = max(self.MIN_LAT + self.current_spn[1] * 0.5, self.lat - shift)
            self.show_map()

        elif event.key() == Qt.Key.Key_Left:
            shift = self.current_spn[0] * 0.8
            self.lon = self.lon - shift
            if self.lon < -180:
                self.lon += 360
            self.show_map()

        elif event.key() == Qt.Key.Key_Right:
            shift = self.current_spn[0] * 0.8
            self.lon = self.lon + shift
            if self.lon > 180:
                self.lon -= 360
            self.show_map()

    def show_map(self):
        if self.is_loading:
            return

        cached_data = self.get_cached_map(
            self.lon, self.lat,
            self.current_spn[0], self.current_spn[1],
            self.zoom_level, self.current_theme
        )

        if cached_data:
            pixmap = QPixmap()
            pixmap.loadFromData(BytesIO(cached_data).getvalue())
            self.map_label.setPixmap(pixmap.scaled(650, 450, Qt.AspectRatioMode.KeepAspectRatio))
            self.setWindowTitle(f"Карта - Зум: {self.zoom_level}/{self.MAX_ZOOM} | "
                                f"Координаты: {self.lon:.3f}, {self.lat:.3f} | "
                                f"spn: {self.current_spn[0]:.3f}")
            return
        else:
            print("Ошибка загрузки")
