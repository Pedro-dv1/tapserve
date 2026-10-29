"""Only a configured, trusted proxy may supply a single overwritten client address."""

from ipaddress import ip_address, ip_network

from django.conf import settings
from rest_framework.exceptions import PermissionDenied


def client_address(request) -> str:
    try:
        peer = ip_address(request.META.get("REMOTE_ADDR", ""))
        if any(peer in ip_network(network) for network in settings.TRUSTED_PROXY_NETWORKS):
            peer = ip_address(request.META.get("HTTP_X_TAPSERVE_CLIENT_IP", ""))
        return str(peer)
    except ValueError as error:
        raise PermissionDenied() from error


def require_pin_network(request) -> None:
    address = ip_address(client_address(request))
    if not any(address in ip_network(network) for network in settings.STAFF_PIN_NETWORKS):
        raise PermissionDenied("Acesso por PIN não permitido nesta rede. Use sua senha individual.")
