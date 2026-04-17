import requests
import math
from typing import Tuple, Optional, Dict, Any, Union, List


def get_spn(toponym: Dict[str, Any], padding: float = 1.2) -> Tuple[str, str]:
    """
    Рассчитывает параметры масштаба (spn) для показа объекта.
    """
    envelope = toponym["boundedBy"]["Envelope"]
    lower = list(map(float, envelope["lowerCorner"].split()))
    upper = list(map(float, envelope["upperCorner"].split()))

    width = abs(upper[0] - lower[0]) * padding
    height = abs(upper[1] - lower[1]) * padding

    if width > 180:
        width = 180
    if height > 90:
        height = 90

    return f"{width:.6f}", f"{height:.6f}"


def get_map_params(toponym_or_points: Union[Dict[str, Any], List[Dict[str, str]]],
                   map_type: str = "map",
                   pt_style: Optional[str] = "pm2rdl") -> Dict[str, str]:
    """
    Универсальная функция для получения параметров карты.

    Args:
        toponym_or_points: либо объект GeoObject, либо список точек
        map_type: тип карты
        pt_style: стиль метки (для одного объекта)

    Returns:
        Dict[str, str]: параметры для запроса
    """

    if isinstance(toponym_or_points, list):
        return _get_map_params_for_points(toponym_or_points, map_type)
    else:
        return _get_map_params_for_toponym(toponym_or_points, map_type, pt_style)


def _get_map_params_for_toponym(toponym: Dict[str, Any],
                                map_type: str = "map",
                                pt_style: Optional[str] = "pm2rdl") -> Dict[str, str]:
    """
    Внутренняя функция для одного объекта
    """
    lon, lat = toponym["Point"]["pos"].split()
    spn_lon, spn_lat = get_spn(toponym)

    params = {
        "ll": f"{lon},{lat}",
        "spn": f"{spn_lon},{spn_lat}",
        "l": map_type
    }

    if pt_style:
        params["pt"] = f"{lon},{lat},{pt_style}"

    return params


def _get_map_params_for_points(points: List[Dict[str, str]],
                               map_type: str = "map") -> Dict[str, str]:
    """
    Внутренняя функция для нескольких точек
    """
    if not points:
        return {}

    if len(points) == 1:
        lon, lat = points[0]["coords"].split(",")
        return {
            "ll": f"{lon},{lat}",
            "spn": "0.05,0.05",
            "l": map_type,
            "pt": "~".join([f"{p['coords']},{p['style']}" for p in points])
        }

    coords_list = [list(map(float, p["coords"].split(","))) for p in points]
    lons = [c[0] for c in coords_list]
    lats = [c[1] for c in coords_list]

    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    center_lon = (min_lon + max_lon) / 2
    center_lat = (min_lat + max_lat) / 2

    spn_lon = (max_lon - min_lon) * 1.2
    spn_lat = (max_lat - min_lat) * 1.2

    spn_lon = max(0.001, min(spn_lon, 180))
    spn_lat = max(0.001, min(spn_lat, 90))

    return {
        "ll": f"{center_lon:.6f},{center_lat:.6f}",
        "spn": f"{spn_lon:.6f},{spn_lat:.6f}",
        "l": map_type,
        "pt": "~".join([f"{p['coords']},{p['style']}" for p in points])
    }


# Расстояние между двумя точками, заданными координатами
def lonlat_distance(a, b):

    degree_to_meters_factor = 111 * 1000 # 111 километров в метрах
    a_lon, a_lat = a
    b_lon, b_lat = b

    # Берем среднюю по широте точку и считаем коэффициент для нее.
    radians_lattitude = math.radians((a_lat + b_lat) / 2.)
    lat_lon_factor = math.cos(radians_lattitude)

    # Вычисляем смещения в метрах по вертикали и горизонтали.
    dx = abs(a_lon - b_lon) * degree_to_meters_factor * lat_lon_factor
    dy = abs(a_lat - b_lat) * degree_to_meters_factor

    # Вычисляем расстояние между точками.
    distance = math.sqrt(dx * dx + dy * dy)

    return distance


def get_coordinates(address, api_key):
    """
    Получает координаты по адресу
    """
    url = "https://geocode-maps.yandex.ru/1.x/"
    params = {
        'apikey': api_key,
        "geocode": address,
        "format": "json"
    }

    response = requests.get(url, params=params)
    json_data = response.json()

    try:
        point = json_data["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]["Point"]["pos"]
        lon, lat = map(float, point.split())
        return lon, lat
    except (IndexError, KeyError):
        return None


def get_district_by_coords(lon, lat, api_key):
    """
    Получает информацию о районе по координатам
    """
    url = "https://geocode-maps.yandex.ru/1.x/"
    params = {
        'apikey': api_key,
        "geocode": f"{lon},{lat}",
        "kind": "district",
        "format": "json"
    }

    response = requests.get(url, params=params)
    json_data = response.json()

    try:
        features = json_data["response"]["GeoObjectCollection"]["featureMember"]

        for feature in features:
            geo_object = feature["GeoObject"]

            components = (geo_object
                          .get("metaDataProperty", {})
                          .get("GeocoderMetaData", {})
                          .get("Address", {})
                          .get("Components", []))

            for component in components:
                if (component.get("kind") == "district" and
                        "район" in component.get("name", "")):
                    return component["name"]

            for component in components:
                if component.get("kind") == "district":
                    return component["name"]

        return None
    except (IndexError, KeyError):
        return None


def get_coordinates_full(address, api_key):
    """
    Получает координаты и полный объект GeoObject по адресу
    """
    url = "https://geocode-maps.yandex.ru/1.x/"
    params = {
        'apikey': api_key,
        "geocode": address,
        "format": "json"
    }

    response = requests.get(url, params=params)
    json_data = response.json()

    try:
        feature = json_data["response"]["GeoObjectCollection"]["featureMember"][0]
        toponym = feature["GeoObject"]
        point = toponym["Point"]["pos"]
        lon, lat = map(float, point.split())
        return (lon, lat), toponym
    except (IndexError, KeyError):
        return None, None
