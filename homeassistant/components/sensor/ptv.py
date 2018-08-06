"""
Sensor for checking status of Public Transport Victoria (PTV) trains, buses and trams.
"""
import logging
import pyptv3
import datetime
from dateutil import relativedelta
from pytz import timezone
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

async def get_stops(config, client):
    stops = pyptv3.Stops(client)
    return await stops.by_location(-37.79371095116535, 144.8650010974549, max_distance=1000)

async def get_departures(client, stop):
    departures = pyptv3.Departures(client, stop["route_type"], stop["stop_id"])
    return await departures.all()

async def get_directions(client, route_id):
    direction = pyptv3.Directions(client)
    return await direction.by_route(route_id)

async def get_disruptions(client, route_id):
    disruptions = pyptv3.Disruptions(client)
    return await disruptions.by_route(route_id)

async def setup(config, client, async_add_entities):
    stops = await get_stops(config, client)

    # Setup: find
    # 1. All Stops that fit criteria
    #   2. All Departures for each stop
    #   3. Find all unique directions from departures for each stop
    # Create one sensor person stop + direction ie "Tottenham - City (Flinders Street)" + "Tottenham (Sunshine)"
    # Update:
    # Find departures + disruptions

    # Allow user to define stops and directions by name and by ID.
    sensors = []
    for stop in stops["stops"]:
        departures = await get_departures(client, stop)

        if "departures" in departures:
            departures = departures["departures"]

            if len(departures) > 0:
                directions = await get_directions(client, departures[0]["route_id"])

                for direction in directions["directions"]:
                    sensors.append(PTVSensor(client, stop, direction))

    async_add_entities(sensors, True)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    client = pyptv3.AsyncClient(hass.loop, config.get("user_id"), config.get("api_key"))
    hass.async_add_job(setup(config, client, async_add_entities))
    return True

class PTVSensor(Entity):
    BUS_ICON = 'mdi:bus'
    TRAM_ICON = 'mdi:tram'
    TRAIN_ICON = 'mdi:train'

    def __init__(self, client, data, direction):
        self._client = client
        self._data = data
        self._departures = []
        self._disruptions = []
        self._direction = direction

    def departure_time(self, departure):
        departure_utc = departure["estimated_departure_utc"]
        if departure_utc is None:
            departure_utc = departure["scheduled_departure_utc"]

        dt = datetime.datetime.strptime(departure_utc, "%Y-%m-%dT%H:%M:%SZ")
        return dt

    def future_departures(self):
        d = filter(lambda d: d["direction_id"] == self._direction["direction_id"], self._departures)
        d = filter(lambda d: self.departure_time(d) > datetime.datetime.utcnow(), d)
        return list(d)

    def departs_in(self, departure):
        delta = relativedelta.relativedelta(self.departure_time(departure), datetime.datetime.utcnow())
        return delta.minutes

    @property
    def name(self):
        return self._data["stop_name"].strip() + " - " + self._direction["direction_name"].strip()

    @property
    def state(self):
        future_departures = self.future_departures()
        if len(future_departures) > 0:
            departs_in_minutes = self.departs_in(future_departures[0])

            if departs_in_minutes <= 0:
                return "Now"
            else:
                return str(departs_in_minutes)
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
        if self._data["route_type"] == 0:
            attrs['Type'] = "Train"
        elif self._data["route_type"] == 1:
            attrs['Type'] = "Tram"
        elif self._data["route_type"] == 2:
            attrs['Type'] = "Bus"
        elif self._data["route_type"] == 3:
            attrs['Type'] = "V/Line Train"
        elif self._data["route_type"] == 4:
            attrs['Type'] = "Night Bus"

        attrs['Stop Name'] = self._data["stop_name"].strip()
        attrs['Destination'] = self._direction['direction_name']
        attrs['Suburb'] = self._data["stop_suburb"]
        attrs['Latitude'] = self._data["stop_latitude"]
        attrs['Longitude'] = self._data["stop_longitude"]

        future_departures = self.future_departures()
        if len(future_departures) > 0:
            next_departure = future_departures[0]
            departs_in_minutes = self.departs_in(next_departure)
            if departs_in_minutes <= 0:
                attrs['Due'] = "Now"
            else:
                attrs['Due'] = "in " + str(departs_in_minutes) + " minutes"

            attrs['Next Departure'] = self.departure_time(next_departure)

            if self._data["route_type"] == 0 or self._data["route_type"] == 3:
                attrs['Platform Number'] = next_departure['platform_number']
                attrs['At Platform'] = next_departure['at_platform']

        return attrs


    async def async_update(self):
        departures = await get_departures(self._client, self._data)

        if "departures" in departures:
            self._departures = departures["departures"]

        return True
