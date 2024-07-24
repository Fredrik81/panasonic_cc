import logging

from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.storage import Store

from .pcomfortcloud.panasonicdevice import PanasonicDevice, PanasonicDeviceInfo, PanasonicDeviceEnergy
from .pcomfortcloud.apiclient import ApiClient
from .pcomfortcloud.changerequestbuilder import ChangeRequestBuilder
from .const import DOMAIN,MANUFACTURER, DEFAULT_DEVICE_FETCH_INTERVAL, CONF_DEVICE_FETCH_INTERVAL, CONF_ENERGY_FETCH_INTERVAL, DEFAULT_ENERGY_FETCH_INTERVAL

_LOGGER = logging.getLogger(__name__)

class PanasonicDeviceCoordinator(DataUpdateCoordinator[int]):

    def __init__(self, hass: HomeAssistant, config: dict, api_client: ApiClient, device_info: PanasonicDeviceInfo):
        super().__init__(
            hass,
            _LOGGER,
            name="Panasonic Device Coordinator",
            update_interval=timedelta(seconds=config.get(CONF_DEVICE_FETCH_INTERVAL, DEFAULT_DEVICE_FETCH_INTERVAL)),
            update_method=self._fetch_device_data,
        )
        self._hass = hass
        self._config = config
        self._api_client = api_client
        self._panasonic_device_info = device_info
        self._device:PanasonicDevice = None
        self._store = Store(hass, version=1, key=f"panasonic_cc_{device_info.id}")
        self._update_id = 0
        
    @property
    def device(self) -> PanasonicDevice:
        return self._device
    
    @property
    def api_client(self) -> ApiClient:
        return self._api_client
    
    @property
    def device_info(self)->DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._panasonic_device_info.id )},
            manufacturer=MANUFACTURER,
            model=self._panasonic_device_info.model,
            name=self._panasonic_device_info.name,
            sw_version=self._api_client.app_version
        )
    
    def get_change_request_builder(self):
        return ChangeRequestBuilder(self._device)
    
    async def async_apply_changes(self, request_builder: ChangeRequestBuilder):
        await self._api_client.set_device_raw(self._device, request_builder.build())

    async def async_get_stored_data(self):
        data = await self._store.async_load()
        if data is None:
            data = {}
        return data
    
    async def async_store_data(self, data):
        await self._store.async_save(data)


    async def _fetch_device_data(self)->int:
        try:
            if self._device is None:
                self._device = await self._api_client.get_device(self._panasonic_device_info)
                _LOGGER.debug(
                    "%s Device features\nNanoe: %s\nEco Navi: %s\nAI Eco: %s", 
                    self._panasonic_device_info.name,
                    self._device.has_nanoe, 
                    self._device.has_eco_navi, 
                    self._device.has_eco_function)
                self._update_id = 1
                return self._update_id
            if await self._api_client.try_update_device(self._device):
               self._update_id = self._update_id + 1
               return self._update_id
        except BaseException as e:
            raise UpdateFailed(f"Invalid response from API: {e}") from e
        return self._update_id

class PanasonicDeviceEnergyCoordinator(DataUpdateCoordinator[int]):

    def __init__(self, hass: HomeAssistant, config: dict, api_client: ApiClient, device_info: PanasonicDeviceInfo):
        super().__init__(
            hass,
            _LOGGER,
            name="Panasonic Device Energy Coordinator",
            update_interval=timedelta(seconds=config.get(CONF_ENERGY_FETCH_INTERVAL, DEFAULT_ENERGY_FETCH_INTERVAL)),
            update_method=self._fetch_device_data,
        )
        self._hass = hass
        self._config = config
        self._api_client = api_client
        self._panasonic_device_info = device_info
        self._energy: PanasonicDeviceEnergy = None
        self._update_id = 0

    @property
    def api_client(self) -> ApiClient:
        return self._api_client
    
    @property
    def energy(self) -> PanasonicDeviceEnergy:
        return self._energy
    
    @property
    def device_info(self)->DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._panasonic_device_info.id )},
            manufacturer=MANUFACTURER,
            model=self._panasonic_device_info.model,
            name=self._panasonic_device_info.name,
            sw_version=self._api_client.app_version
        )

    async def _fetch_device_data(self)->int:
        try:
            if self._energy is None:
                self._energy = await self._api_client.async_get_energy(self._panasonic_device_info)
                self._update_id = 1
                return self._update_id
            if await self._api_client.async_try_update_energy(self._energy):
               self._update_id = self._update_id + 1
               return self._update_id
        except BaseException as e:
            raise UpdateFailed(f"Invalid response from API: {e}") from e
        return self._update_id