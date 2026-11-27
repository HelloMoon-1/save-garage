import ipaddress
import json
from pathlib import Path
import socket
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'engine'), str(ROOT / 'vendor')]
import app
from poc import dt_source


class LocalIPv6Tests(unittest.TestCase):
    def setUp(self):
        self.sock = Mock()
        self.sock.getsockname.return_value = ('192.0.2.1', 1234)
        self.adapters = {
            'Wi-Fi': [SimpleNamespace(family=socket.AF_INET, address='192.0.2.1')],
            'VPN': [SimpleNamespace(family=socket.AF_INET6, address='fe80::1%9')],
        }

    def test_reconnect_after_enabling_ipv6_on_the_selected_adapter(self):
        with patch('psutil.net_if_addrs', return_value=self.adapters):
            with self.assertRaises(dt_source.LocalIPv6Unavailable) as failure:
                dt_source.local_link_local(self.sock)
            event = json.dumps({'issue': 'local_ipv6', 'adapter': failure.exception.adapter})
            self.assertEqual(app.upload_network_hint('[network] ' + event),
                             {'code': 'local_ipv6', 'adapter': 'Wi-Fi', 'platform': sys.platform})
            self.adapters['Wi-Fi'].append(SimpleNamespace(family=socket.AF_INET6, address='fe80::2%5'))
            self.assertEqual(dt_source.local_link_local(self.sock), ipaddress.IPv6Address('fe80::2').packed)

    def test_windows_fallback_without_psutil_uses_only_the_connected_adapter(self):
        rows = [{"InterfaceAlias": "VPN", "IPAddress": "fe80::1"},
                {"InterfaceAlias": "家庭网络", "IPAddress": "192.0.2.1"}]
        with patch.dict(sys.modules, psutil=None), patch.object(sys, 'platform', 'win32'), \
                patch.dict(dt_source.os.environ, SystemRoot='C:/Windows'), \
                patch.object(dt_source.subprocess, 'run') as query:
            query.return_value.stdout = json.dumps(rows)
            with self.assertRaises(dt_source.LocalIPv6Unavailable) as failure:
                dt_source.local_link_local(self.sock)
            self.assertEqual(failure.exception.adapter, '家庭网络')
            rows.append({"InterfaceAlias": "家庭网络", "IPAddress": "fe80::2%5"})
            query.return_value.stdout = json.dumps(rows)
            self.assertEqual(dt_source.local_link_local(self.sock), ipaddress.IPv6Address('fe80::2').packed)
            query.side_effect = OSError('unavailable')
            with self.assertRaisesRegex(ValueError, 'could not read Windows network adapters'):
                dt_source.local_link_local(self.sock)

    def test_unknown_interface_and_unrelated_messages(self):
        with patch('psutil.net_if_addrs', return_value={}):
            with self.assertRaises(dt_source.LocalIPv6Unavailable) as failure:
                dt_source.local_link_local(self.sock)
            self.assertIsNone(failure.exception.adapter)
        for line in ('[cmd] session ended: timed out', '[network] invalid', '[network] {}'):
            self.assertIsNone(app.upload_network_hint(line))
