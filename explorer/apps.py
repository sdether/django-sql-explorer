from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ExplorerAppConfig(AppConfig):

    name = 'explorer'
    verbose_name = _('SQL Explorer')

    def ready(self):
        from explorer.schema import build_async_schemas
        from explorer.connections import connections
        connections.validate()
        build_async_schemas()

