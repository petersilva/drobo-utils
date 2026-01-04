"""
Shared pytest fixtures for drobo-utils tests.

This module provides mock fixtures for testing without physical hardware.
"""

import pytest
import sys
import os
from contextlib import contextmanager
from unittest.mock import MagicMock, patch, mock_open
from io import StringIO

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# Platform Skip Markers
# =============================================================================

# Marker for tests that require Linux (ioctl)
requires_linux = pytest.mark.skipif(
    sys.platform != 'linux',
    reason="Test requires Linux platform for ioctl operations"
)

# Marker for tests that require fcntl module
requires_fcntl = pytest.mark.skipif(
    not hasattr(os, 'O_NONBLOCK'),
    reason="Test requires fcntl module (Unix-like system)"
)


# =============================================================================
# PyQt5 Availability Check
# =============================================================================

try:
    from PyQt5.QtWidgets import QApplication
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

# Marker for tests that require PyQt5
requires_pyqt5 = pytest.mark.skipif(
    not HAS_PYQT5,
    reason="Test requires PyQt5 to be installed"
)


@pytest.fixture(scope='session')
def qt_app():
    """Create a QApplication instance for GUI tests (session-scoped)."""
    if not HAS_PYQT5:
        pytest.skip("PyQt5 not installed")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# =============================================================================
# Mock ioctl Fixture
# =============================================================================

@pytest.fixture
def mock_ioctl():
    """Mock fcntl.ioctl to avoid actual device I/O."""
    with patch('fcntl.ioctl') as mock:
        # Default: return success (0)
        mock.return_value = 0
        yield mock


@pytest.fixture
def mock_ioctl_with_response():
    """Mock fcntl.ioctl that populates response buffers."""
    def _create_mock(responses=None):
        """
        Create a mock that returns different responses based on call order.

        Args:
            responses: List of (return_value, buffer_data) tuples
        """
        if responses is None:
            responses = [(0, b'\x00' * 64)]

        call_count = [0]

        def side_effect(fd, request, arg, mutate_flag=True):
            idx = min(call_count[0], len(responses) - 1)
            call_count[0] += 1
            ret_val, data = responses[idx]
            if data and hasattr(arg, 'raw'):
                arg.raw = data[:len(arg)]
            return ret_val

        mock = MagicMock(side_effect=side_effect)
        return mock

    return _create_mock


# =============================================================================
# Mock Device File Fixture
# =============================================================================

@pytest.fixture
def mock_device_file():
    """Mock open() for /dev/sdX device files."""
    mock_file = MagicMock()
    mock_file.fileno.return_value = 3  # Fake file descriptor

    with patch('builtins.open', return_value=mock_file) as mock_open_func:
        yield mock_open_func, mock_file


@pytest.fixture
def mock_os_listdir():
    """Mock os.listdir to return fake device list."""
    @contextmanager
    def _create_mock(devices=None):
        if devices is None:
            devices = ['sda', 'sdb', 'sdc']

        with patch('os.listdir', return_value=devices) as mock:
            yield mock

    return _create_mock


# =============================================================================
# Mock Drobo SCSI Responses
# =============================================================================

@pytest.fixture
def mock_drobo_responses():
    """Provide sample Drobo SCSI response data for testing."""
    return {
        # Identify LUN response (vendor string)
        'identify_lun': {
            'host': 0,
            'channel': 0,
            'id': 0,
            'lun': 0,
            'vendor': 'Drobo   ',
        },
        # Status subpage response
        'status': {
            'unit_status': 0,  # Normal operation
            'slot_count': 4,
            'slot_status': [3, 3, 3, 0x80],  # green, green, green, empty
        },
        # Capacity subpage response
        'capacity': {
            'total_capacity_protected': 4 * 1024 * 1024 * 1024 * 1024,  # 4TB
            'used_capacity_protected': 1 * 1024 * 1024 * 1024 * 1024,  # 1TB
            'free_capacity_protected': 3 * 1024 * 1024 * 1024 * 1024,  # 3TB
        },
        # Config subpage response
        'config': {
            'max_lun_size': 2 * 1024 * 1024 * 1024 * 1024,  # 2TB
            'lun_count': 1,
        },
        # Firmware version
        'firmware': {
            'version': '1.3.5',
            'revision': '12345',
        },
    }


