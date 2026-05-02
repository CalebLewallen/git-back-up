from litestar import Litestar

from database.engine import sqlalchemy_plugin

app = Litestar(
    plugins=[sqlalchemy_plugin]
)