from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget,
                             QLabel, QComboBox, QHBoxLayout, QLineEdit,
                             QPushButton, QTabWidget, QListWidget,
                             QListWidgetItem, QMessageBox)
from PyQt6.QtCore import Qt, QEvent, QTimer
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtGui import QPixmap
import requests
from io import BytesIO
from functools import lru_cache
from utils import get_coordinates_full, get_spn
import math


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Карта")
        self.setGeometry(100, 100, 850, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_h_layout = QHBoxLayout(central_widget)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        self.tab_widget = QTabWidget()

        map_tab = QWidget()
        map_layout = QVBoxLayout(map_tab)

        top_layout = QHBoxLayout()

        theme_label = QLabel("Тема карты:")
        top_layout.addWidget(theme_label)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Светлая", "Тёмная"])
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        self.theme_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        top_layout.addWidget(self.theme_combo)
        top_layout.addStretch()
        map_layout.addLayout(top_layout)

        search_layout = QHBoxLayout()
        search_label = QLabel("Поиск:")
        search_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите адрес или объект...")
        self.search_input.returnPressed.connect(self.search_object)
        self.search_input.installEventFilter(self)
        search_layout.addWidget(self.search_input)

        self.search_button = QPushButton("Искать")
        self.search_button.clicked.connect(self.search_object)
        search_layout.addWidget(self.search_button)

        map_layout.addLayout(search_layout)

        self.map_label = QLabel()
        self.map_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        map_layout.addWidget(self.map_label)

        self.tab_widget.addTab(map_tab, "Карта")

        markers_tab = QWidget()
        markers_layout = QHBoxLayout(markers_tab)

        left_markers = QWidget()
        left_markers_layout = QVBoxLayout(left_markers)

        self.markers_list = QListWidget()
        self.markers_list.itemClicked.connect(self.on_marker_selected)
        left_markers_layout.addWidget(self.markers_list)

        right_markers = QWidget()
        right_markers_layout = QVBoxLayout(right_markers)

        self.marker_info_label = QLabel("Выберите метку")
        self.marker_info_label.setWordWrap(True)
        right_markers_layout.addWidget(self.marker_info_label)

        right_markers_layout.addSpacing(20)

        self.show_on_map_btn = QPushButton("Показать на карте")
        self.show_on_map_btn.clicked.connect(self.show_selected_marker)
        right_markers_layout.addWidget(self.show_on_map_btn)

        self.delete_marker_btn = QPushButton("Удалить метку")
        self.delete_marker_btn.clicked.connect(self.delete_selected_marker)
        right_markers_layout.addWidget(self.delete_marker_btn)

        right_markers_layout.addStretch()

        markers_layout.addWidget(left_markers, 2)
        markers_layout.addWidget(right_markers, 1)

        self.tab_widget.addTab(markers_tab, "Метки")

        left_layout.addWidget(self.tab_widget)

        main_h_layout.addWidget(left_panel, 3)

        self.markers = []

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

        self.api_key = "8013b162-6b42-4997-9691-77b7074026e0"

        self.update_spn_from_zoom()
        self.show_map()

    def on_marker_selected(self, item):
        marker = item.data(Qt.ItemDataRole.UserRole)
        if marker:
            self.marker_info_label.setText(f"Адрес: {marker['address']}\n\n"
                                           f"Координаты:\n"
                                           f"lon: {marker['coords'][0]:.6f}\n"
                                           f"lat: {marker['coords'][1]:.6f}")

    def update_markers_list(self):
        self.markers_list.clear()
        for i, marker in enumerate(self.markers):
            item = QListWidgetItem(f"{i + 1}. {marker['address']}")
            item.setData(Qt.ItemDataRole.UserRole, marker)
            self.markers_list.addItem(item)

    def add_marker(self, address, coords):
        marker = {
            "address": address,
            "coords": coords
        }
        self.markers.append(marker)
        self.update_markers_list()

        self.show_map()

    def show_selected_marker(self):
        current_item = self.markers_list.currentItem()
        if current_item:
            marker = current_item.data(Qt.ItemDataRole.UserRole)
            if marker:
                self.lon, self.lat = marker["coords"]
                self.show_map()
                self.tab_widget.setCurrentIndex(0)

    def delete_selected_marker(self):
        current_row = self.markers_list.currentRow()
        if current_row >= 0:
            marker = self.markers[current_row]
            reply = QMessageBox.question(self, "Подтверждение",
                                         f"Удалить метку '{marker['address']}'?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.markers.pop(current_row)
                self.update_markers_list()
                self.marker_info_label.setText("Выберите метку")
                self.show_map()

    def eventFilter(self, obj, event):
        if obj == self.search_input and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key in [Qt.Key.Key_Left, Qt.Key.Key_Right,
                       Qt.Key.Key_Up, Qt.Key.Key_Down,
                       Qt.Key.Key_PageUp, Qt.Key.Key_PageDown]:
                self.keyPressEvent(event)
                return True

        return super().eventFilter(obj, event)

    def search_object(self):
        query = self.search_input.text().strip()
        if not query:
            return

        coords, toponym = get_coordinates_full(query, self.api_key)

        if coords and toponym:
            try:
                full_address = toponym.get("metaDataProperty", {}) \
                    .get("GeocoderMetaData", {}) \
                    .get("text", query)
            except:
                full_address = query

            self.add_marker(full_address, coords)

            self.lon, self.lat = coords

            spn_lon, spn_lat = get_spn(toponym)
            spn_value = max(float(spn_lon), float(spn_lat))
            self.zoom_level = self.convert_spn_to_zoom(spn_value)
            self.update_spn_from_zoom()

            self.get_cached_map.cache_clear()
            self.show_map()

            self.setWindowTitle(f"Карта - Добавлена метка: {full_address}")
        else:
            self.map_label.setText(f"Объект '{query}' не найден")
            QTimer.singleShot(2000, lambda: self.show_map() if not self.is_loading else None)

    def convert_spn_to_zoom(self, spn_value):
        if spn_value <= 0:
            return self.MAX_ZOOM

        t = math.log(spn_value / self.MAX_SPN) / math.log(self.MIN_SPN / self.MAX_SPN)
        zoom = int(round(t * self.MAX_ZOOM))
        zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, zoom))

        return zoom

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
    def get_cached_map(self, lon, lat, spn_lon, spn_lat, theme, markers_tuple):
        url = "https://static-maps.yandex.ru/1.x/"

        if theme == "light":
            map_type = "map"
        else:
            map_type = "sat"

        params = {
            'll': f'{lon},{lat}',
            'spn': f'{spn_lon},{spn_lat}',
            'l': map_type,
            'size': '650,450'
        }

        if markers_tuple:
            pt_params = []
            for marker in markers_tuple:
                pt_params.append(f"{marker[0]},{marker[1]},pm2rdl")
            params['pt'] = "~".join(pt_params)

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

        markers_tuple = tuple((m["coords"][0], m["coords"][1]) for m in self.markers)

        cached_data = self.get_cached_map(
            self.lon, self.lat,
            self.current_spn[0], self.current_spn[1],
            self.current_theme, markers_tuple
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
