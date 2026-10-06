import http.server
import threading

import pytest

from task_manager.tasks import wis2


class _FakeSock:
    def __init__(self, ip):
        self.ip = ip
        self.closed = False

    def getpeername(self):
        return (self.ip, 443)

    def close(self):
        self.closed = True


@pytest.mark.parametrize("ip", [
    "10.0.0.1", "172.16.0.1", "192.168.1.1",   # private
    "127.0.0.1", "::1",                         # loopback
    "169.254.169.254", "fe80::1",               # link-local (cloud metadata)
    "100.64.0.1",                               # carrier-grade NAT
    "0.0.0.0", "224.0.0.1",                     # unspecified, multicast
    "::ffff:10.0.0.1",                          # IPv4-mapped private
])
def test_non_public_peer_blocked(ip):
    sock = _FakeSock(ip)

    with pytest.raises(wis2.BlockedAddressError):
        wis2._check_public_peer(sock)

    assert sock.closed


@pytest.mark.parametrize("ip", ["8.8.8.8", "2001:4860:4860::8888", "::ffff:8.8.8.8"])
def test_public_peer_allowed(ip):
    sock = _FakeSock(ip)

    wis2._check_public_peer(sock)

    assert not sock.closed


class _OkHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


@pytest.fixture
def local_server():
    server = http.server.HTTPServer(("127.0.0.1", 0), _OkHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server.server_address[1]
    server.shutdown()
    server.server_close()


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost"])
def test_pool_blocks_private_host(local_server, host):
    with pytest.raises(wis2.BlockedAddressError):
        wis2._pool.request("GET", f"http://{host}:{local_server}/", retries=False)


def test_pool_allows_private_host_when_opted_in(local_server, monkeypatch):
    monkeypatch.setattr(wis2, "DOWNLOAD_ALLOW_PRIVATE_ADDRESSES", True)

    response = wis2._pool.request("GET", f"http://127.0.0.1:{local_server}/", retries=False)

    assert response.status == 200
    assert response.data == b"ok"


def test_blocked_download_fails_without_retry(request_mock):
    request_mock.side_effect = wis2.BlockedAddressError("10.0.0.1 is not a public address")
    job = {
        "topic": "cache/a/wis2/x/data/core/obs", "target": "t", "filter": {},
        "_broker": "b", "_received": "r", "_queued": "q",
        "payload": {
            "id": "m-ssrf",
            "properties": {"data_id": "wis2/x/data/ssrf-1", "pubtime": "2026-10-02T10:00:00Z"},
            "links": [{"rel": "canonical", "href": "http://10.0.0.1/file.bufr"}],
        },
    }

    result = wis2.download_from_wis2.run(job)

    assert result["status"] == wis2.STATUS_FAILED
    assert result["error_class"] == "BlockedAddressError"
    request_mock.assert_called_once()
