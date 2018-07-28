"""
Sensor for checking status of Public Transport Victoria (PTV) trains, buses and trams.
"""
import logging
import pyptv3
import datetime
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

def get_stops(client):
    stops = pyptv3.Stops(client)
    return stops.by_location(-37.79371095116535, 144.8650010974549)

def setup_platform(hass, config, add_devices, discovery_info=None):
    client = pyptv3.Client(config.get("user_id"), config.get("api_key"))
    stops = get_stops(client)

    sensors = []
    for stop in stops["stops"]:
        sensors.append(PTVSensor(client, stop))

    add_devices(sensors, True)


class PTVSensor(Entity):
    BUS_ICON = 'mdi:bus'
    TRAM_ICON = 'mdi:tram'
    TRAIN_ICON = 'mdi:train'

    def __init__(self, client, data):
        print(data)
        self._client = client
        self._data = data
        self._departures = []

    def next_departure(self, departure):
        next_departure = departure["estimated_departure_utc"]
        if next_departure is None:
            next_departure = departure["scheduled_departure_utc"]

        print(next_departure)
        time = datetime.datetime.strptime(next_departure, "%Y-%m-%dT%H:%M:%SZ")
        return str(time - datetime.datetime.now())

    @property
    def name(self):
        return self._data["stop_name"]

    @property
    def state(self):
        if len(self._departures) > 0:
            return self.next_departure(self._departures[0])
        else:
            return None

    @property
    def icon(self):
        if self._data["route_type"] == 0:
            return self.TRAIN_ICON
        elif self._data["route_type"] == 1:
            return self.TRAM_ICON
        elif self._data["route_type"] == 2:
            return self.BUS_ICON
        elif self._data["route_type"] == 3:
            return self.TRAIN_ICON
        elif self._data["route_type"] == 4:
            return self.BUS_ICON

    @property
    def device_state_attributes(self):
        """Return other details about the sensor state."""
        attrs = {}
        attrs['Suburb'] = self._data["stop_suburb"]
        attrs['Latitude'] = self._data["stop_latitude"]
        attrs['Longitude'] = self._data["stop_longitude"]
        return attrs

    def update(self):
        departures = pyptv3.Departures(self._client, self._data["route_type"], self._data["stop_id"])
        result = departures.all()
        self._departures = result["departures"]
