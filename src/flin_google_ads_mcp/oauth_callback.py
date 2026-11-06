"""Short-lived, loopback-only OAuth receiver for local desktop clients."""

from __future__ import annotations

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlparse, urlunparse
import os
import secrets
import socket
import threading

from . import auth
from .config import ConfigurationError, Settings


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_port = False

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(2)
        return connection, address

    def handle_error(self, request, client_address):
        # Never log callback URLs, authorization codes or token responses.
        pass


@dataclass
class _Flow:
    server: _Server
    redirect_uri: str
    state: str
    status: str = "waiting_for_browser"
    timer: threading.Timer | None = None


class OAuthCallback:
    def __init__(self) -> None:
        # Also serialize manual credential changes with automatic completion.
        self.lock = threading.RLock()
        self._flow: _Flow | None = None

    def status(self) -> str:
        with self.lock:
            return self._flow.status if self._flow else "idle"

    def _finish(self, flow: _Flow, status: str) -> None:
        if self._flow is not flow or flow.status != "waiting_for_browser":
            return
        flow.status = status
        if flow.timer:
            flow.timer.cancel()
        with auth._auth_lock:
            auth._pending_auth.clear()
        flow.server.shutdown()
        flow.server.server_close()

    def cancel(self) -> None:
        with self.lock:
            if self._flow:
                self._finish(self._flow, "cancelled")

    def start(
        self, settings: Settings, auth_file: Path, on_saved: Callable[[], None]
    ) -> str:
        with self.lock:
            self.cancel()
            # Desktop OAuth clients support an OS-assigned loopback port.
            redirect = os.getenv(
                "GOOGLE_ADS_OAUTH_REDIRECT_URI", "http://127.0.0.1:0/"
            ).strip()
            parsed = auth.validate_redirect_uri(redirect)
            host = "127.0.0.1" if parsed.hostname == "localhost" else parsed.hostname
            family = socket.AF_INET6 if host == "::1" else socket.AF_INET
            manager = self

            class Handler(BaseHTTPRequestHandler):
                def log_message(self, *args):
                    pass

                def do_GET(self):
                    with manager.lock:
                        status, message = manager._receive(
                            flow,
                            self.path,
                            self.headers.get("Host"),
                            settings,
                            auth_file,
                            on_saved,
                        )
                    body = (
                        "<!doctype html><html lang='en'><meta charset='utf-8'>"
                        "<title>Google Ads sign-in</title><h1>Google Ads sign-in</h1>"
                        f"<p>{message}</p></html>"
                    ).encode("utf-8")
                    self.send_response(status)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Referrer-Policy", "no-referrer")
                    self.send_header(
                        "Content-Security-Policy",
                        "default-src 'none'; frame-ancestors 'none'",
                    )
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.end_headers()
                    self.wfile.write(body)

            class Server(_Server):
                address_family = family

            try:
                receiver = Server(
                    (host, parsed.port if parsed.port is not None else 80), Handler
                )
            except OSError as exc:
                raise ConfigurationError(
                    "Could not open the local OAuth callback. Free the configured port or "
                    "unset GOOGLE_ADS_OAUTH_REDIRECT_URI to use an available port, then call get_auth_url."
                ) from exc
            try:
                port = receiver.server_address[1]
                authority = (
                    f"[{host}]:{port}"
                    if family == socket.AF_INET6
                    else f"{host}:{port}"
                )
                redirect = urlunparse(
                    parsed._replace(netloc=authority, path=parsed.path or "/")
                )
                url = auth.build_auth_url(settings, redirect)
                state = parse_qs(urlparse(url).query)["state"][0]
                flow = _Flow(receiver, redirect, state)
                self._flow = flow
                threading.Thread(
                    target=receiver.serve_forever,
                    kwargs={"poll_interval": 0.1},
                    daemon=True,
                ).start()
                flow.timer = threading.Timer(
                    auth.AUTH_TTL_SECONDS, self._expire, args=(flow,)
                )
                flow.timer.daemon = True
                flow.timer.start()
                return url
            except Exception:
                receiver.server_close()
                raise

    def _expire(self, flow: _Flow) -> None:
        with self.lock:
            self._finish(flow, "expired")

    def _receive(
        self,
        flow: _Flow,
        path: str,
        host: str | None,
        settings: Settings,
        auth_file: Path,
        on_saved: Callable[[], None],
    ) -> tuple[int, str]:
        if self._flow is not flow or flow.status != "waiting_for_browser":
            return 410, "This sign-in is no longer active. Run get_auth_url again."
        parsed = urlparse(path)
        expected = urlparse(flow.redirect_uri)
        query = parse_qs(parsed.query, keep_blank_values=True)
        if (
            parsed.scheme
            or parsed.netloc
            or parsed.fragment
            or parsed.path != expected.path
            or host != expected.netloc
            or len(query.get("state", [])) != 1
            or not secrets.compare_digest(
                query["state"][0].encode(), flow.state.encode()
            )
        ):
            return 400, "Invalid callback. Use the link from the latest get_auth_url."
        if "error" in query and "code" not in query:
            self._finish(flow, "denied")
            return 400, "Sign-in was not authorized. Run get_auth_url to try again."
        if "error" in query or len(query.get("code", [])) != 1 or not query["code"][0]:
            return 400, "Invalid callback. Use the link from the latest get_auth_url."
        try:
            token = auth.exchange_code_for_refresh_token(
                settings, flow.redirect_uri + "?" + parsed.query, flow.redirect_uri
            )
            auth.save_refresh_token(token, auth_file)
            on_saved()
        except Exception:
            self._finish(flow, "failed")
            return 500, "Sign-in could not be completed. Run get_auth_url to try again."
        self._finish(flow, "stored")
        return (
            200,
            "Sign-in complete. Return to Claude and run auth_status. You can close this tab.",
        )


oauth_callback = OAuthCallback()
