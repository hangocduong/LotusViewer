"""Lý do kết thúc do engine gửi sang GTK."""
from lotusviewer import chuoi


def test_remote_disconnect_reason_is_translated():
    assert chuoi.ly_do("The remote computer disconnected.") == "Máy kia đã ngắt kết nối."
    assert chuoi.ly_do("The remote computer disconnected. Details") == "Máy kia đã ngắt kết nối."
    assert chuoi.ly_do("The Windows computer disconnected.") == "Máy kia đã ngắt kết nối."
    assert chuoi.ly_do("unknown") == chuoi.KET_THUC_MAC_DINH
