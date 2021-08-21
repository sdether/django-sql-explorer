import importlib
import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connections as djcs

from explorer.app_settings import EXPLORER_CONNECTION_REPOSITORY
from explorer.utils import InvalidExplorerConnectionException

logger = logging.getLogger(__name__)


class ExplorerConnections:

    # We export valid SQL connections here so that consuming code never has to
    # deal with django.db.connections directly, and risk accessing a connection
    # that hasn't been registered to Explorer.

    def __init__(self):
        self._connections = getattr(settings, 'EXPLORER_CONNECTIONS', {})
        self.default_name = getattr(
            settings, 'EXPLORER_DEFAULT_CONNECTION', None
        )

    @property
    def default_connection(self):
        return self[self.default_name]

    def validate(self):
        # Validate connections
        if self.default_name not in self._connections:
            raise ImproperlyConfigured(
                f'EXPLORER_DEFAULT_CONNECTION is {self.default_name}, '
                f'but that alias is not present in the values of '
                f'EXPLORER_CONNECTIONS'
            )

        for name, conn_name in self._connections.items():
            # We check out connection list agaist the Django connections here to validate
            # that all configured connections exist. However, we do a 'live' lookup of
            # the connection on each item access, because  Django insists that connections
            # that are created in a thread are only accessed by that thread
            if conn_name not in djcs:
                raise ImproperlyConfigured(
                    f'EXPLORER_CONNECTIONS contains ({name}, {conn_name}), '
                    f'but {conn_name} is not a valid Django DB connection.'
                )

    def __getitem__(self, item):
        conn = self._connections.get(item)
        if not conn:
            if item in djcs:
                # Original connection handling did lookups by the django names not the explorer
                # alias, which in turn got stored in `Query` objects. In order to support existing
                # stored `Query` instances we fall back to looking up the connection by the django
                # name in case of a lookup miss
                logger.info(f"using legacy lookup by django connection name for '{item}'")
                conn = item
            else:
                raise InvalidExplorerConnectionException(
                    f'Attempted to access connection {item}, '
                    f'but that is not a registered Explorer connection.'
                )
        # Django insists that connections that are created in a thread are only accessed
        # by that thread, so we do a 'live' lookup of the connection on each item access.
        return djcs[self._connections[conn]]

    def __contains__(self, item):
        return item in self._connections

    def keys(self):
        return self._connections.keys()

    def values(self):
        return [self[v] for v in self._connections.values()]

    def items(self):
        return [(k, self[v]) for k, v in self._connections.items()]


if EXPLORER_CONNECTION_REPOSITORY:
    repository_class = importlib.import_module(EXPLORER_CONNECTION_REPOSITORY)
    connection = repository_class()
else:
    connections = ExplorerConnections()
