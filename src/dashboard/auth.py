import hmac
import os

from flask import Response, request


def require_basic_auth(server):
    """Instala un antes-de-cada-request de HTTP Basic Auth sobre `server` (el
    Flask app de un Dash), leyendo DASHBOARD_USER/DASHBOARD_PASSWORD del entorno.
    """
    user = os.environ["DASHBOARD_USER"]
    password = os.environ["DASHBOARD_PASSWORD"]

    @server.before_request
    def _check_auth():
        auth = request.authorization
        valid = (
            auth is not None
            and hmac.compare_digest(auth.username, user)
            and hmac.compare_digest(auth.password, password)
        )
        if not valid:
            return Response(
                "Login requerido", 401, {"WWW-Authenticate": 'Basic realm="Dashboard"'}
            )
