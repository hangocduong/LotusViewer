"""Mọi chuỗi người dùng thấy. Thông báo tiếng Anh của engine chỉ vào log, không hiện ra giao diện."""
from __future__ import annotations

TEN_APP = "LotusViewer"

TAB_NHAN = "Nhận hỗ trợ"
TAB_DIEU_KHIEN = "Điều khiển máy khác"

NHAN_GIOI_THIEU = "Đọc ID và mật khẩu dưới đây cho người hỗ trợ bạn."
NHAN_ID = "ID máy này"
NHAN_MAT_KHAU = "Mật khẩu"
NHAN_CHUA_CO = "—"
NHAN_DANG_DANG_KY = "Đang đăng ký máy này…"
NHAN_DANG_CHO = "Đang chờ kết nối. Mỗi kết nối đều phải được bạn duyệt."
NHAN_BAT_DAU = "Bắt đầu chia sẻ"
NHAN_DUNG = "Dừng chia sẻ"
NHAN_CHI_X11 = "Chỉ hỗ trợ phiên X11"

DK_GIOI_THIEU = "Nhập ID và mật khẩu của máy cần điều khiển."
DK_ID = "ID máy kia"
DK_MAT_KHAU = "Mật khẩu"
DK_GAN_DAY = "ID gần đây"
DK_KET_NOI = "Kết nối"
DK_DANG_KET_NOI = "Đang kết nối…"
DK_ID_SAI = "ID chỉ gồm chữ số."
DK_THIEU_MAT_KHAU = "Hãy nhập mật khẩu của máy kia."

CLIPBOARD = "Chia sẻ clipboard"
CLIPBOARD_GHI_CHU = "Áp dụng cho lần chia sẻ hoặc kết nối tiếp theo."
CAI_DAT = "Cài đặt…"

DUYET_TIEU_DE = "Có người muốn kết nối"
DUYET_NOI_DUNG = "{ten} (ID do máy kia tự khai: {id}) muốn kết nối vào máy này."
DUYET_TEN_TRONG = "Một máy không rõ tên"
DUYET_DEM_NGUOC = "Tự từ chối sau {giay} giây."
DUYET_TU_CHOI = "Từ chối"
DUYET_CHI_XEM = "Chỉ cho xem"
DUYET_DIEU_KHIEN = "Cho xem và điều khiển"

PHIEN_DUOC_HO_TRO = "Đang được hỗ trợ bởi {ten}"
PHIEN_DIEU_KHIEN = "Đang điều khiển {id}"
PHIEN_CHI_XEM_DIEU_KHIEN = "Đang xem {id} (chỉ xem)"
PHIEN_CHO_PHEP_DIEU_KHIEN = "Cho phép điều khiển"
PHIEN_DUOC_DIEU_KHIEN = "Máy kia cho phép điều khiển. Bật tắt bằng phím F12 trong cửa sổ phiên."
PHIEN_CHI_XEM = "Máy kia chỉ cho xem."
PHIEN_CLIPBOARD_BAT = "Clipboard: đang chia sẻ"
PHIEN_CLIPBOARD_TAT = "Clipboard: không chia sẻ"
PHIEN_GUI = "Gửi"
PHIEN_GUI_TEP = "Gửi tệp…"
PHIEN_KET_THUC = "Kết thúc"
PHIEN_BAN = "Bạn"
PHIEN_MAY_KIA = "Máy kia"
PHIEN_DA_GUI_TEP = "Đã gửi tệp {ten}."
PHIEN_TEP_XONG = "Đã chuyển xong tệp {ten}."
PHIEN_TEP_LOI = "Không chuyển được tệp {ten}."
PHIEN_TEP_HUY = "Đã huỷ tệp {ten}."
PHIEN_TEP_GUI_XONG = "Đã chuyển xong một tệp."
PHIEN_CHON_TEP = "Chọn tệp để gửi"
PHIEN_HUY = "Huỷ"
PHIEN_CHON = "Chọn"

TEP_TIEU_DE = "Nhận tệp?"
TEP_NOI_DUNG = "Nhận tệp {ten} ({co})?"
TEP_NHAN = "Nhận"
TEP_TU_CHOI = "Từ chối"