@pytest.fixture
def mock_drobo_device(mock_drobo_responses):
    """Create a fully mocked Drobo device."""
    mock_device = MagicMock()

    # Set up common attributes
    mock_device.device = '/dev/sdz'
    mock_device.name = 'Drobo01'
    mock_device.serial = 'DRB123456'

    # Mock status method
    mock_device.GetSubPageStatus.return_value = mock_drobo_responses['status']
    mock_device.GetSubPageCapacity.return_value = mock_drobo_responses['capacity']
    mock_device.GetSubPageConfig.return_value = mock_drobo_responses['config']
    mock_device.GetSubPageFirmware.return_value = mock_drobo_responses['firmware']

    # Mock slot info
    mock_device.slot_count = 4
    mock_device.slots = mock_drobo_responses['status']['slot_status']

    return mock_device


# =============================================================================
# Mock Firmware Server Fixture
# =============================================================================

@pytest.fixture
def mock_firmware_server():
    """Mock urllib requests for firmware download testing."""
    @contextmanager
    def _create_mock(firmware_data=None, version='1.4.0', status_code=200):
        if firmware_data is None:
            # Create minimal valid firmware structure
            # Magic number + length + CRC + body
            import struct
            import zlib

            body = b'FAKE_FIRMWARE_BODY' * 100
            body_crc = zlib.crc32(body) & 0xffffffff
            header = struct.pack('>4sII', b'DRI\x00', len(body), body_crc)
            firmware_data = header + body

        mock_response = MagicMock()
        mock_response.read.return_value = firmware_data
        mock_response.status = status_code
        mock_response.getcode.return_value = status_code
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response) as mock:
            yield mock, mock_response

    return _create_mock


@pytest.fixture
def mock_firmware_zip():
    """Mock zipfile operations for firmware extraction."""
    @contextmanager
    def _create_mock(firmware_content=b'FAKE_FIRMWARE'):
        mock_zip = MagicMock()
        mock_zip_file = MagicMock()
        mock_zip_file.read.return_value = firmware_content
        mock_zip.open.return_value.__enter__.return_value = mock_zip_file
        mock_zip.namelist.return_value = ['firmware.dri']

        with patch('zipfile.ZipFile', return_value=mock_zip) as mock:
            yield mock, mock_zip

    return _create_mock


# =============================================================================
# CLI Testing Fixtures
# =============================================================================

@pytest.fixture
def capture_stdout():
    """Capture stdout for CLI output testing."""
    captured = StringIO()
    with patch('sys.stdout', captured):
        yield captured


@pytest.fixture
def mock_sys_argv():
    """Mock sys.argv for CLI argument testing."""
    def _set_args(args):
        with patch.object(sys, 'argv', ['drobom'] + args):
            yield
    return _set_args


@pytest.fixture
def mock_drobo_class(mock_drobo_device):
    """Mock the Drobo class for CLI testing."""
    with patch('Drobo.Drobo', return_value=mock_drobo_device) as mock:
        yield mock


# =============================================================================
# DroboIOctl Testing Fixtures
# =============================================================================

@pytest.fixture
def mock_drobo_ioctl_class(mock_device_file, mock_ioctl):
    """Create a mocked DroboIOctl instance."""
    mock_open_func, mock_file = mock_device_file

    # Import after mocking
    with patch('builtins.open', mock_open_func):
        with patch('fcntl.ioctl', mock_ioctl):
            import DroboIOctl
            instance = DroboIOctl.DroboIOctl('/dev/sdz', debugflags=0)
            yield instance


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_scsi_response():
    """Provide a sample SCSI response buffer."""
    import struct
    # Standard inquiry response format
    return struct.pack(
        '8s8s16s',
        b'\x00' * 8,      # Vendor-specific
        b'Drobo   ',      # Vendor identification
        b'Drobo          ' # Product identification
    )


@pytest.fixture
def sample_slot_status():
    """Provide sample slot status data for different scenarios."""
    return {
        'all_green': [3, 3, 3, 3],
        'one_empty': [3, 3, 3, 0x80],
        'one_failed': [3, 6, 3, 3],  # red-black = failed
        'rebuilding': [3, 4, 3, 3],  # red-green = rebuilding
        'no_redundancy': [3, 3, 0x80, 0x80],
    }


@pytest.fixture
def sample_unit_status():
    """Provide sample unit status flags for different scenarios."""
    return {
        'normal': 0,
        'red_alert': 0x0002,
        'yellow_alert': 0x0004,
        'no_disks': 0x0008,
        'bad_disk': 0x0010,
        'no_redundancy': 0x0040,
        'format_in_progress': 0x0400,
        'new_firmware': 0x2000,
    }
