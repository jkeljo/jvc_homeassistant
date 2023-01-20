"""Implement JVC component."""
from collections.abc import Iterable
import logging

from jvc_projector.jvc_projector import JVCProjector
import voluptuous as vol

from homeassistant.components.remote import PLATFORM_SCHEMA, RemoteEntity
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_TIMEOUT,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    INFO_COMMAND,
)

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Required(CONF_SCAN_INTERVAL): cv.time_period,
        vol.Optional(CONF_TIMEOUT): cv.positive_int,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType = None,
) -> None:
    """Set up platform."""
    host = config.get(CONF_HOST)
    name = config.get(CONF_NAME)
    password = config.get(CONF_PASSWORD)
    jvc_client = JVCProjector(
        host=host,
        password=password,
        logger=_LOGGER,
        connect_timeout=int(config.get(CONF_TIMEOUT, 3)),
    )
    # create a long lived connection
    jvc_client.open_connection()
    add_entities(
        [
            JVCRemote(name, host, jvc_client),
        ]
    )


class JVCRemote(RemoteEntity):
    """Implements the interface for JVC Remote in HA."""

    def __init__(
        self,
        name: str,
        host: str,
        jvc_client: JVCProjector = None,
    ) -> None:
        """JVC Init."""
        self._name = name
        self._host = host
        # attributes
        self._state = False
        self._lowlatency_enabled = False
        self._installation_mode = ""
        self._picture_mode = ""
        self._input_mode = ""
        self._laser_mode = ""
        self._eshift = ""
        self._color_mode = ""
        self._input_level = ""
        self._content_type = ""
        self._hdr_processing = ""
        self._lamp_power = ""
        self._hdr_data = ""
        self._theater_optimizer = ""

        self.jvc_client = jvc_client
        self._model_family = self.jvc_client.model_family

    @property
    def should_poll(self):
        """Poll."""
        return True

    @property
    def name(self):
        """Name."""
        return self._name

    @property
    def host(self):
        """Host."""
        return self._host

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        # Separate views for models to be cleaner

        # make sensors or automations based on these
        if "NZ" in self._model_family:
            return {
                "power_state": self._state,
                "picture_mode": self._picture_mode,
                "content_type": self._content_type,
                "hdr_data": self._hdr_data,
                "hdr_processing": self._hdr_processing,
                "theater_optimizer": "on" in self._theater_optimizer,
                "low_latency": self._lowlatency_enabled,
                "input_mode": self._input_mode,
                "laser_mode": self._laser_mode,
                "input_level": self._input_level,
                "color_mode": self._color_mode,
                "installation_mode": self._installation_mode,
                "eshift": self._eshift,
                "model": self._model_family,
            }

        if "NX" in self._model_family:
            return {
                "power_state": self._state,
                "picture_mode": self._picture_mode,
                "hdr_data": self._hdr_data,
                "low_latency": self._lowlatency_enabled,
                "input_mode": self._input_mode,
                "lamp_power": self._lamp_power,
                "input_level": self._input_level,
                "installation_mode": self._installation_mode,
                "color_mode": self._color_mode,
                "eshift": self._eshift,
                "model": self._model_family,
            }

        # for stuff like np-5 
        return {
            "power_state": self._state,
            "picture_mode": self._picture_mode,
            "low_latency": self._lowlatency_enabled,
            "input_mode": self._input_mode,
            "lamp_power": self._lamp_power,
            "input_level": self._input_level,
            "color_mode": self._color_mode,
            "installation_mode": self._installation_mode,
            "model": self._model_family,
        }

    @property
    def is_on(self):
        """Return the last known state of the projector."""

        return self._state

    def turn_on(self, **kwargs):
        """Send the power on command."""

        self.jvc_client.power_on()
        self._state = True

    def turn_off(self, **kwargs):
        """Send the power off command."""

        self.jvc_client.power_off()
        self._state = False

    def update(self):
        """Retrieve latest state."""
        self._state = self.jvc_client.is_on()

        if self._state:
            # Common attributes
            self._lowlatency_enabled = self.jvc_client.is_ll_on()
            self._installation_mode = self.jvc_client.get_install_mode()
            self._input_mode = self.jvc_client.get_input_mode()
            self._color_mode = self.jvc_client.get_color_mode()
            self._input_level = self.jvc_client.get_input_level()
            self._picture_mode = self.jvc_client.get_picture_mode()

            # NZ specifics
            if "NZ" in self._model_family:
                self._content_type = self.jvc_client.get_content_type()
                self._laser_mode = self.jvc_client.get_laser_mode()
                # only check HDR if the content type matches else timeout
                if any(x in self._content_type for x in ["hdr", "hlg"]):
                    self._hdr_processing = self.jvc_client.get_hdr_processing()
                    self._theater_optimizer = (
                        self.jvc_client.get_theater_optimizer_state()
                    )
            
            # Get lamp power if not NZ
            if not "NZ" in self._model_family:
                self._lamp_power = self.jvc_client.get_lamp_power()

            # nx and nz have these things, others may not
            if any(x in self._model_family for x in ["NX", "NZ"]):
                self._eshift = self.jvc_client.get_eshift_mode()
                self._hdr_data = self.jvc_client.get_hdr_data()

    def send_command(self, command: Iterable[str], **kwargs):
        """Send commands to a device."""

        self.jvc_client.exec_command(command)
