# LotusViewer

LotusViewer là fork của [DeanOpen/MacViewer](https://github.com/DeanOpen/MacViewer), giữ lịch sử và giấy phép MIT của mã nguồn upstream. Giữ nguyên attribution trong `LICENSE` và `THIRD_PARTY_NOTICES.md`.

Thay đổi của LotusOS hiện có: ghim toolchain Rust; dùng crate vendored ngoài Git; cấu hình release một codegen unit, bỏ symbols; đóng gói engine thành `.deb` tái lập. Chưa có launcher GTK3 và chưa đo phiên với UltraViewer Windows.

Đây không phải sản phẩm chính thức của UltraViewer, không được UltraViewer chứng thực. Engine phụ thuộc relay bên thứ ba. `Sources/UltraViewerProtocol/Resources/8bit.dat` là tài nguyên do UltraViewer cung cấp, không có giấy phép phân phối lại và không thuộc MIT; không phải open-source. Chủ dự án ngày 2026-10-21 quyết định đóng kèm như upstream; pháp nhân Hải Anh nhận rủi ro phân phối và ToS UltraViewer chưa được rà soát đầy đủ.
