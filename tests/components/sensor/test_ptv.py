"""The tests for the Public Transport Victoria (PTV) platform."""
import unittest
import requests_mock

from homeassistant.components.sensor.ptv import CONF_LINE, URL
from homeassistant.setup import setup_component
from tests.common import load_fixture, get_test_home_assistant

VALID_CONFIG = {
    'platform': 'ptv',
    'user_id': 'test_user_id',
    'api_key': 'test_api_key'
}


class TestPTVSensor(unittest.TestCase):
    """Test the tube_state platform."""

    def setUp(self):
        """Initialize values for this testcase class."""
        self.hass = get_test_home_assistant()
        self.config = VALID_CONFIG

    def tearDown(self):
        """Stop everything that was started."""
        self.hass.stop()

    @requests_mock.Mocker()
    def test_setup(self, mock_req):
        """Test for operational tube_state sensor with proper attributes."""
        self.assertTrue(
            setup_component(self.hass, 'sensor', {'sensor': self.config}))

        state = self.hass.states.get('sensor.ptv')
