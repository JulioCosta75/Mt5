"""Unit tests for MT5 login error message mapping (no live terminal required)."""
from __future__ import annotations

import unittest

from mt5_service import format_login_error


class FormatLoginErrorTests(unittest.TestCase):
    def test_auth_failed_minus_6(self):
        msg = format_login_error(-6, (-6, "Terminal: Authorization failed"))
        self.assertIn("Não foi possível entrar na conta MT5", msg)
        self.assertIn("login", msg.lower())
        self.assertIn("password", msg.lower())
        self.assertIn("servidor", msg.lower())
        self.assertNotIn("login failed:", msg)

    def test_server_not_found_minus_2(self):
        msg = format_login_error(-2, (-2, "Common: No connection"))
        self.assertIn("Servidor MT5 não encontrado", msg)
        self.assertIn("PepperstoneUK-Demo", msg)

    def test_server_not_found_minus_4(self):
        msg = format_login_error(-4, (-4, "Terminal: No connection"))
        self.assertIn("Servidor MT5 não encontrado", msg)

    def test_ipc_timeout_minus_10005(self):
        msg = format_login_error(-10005, (-10005, "IPC timeout"))
        self.assertIn("IPC timeout (-10005)", msg)
        self.assertIn("Close MetaTrader 5", msg)

    def test_unmapped_keeps_technical_detail(self):
        err = (-999, "Some obscure failure")
        msg = format_login_error(-999, err)
        self.assertIn("Não foi possível ligar à MT5", msg)
        self.assertIn("Detalhe técnico para suporte:", msg)
        self.assertIn(str(err), msg)


if __name__ == "__main__":
    unittest.main()
