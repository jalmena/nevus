"""neVus: self-hosted longitudinal tracking of moles and skin marks. Not a diagnostic tool."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("nevus")
except PackageNotFoundError:  # running from a checkout without an installed distribution
    __version__ = "0.0.0"
