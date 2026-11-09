# ĐỌC TRƯỚC: CÁCH HIỂU PROJECT NÀY TRONG 15 PHÚT

Bạn không cần đọc Python ngay. Hãy đi từ **bài toán kinh doanh → dữ liệu → phát hiện → phương án → quyết định tương lai**.

## 1. Nhà máy làm gì?

Hai sản phẩm P01/P02 đi qua:

**Nguyên vật liệu → Cutting → Grinding → Polishing → Inspection → Thành phẩm → Giao khách.**

Máy Polishing mới hoạt động từ tuần 9; máy Inspection mới từ tuần 13. WIP là bán thành phẩm nằm chờ giữa các công đoạn.

## 2. Vấn đề kinh doanh?

Trong 16 tuần lịch sử, khách đặt **842.905**, nhà máy giao **835.089**, còn thiếu **7.816**. Tồn kho thành phẩm ban đầu là **4.200**, nên **sản lượng sản xuất** và **lượng giao** không giống nhau.

## 3. Điều tra SQL tìm thấy gì?

- WIP trước Grinding tích lên **117.938** tại cuối W16.
- WIP trước Polishing và Inspection đã hết từ W14; hai công đoạn downstream có thể thiếu đầu vào.
- Vì vậy, cần ưu tiên kiểm tra **Grinding** và mối liên hệ với **Cutting**, thay vì mua thêm máy Inspection.
- Lưu ý: `fact_inventory_snapshot.finished_goods_units` chứa giá trị 0 dù sổ cân đối thành phẩm cho thấy từng có FG dương. Dashboard gắn cờ lỗi này.

## 4. Python làm việc gì?

Python giải bài toán: **với công suất các máy, yield từng công đoạn và nhu cầu, nên phân bổ sản xuất theo tuần thế nào để giao được nhiều nhất?**

Đây là Linear Programming. Python không được phép tạo hàng “từ không khí”: tổng nguyên vật liệu, WIP, thành phẩm và đơn giao phải thỏa điều kiện cân bằng.

Trên 16 tuần lịch sử:

- **Actual (đã xảy ra)**: còn thiếu 7.816.
- **As-is LP (không mua máy, tối ưu kế hoạch)**: mô hình còn thiếu khoảng 4.469.
- **OT +10% Cutting/Grinding từ tuần 9**: mô hình đạt 0 backlog tại W16.
- **Perf +5pp** hoặc **+1 máy Grinding từ W9**: cũng đạt 0 backlog tại W16 trong các điều kiện giả định.

Các phương án này **không hề thay đổi lịch sử**. Chúng là phép kiểm tra *giả sử nhà máy đã có một kế hoạch khác*, đồng thời dùng dữ liệu lịch sử để xem logic của mô hình có hợp lý hay không. LP ở đây biết trước kết quả cả 16 tuần; không được xem như forecast thực thụ.

## 5. Thế project giúp ích gì cho quyết định tương lai?

Project còn một phần riêng **Forward W17–W24**, hoàn toàn chưa xảy ra.

- Dự báo thêm khoảng **607.573** đơn vị nhu cầu qua 8 tuần bằng xu hướng từ dữ liệu W9–W16 (chỉ là giả định, chưa được kiểm định).
- Mang sang tuần 17 backlog 7.816 và WIP trước Grinding 117.938 từ cuối W16.
- Dưới nhu cầu tăng nhanh giả định, chỉ thêm một máy Grinding hoặc tăng ca 10% vẫn chưa giải quyết hết thiếu hàng.
- Thêm máy Cutting **không giúp tăng số hàng giao trong những phương án đang thử**, vì đã có WIP rất lớn trước Grinding.
- Nếu mở rộng Grinding, **Polishing có thể trở thành bottleneck mới** (100% load ở W24 trong phương án F3).

**Ý nghĩa:** Không phải cứ thấy máy nào bận thì mua thêm; phải tính toàn dây chuyền và kiểm tra dự báo trước khi phê duyệt CAPEX.

## 6. Nên mở file nào trước?

1. **`outputs/dashboard.html`**: xem biểu đồ và kết quả thực tế, scenario, future forecast.
2. **`PROJECT_REPORT_VI.md`**: đọc số liệu và lời giải chi tiết.
3. **`notebooks/Apple_GSM_Manufacturing_Case.ipynb`**: xem Python đã chạy, các bảng và biểu đồ.
4. **`sql/01_sqlite_reproduce.sql`**: xem các truy vấn thật trên data gốc.
5. **`powerbi/README_POWERBI.md`**: dựng báo cáo `.pbix` trên Power BI Desktop của bạn.

**Chú ý:** Dataset là synthetic case, không phải dữ liệu Apple. File HTML là dashboard hoàn chỉnh chạy độc lập; muốn có `.pbix` cần dựng trên Power BI Desktop từ CSV + DAX đi kèm. Các giả định chi phí, forecast và stress test chưa được xác minh bằng dữ liệu doanh nghiệp thực.
