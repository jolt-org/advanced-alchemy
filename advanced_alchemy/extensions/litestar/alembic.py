from contextlib import suppress

from litestar import Litestar
from litestar.exceptions import ImproperlyConfiguredException

from advanced_alchemy.alembic.commands import AlembicCommands as _AlembicCommands
from advanced_alchemy.extensions.litestar.plugins import SQLAlchemyInitPlugin


def get_database_migration_plugin(app: Litestar) -> SQLAlchemyInitPlugin:
    """Retrieve a database migration plugin from the Litestar application's plugins.

    This function attempts to find and return either the SQLAlchemyPlugin or SQLAlchemyInitPlugin.
    If neither plugin is found, it raises an ImproperlyConfiguredException.
    """

    with suppress(KeyError):
        return app.plugins.get(SQLAlchemyInitPlugin)
    msg = "Failed to initialize database migrations. The required plugin (SQLAlchemyPlugin or SQLAlchemyInitPlugin) is missing."
    raise ImproperlyConfiguredException(
        msg,
    )


class AlembicCommands(_AlembicCommands):
    def __init__(self, app: Litestar) -> None:
        self._app = app
        self.plugin_config = get_database_migration_plugin(self._app)._config  # noqa: SLF001
        self.config = self._get_alembic_command_config()
