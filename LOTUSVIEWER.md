# LotusViewer

LotusViewer là fork của [DeanOpen/MacViewer](https://github.com/DeanOpen/MacViewer), giữ lịch sử và giấy phép MIT của mã nguồn upstream. Giữ nguyên attribution trong `LICENSE` và `THIRD_PARTY_NOTICES.md`.

Thay đổi của LotusOS hiện có: ghim toolchain Rust; dùng crate vendored ngoài Git; cấu hình release một codegen unit, bỏ symbols; đóng gói engine thành `.deb` tái lập; bộ vá engine dưới đây. Launcher GTK3 nằm trong `lotusviewer-gtk/`. Bằng chứng VM và điều kiện phát hành do kho LotusOS quản lý.

## Bộ vá engine

Khi merge upstream, giữ nguyên các điểm này; test trong `cargo test` canh từng điểm.

1. **Giao thức `--ipc` (v1)** cho `host` và `connect`, ở `LinuxViewer/src/ipc.rs`. Ở chế độ này stdout chỉ có các dòng giao thức, chữ cho người đọc ở stderr. Mọi trường văn bản đến từ máy xa là chuỗi JSON một dòng, nên chat hay tên tệp không mở được dòng mới. Mỗi trường ID chỉ là chữ số, ID xa không hợp lệ ghi là `0`.

   | Dòng stdout | Nghĩa |
   |---|---|
   | `IPC 1` | Bắt tay, luôn là dòng đầu |
   | `ID <digits> PASSWORD <json>` | ID và mật khẩu của máy (host) |
   | `REQUEST <digits> <json-name>` | Có kết nối xin vào (host) |
   | `CONNECTED <digits>` | Phiên đã bắt đầu |
   | `CONTROL on\|off` | Bên kia có được điều khiển hay không |
   | `CHAT <json>` | Tin chat của bên kia |
   | `FILE <id> <size> <json-name>` | Bên kia gửi tệp |
   | `FILE-DONE <id>` | Tệp xong |
   | `FILE-FAIL <id> <json>` | Tệp lỗi hoặc bị huỷ (`"Canceled"`) |
   | `STATUS <json>` | Trạng thái |
   | `ENDED <json>` | Phiên kết thúc, kèm lý do |

   Lệnh stdin giữ như upstream. Host nhận `y`/`v`/`n`, `c`, `x`, `t <text>`, `f <path>`, `a <id>`, `r <id>`. Connect nhận `t`, `f`, `a`, `r`, `x`; quyền điều khiển phía connect bật tắt bằng F12 trong cửa sổ phiên. Ở `--ipc`, cửa sổ phiên không hiện chat và tắt F8, vì giao diện LotusViewer lo phần chat.
2. **`connect --password-stdin`**: dòng đầu stdin là mật khẩu, nên mật khẩu không nằm trên argv. Dùng cùng `--password` thì engine báo lỗi.
3. **Engine dừng khi stdin đóng** ở `--ipc`. Host báo kết thúc phiên cho viewer, huỷ đăng ký relay rồi thoát rc 0. Connect đóng phiên. Ngoài `--ipc`, host vẫn bỏ qua stdin đóng như upstream.
4. **Gỡ hai đường bỏ qua an toàn.** Đã xoá cờ `host --auto-approve`, nên phiên host chỉ bắt đầu sau lệnh `y` hoặc `v`. Đã xoá biến `LINUXVIEWER_INSECURE_RELAY`, nên TLS relay luôn kiểm chứng chỉ theo `webpki-roots` cộng Sectigo R46. Duyệt tay và khoá sau 5 lần sai mật khẩu giữ nguyên.
5. **Connect không tự nhận tệp.** Tệp đến chỉ được ghi vào `--download-dir` sau lệnh `a <id>` (ngoài `--ipc` là `/accept <id>`). Lệnh `r <id>` (`/cancel <id>`) hoặc phiên kết thúc khi chưa trả lời thì huỷ tệp và không để lại gì trên đĩa.
6. **Thư mục cấu hình** là `$XDG_CONFIG_HOME/lotusviewer/`, mặc định `~/.config/lotusviewer/`. Thư mục có mode 0700, tệp hồ sơ 0600. Recents và token Wayland cũng nằm ở đây. Không di trú từ `linuxviewer`.
7. **Mật khẩu host đổi mỗi lượt chạy.** ID giữ nguyên (khoá theo `device_identity` và MAC), mật khẩu 8 chữ số được sinh lại mỗi lần `host` khởi động và ghi đè `host-profile`. Hồ sơ phía connect không đổi.
8. **Clipboard từ viewer cần quyền điều khiển.** Ở chế độ chỉ xem (`v`, hoặc sau lệnh `c` tắt điều khiển), engine bỏ clipboard viewer gửi tới, như bỏ sự kiện chuột và phím. Chia sẻ clipboard vẫn chỉ chạy khi người dùng bật khi bắt đầu phiên.

9. **Từ chối khác hết giờ.** Khi đang chờ duyệt, lệnh `n` gửi mã 39 (blocked); hết 45 giây hoặc kết thúc phiên vẫn gửi 27. Client giữ lý do blocked cả trước khởi tạo qua relay và LAN. Cần đo lại tương thích với UltraViewer Windows trước receipt.
10. **Nhận diện và trạng thái phiên.** Tên login mặc định và tiêu đề cửa sổ dùng LotusViewer; tiêu đề dịch nhãn điều khiển, âm thanh, phóng, màn hình và trợ giúp. Nội dung `HELP` giữ nguyên. GTK dịch lý do remote disconnected, hiển thị chỉ xem theo `CONTROL off` và yêu cầu hộp nhận tệp nằm trên cửa sổ phiên; vẫn chỉ nhận sau khi người dùng duyệt.

Đây không phải sản phẩm chính thức của UltraViewer, không được UltraViewer chứng thực. Engine phụ thuộc relay bên thứ ba. `Sources/UltraViewerProtocol/Resources/8bit.dat` là tài nguyên do UltraViewer cung cấp, không có giấy phép phân phối lại và không thuộc MIT; không phải open-source. Chủ dự án ngày 2026-10-21 quyết định đóng kèm như upstream; pháp nhân Hải Anh nhận rủi ro phân phối và ToS UltraViewer chưa được rà soát đầy đủ.