DONG_TIEU_DE = "Đang có phiên"
DONG_NOI_DUNG = "Đóng LotusViewer sẽ kết thúc phiên đang chạy. Vẫn đóng?"
DONG_DONG = "Đóng"
DONG_O_LAI = "Ở lại"

CD_TIEU_DE = "Cài đặt"
CD_TEN = "Tên hiển thị"
CD_TEN_GOI_Y = "Để trống thì dùng tên mặc định"
CD_THU_MUC = "Thư mục nhận tệp"
CD_CLIPBOARD = "Chia sẻ clipboard mặc định"
CD_LUU = "Lưu"
CD_HUY = "Huỷ"

KET_THUC_MAC_DINH = "Phiên đã kết thúc."
LOI_ENGINE = "Không chạy được LotusViewer. Chi tiết ở {log}."
LOI_PHIEN_BAN = "Bộ máy LotusViewer không khớp phiên bản giao diện. Hãy cài lại LotusViewer."
LOI_GUI_TEP = "Không gửi được tệp này."

# Lý do kết thúc và trạng thái của engine → câu tiếng Việt. Khoá là tiền tố câu tiếng Anh.
LY_DO = (
    ("The remote computer disconnected", "Máy kia đã ngắt kết nối."),
    ("The incoming request was declined", "Đã từ chối kết nối."),
    ("The incoming connection timed out", "Kết nối hết thời gian chờ. Hãy nhờ máy kia kết nối lại."),
    ("The incoming relay did not provide an address", "Kết nối không hoàn tất. Hãy nhờ máy kia kết nối lại."),
    ("The incoming relay disconnected", "Mất kết nối với máy kia."),
    ("You ended the incoming session", "Bạn đã kết thúc phiên."),
    ("The Windows computer disconnected", "Máy kia đã ngắt kết nối."),
    ("The Windows viewer requested an unsupported screen color mode", "Máy kia cần chế độ màu 16-bit."),
    ("The Windows viewer needs modern 16-bit screen mode", "Máy kia cần chế độ màu 16-bit."),
    ("The host stopped", "Đã dừng chia sẻ."),
    ("The LotusViewer window closed", "Cửa sổ phiên đã đóng."),
    ("Screen capture failed", "Không chụp được màn hình."),
    ("Disconnected", "Đã ngắt kết nối."),
    ("Session ended", "Phiên đã kết thúc."),
    ("The partner ID is not online", "Máy kia không trực tuyến."),
    ("The partner did not accept the session in time", "Máy kia không nhận phiên kịp thời."),
    ("UltraViewer rejected the partner password", "Sai mật khẩu."),
    ("UltraViewer passwords must be ASCII", "Mật khẩu chỉ gồm chữ không dấu và số."),
    ("UltraViewer did not answer", "Máy chủ UltraViewer không trả lời. Kiểm tra mạng rồi thử lại."),
    ("UltraViewer declined the partner lookup", "Không tìm được máy kia."),
    ("Too many wrong passwords", "Sai mật khẩu quá nhiều lần. Máy này tạm từ chối kết nối mới trong 5 phút."),
    ("Registering this computer", "Đang đăng ký máy này…"),
    ("Restoring the relay connection", "Đang nối lại…"),
    ("Finding the partner computer", "Đang tìm máy kia…"),
    ("Connecting", "Đang kết nối…"),
    ("Waiting for the partner to accept the session", "Đang chờ máy kia nhận phiên…"),
    ("Connected directly over the local network", "Đã kết nối."),
    ("Connected", "Đã kết nối."),
    ("Refreshing the remote screen", "Đang làm mới màn hình máy kia…"),
)


def ly_do(english: str, mac_dinh: str = KET_THUC_MAC_DINH) -> str:
    for tien_to, cau in LY_DO:
        if english.startswith(tien_to):
            return cau
    return mac_dinh


def co_tep(so_byte: int) -> str:
    don_vi = ("B", "KB", "MB", "GB", "TB")
    gia_tri, i = float(so_byte), 0
    while gia_tri >= 1024 and i < len(don_vi) - 1:
        gia_tri, i = gia_tri / 1024, i + 1
    so = f"{gia_tri:.0f}" if i == 0 else f"{gia_tri:.1f}".replace(".", ",")
    return f"{so} {don_vi[i]}"
