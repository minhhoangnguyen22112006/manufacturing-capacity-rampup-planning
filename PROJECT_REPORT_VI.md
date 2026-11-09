# BÁO CÁO PROJECT — MANUFACTURING CAPACITY & RAMP-UP OPTIMIZATION

**Loại dữ liệu:** synthetic case, không phải dữ liệu nội bộ Apple hay một nhà cung cấp có thật.  
**Giai đoạn quan sát:** W1–W16, 05/01/2026–26/04/2026.  
**Công cụ:** SQL / SQLite / SQL Server T-SQL / Python SciPy HiGHS / Plotly / Power BI CSV + DAX.  
**Phạm vi:** hai sản phẩm P01/P02, bốn công đoạn, 15 máy (13 hoạt động đầu kỳ, bổ sung 1 Polishing W9 và 1 Inspection W13).

## 1. Tóm tắt điều hành

Nhà máy phải đáp ứng nhu cầu tăng dần qua 16 tuần. Tổng 842.905 đơn vị được đặt, 835.089 đã giao và 7.816 chưa được đáp ứng ở cuối W16, tương đương fulfillment **99,07%** theo tổng số lượng đơn đặt hàng. 4.200 thành phẩm tồn đầu kỳ giúp giải thích vì sao shipped units lớn hơn tổng thành phẩm sản xuất trong kỳ.

Phân tích cân bằng vật chất cho thấy sau tuần 16 còn **117.938** đơn vị WIP giữa Cutting và Grinding, trong khi WIP trước Polishing và Inspection về **0**. Đây là bằng chứng về mất cân bằng công suất nghiêm trọng ở Grinding, đồng thời cho thấy việc chỉ mở rộng downstream không bảo đảm đáp ứng nhu cầu.

Mô hình LP hoạch định công suất cho cả 16 tuần, khi chỉ sử dụng máy móc hiện trạng nhưng tối ưu kế hoạch theo thông tin đã biết, ước lượng có thể giao **838.436** đơn vị (còn thiếu **4.469**), tăng **3.347** so với lịch sử. Ba can thiệp riêng lẻ (tăng ca Cutting/Grinding, tăng performance 5 điểm phần trăm, thêm Grinding từ W9) đều có nghiệm giao đủ **842.905** trong mô hình xác định. Với các giả định chi phí đã nêu, overtime có chi phí tăng thêm trực tiếp thấp nhất trong tập phương án được thử.

**Không diễn giải các kết quả mô phỏng thành sản lượng thực tế đã đạt được; không áp dụng mô hình hindsight như dự báo tương lai.**

## 2. Câu hỏi kinh doanh

- Supplier capacity có đáp ứng demand và ramp-up hay không?
- Bottleneck và WIP hình thành ở đâu, trong giai đoạn nào?
- Nếu có thêm công suất ở Cutting/Grinding, downstream có tiếp nhận được không?
- Trong các phương án có thể thử, cách nào giải quyết thiếu hụt với chi phí giả định hợp lý nhất?

## 3. Quy trình sản xuất

`Raw Material → Cutting → WIP 1 → Grinding → WIP 2 → Polishing → WIP 3 → Inspection → Finished Goods → Shipment`.

- Cutting: 3 máy.
- Grinding: 4 máy.
- Polishing: 3 máy đầu kỳ, bổ sung M0304 W9 → 4 máy.
- Inspection: 3 máy đầu kỳ, bổ sung M0404 W13 → 4 máy.
- Yield: `Good Units / Input Units`.
- WIP cuối kỳ: `WIP đầu kỳ + Good upstream - Input downstream`.
- Finished Inventory: `FG đầu kỳ + Final-stage good - Shipped`.
- Backlog: `Backlog đầu kỳ + Demand - Shipped`.

## 4. Kết quả SQL — Actual

### 4.1. Quy mô data

- 6.160 production rows: 5.280 Completed, 880 No schedule.
- 32 firm customer orders (P01/P02 × 16 tuần).
- 222 shipment records.
- 15 máy định danh; lịch commissioning theo dim_machine.
- 224 daily inventory snapshot rows.

### 4.2. Toàn kỳ

| Công đoạn | Input | Good | Scrap | Tổng yield |
|---|---:|---:|---:|---:|
| Precision Cutting | 1.023.444 | 1.011.572 | 11.872 | 98,84% |
| Edge Grinding | 893.634 | 875.783 | 17.851 | 98,00% |
| Surface Polishing | 875.783 | 840.158 | 35.625 | 95,93% |
| Optical Inspection | 840.158 | 830.889 | 9.269 | 98,90% |

Không được so sánh trực tiếp tổng `Good` giữa hai stage mà bỏ qua WIP dịch chuyển theo tuần.

### 4.3. Kiểm tra tại tuần 16

| Stage | Operating minutes | Actual ideal workload minutes | Observed load |
|---|---:|---:|---:|
| Cutting | 16.850 | 15.939,25 | 94,59% |
| Grinding | 22.308 | 20.494,18 | 91,87% |
| Polishing | 22.079 | 17.363,47 | 78,64% |
| Inspection | 22.245 | 14.884,67 | 66,91% |

`Observed load` **không phải** measured machine performance. Downstream load thấp một phần có thể là do chưa có đủ bán thành phẩm. Tại tuần 16, nominal-capacity load của Cutting/Grinding hơi vượt 100% (100,58% và 100,18%) so với sản lượng thực tế; điều này nhấn mạnh nominal factor chỉ là thông số gần đúng, không phải hard historical capacity chính xác tuyệt đối.

### 4.4. Tồn WIP cuối mỗi giai đoạn quan trọng

| Tuần | Trước Grinding | Trước Polishing | Trước Inspection |
|---|---:|---:|---:|
| W8 | 59.651 | 52.431 | 0 |
| W9 | 65.824 | 42.882 | 6.477 |
| W12 | 86.723 | 14.684 | 21.797 |
| W13 | 95.587 | 4.302 | 8.896 |
| W14 | 102.883 | 0 | 0 |
| W15 | 110.500 | 0 | 0 |
| W16 | 117.938 | 0 | 0 |

WIP trước Grinding tăng mạnh, trong khi những buffer downstream đã được dùng hết từ W14. Sau đó throughput cuối dây chuyền gần như bị giới hạn bởi flow mới từ Grinding. Đây là dấu hiệu ưu tiên điều tra năng lực Grinding; cần thêm thông tin schedule và material transfer mới kết luận nhân quả hoàn toàn.

### 4.5. Nhu cầu và fulfillment lịch sử

- Tổng đơn hàng: **842.905**.
- Tổng sản lượng hoàn thành qua Inspection: **830.889**.
- Thành phẩm tồn đầu kỳ: **4.200**.
- Thực giao: **835.089**.
- Kết chuyển FG cuối kỳ: **0**.
- Chưa đáp ứng W16: **7.816** (P01: 4.380, P02: 3.436).
- Trong dữ liệu, mọi **shipment row đã ghi nhận** đều giao không muộn hơn due date; phần **chưa ship** không được xem là “giao đúng hạn”. Đơn hàng bị giao thiếu cuối kỳ, nên không thể báo “OTIF 100%”.

Đối chiếu cân bằng:

`830.889 + 4.200 = 835.089`.

### 4.6. Data Quality: lỗi snapshot Finished Goods

Sổ tính toán từ sản lượng, tồn đầu kỳ và giao hàng cho thấy tồn thành phẩm thực tế đã có lúc dương (ví dụ tổng **25.157** ở W4), trong khi `fact_inventory_snapshot.finished_goods_units` ở toàn bộ snapshot đều bằng 0. Sai lệch lớn nhất tại cấp sản phẩm/tuần là **16.379** đơn vị. Trong dashboard, dùng `calculated_ending_fg` và giữ cột `fg_reconciliation_delta` làm dấu vết kiểm tra. WIP snapshots khớp **0 sai lệch** với cân bằng sản xuất cuối tuần.

## 5. Kết quả Python — Planning simulation và intervention

### 5.1. Input, variables và constraints

- Input: demand từng tuần/sản phẩm; yield từng tuần/stage/sản phẩm; cycle time và nominal performance từng máy; operating time deduplicate; lịch commissioning; initial stock; material receipts.
- Biến: sản lượng xử lý theo machine/product/week, WIP cuối tuần, FG cuối tuần, nguyên vật liệu cuối tuần, shipment và backlog theo product/week.
- Ràng buộc: capacity từng máy; raw-material conservation; WIP flow; FG flow; demand/backlog balance; biến không âm.
- Mục tiêu: ưu tiên tuyệt đối backlog thấp, sau đó hạn chế tồn kho và sản xuất thừa (LP với penalty, **không phải MILP tối ưu tổng chi phí**).
- Các biến sản lượng là liên tục và mô hình giả định các công đoạn có thể truyền sản phẩm trong cùng tuần.

### 5.2. Kết quả deterministic, 16 tuần

| Plan | Shipped units | Backlog W16 | Fulfillment | Policy cost (USD, giả định) |
|---|---:|---:|---:|---:|
| Actual observed | 835.089 | 7.816 | 99,07% | Không tính như scenario |
| S0 LP / máy hiện trạng | 838.436 | 4.469 | 99,47% | 22.346 |
| S1 OT +10% Cutting/Grinding từ W9 | 842.905 | 0 | 100,00% | 1.321 |
| S2 Perf +5pp tất cả máy từ W9 | 842.905 | 0 | 100,00% | 48.000 |
| S3 Thêm Grinding W9 | 842.905 | 0 | 100,00% | 75.000 |
| S4 OT + thêm Grinding | 842.905 | 0 | 100,00% | 76.104 |
| S5 OT + Perf + thêm Grinding | 842.905 | 0 | 100,00% | 124.044 |

**Giải thích điều kiện can thiệp:** can thiệp chỉ từ W9, công suất bổ sung ở C được giả định sẵn sàng ngay W9. Để đáp ứng commissioning W9 với lead time 3 tuần, cần quyết định mua trước đó (ví dụ vào W6); thời điểm mua không được tối ưu trong bộ LP này. Không thể áp dụng những quyết định đó vào tuần 16 rồi tuyên bố ngược rằng sản lượng tuần 9 thay đổi.

**Giả định cost:** `Backlog cost = $5/đơn vị/tuần`, OT tăng thêm dùng công thức `1,5× labor hourly + energy hourly`, machine purchase cost Grinding là $75.000; cải thiện performance 5pp toàn bộ 4 stage tính 4×$12.000. Những con số chỉ minh họa quyết định, không phải audited total cost, không phải chi phí Apple.

Scenario cost đã tính theo overtime **thực sự cần dùng trên capacity nominal**, không phải mọi phút được cho phép tăng ca. Không có khấu hao CAPEX, giá trị còn lại, downtime/ramp learning của máy mới hay chi phí vốn.

### 5.3. Interpretation

S0 cho thấy tối ưu lại lịch sản xuất có thể cải thiện fulfillment mà không thay đổi cấu hình thiết bị. Nếu cần xóa backlog toàn kỳ, ở bộ giả định thử nghiệm này S1 là phương án rẻ nhất **trong số 6 chính sách đã thử**. S3 chỉ nên được phê duyệt nếu có lý do dài hạn như nhu cầu tiếp tục tăng sau tuần 16, cần thêm khả năng chống rủi ro, công suất cần duy trì nhiều quý hoặc chi phí overtime thực tế cao hơn.

**Không khẳng định S1 là global optimum**: chưa có MILP endogenously chọn giờ OT và thời điểm đầu tư theo chi phí thực; chi phí thực tế chưa được xác minh. Mọi kịch bản đều dùng nhu cầu/yield/downtime lịch sử mà optimizer “biết trước”.

## 6. Monte Carlo stress test

150 trial với các shock giả định W9–W16:
- Demand: shock chung tuần SD khoảng 2,5% kết hợp shock sản phẩm SD 1,8%.
- Operating time: shock chung khoảng 2,5% và riêng máy 1,2%.
- Yield: SD 0,15 điểm phần trăm cho stage/product/week.

Kết quả: S0 có mean backlog ~**4.377**, P90 ~**10.619**, ~**32,7%** số mẫu xóa hết backlog. Với các shock được thử, S1, S2, S3 xóa hết backlog ở 150/150 mẫu. **Không được diễn giải đây là xác suất 100% giao hàng tương lai** vì mô hình tái tối ưu với thông tin toàn bộ kết quả ngẫu nhiên (perfect foresight), biến động giả định tương đối nhỏ và chưa kiểm định phân phối trên dữ liệu holdout.

## 7. Kết luận quản trị và CV

**Findings:** demand ramp làm lộ mất cân bằng giữa Cutting/Grinding và downstream; WIP before Grinding cuối kỳ 117.938; hàng chưa đáp ứng sau khi dùng hết FG buffer là 7.816; mua thêm thiết bị Inspection trước khi giải quyết upstream có thể không tối ưu.

**Recommendation trong phạm vi case:** sử dụng data-based supplier capacity reviews; theo dõi tuần `Good/Operating Minutes`, `WIP by buffer`, `Committed demand`, `Shipments vs due`, và tiến hành OT có mục tiêu ở Cutting/Grinding nếu trade-off chi phí và an toàn phù hợp. Chỉ cân nhắc CAPEX nếu có forecast và ROI > horizon 16 tuần.

**Gợi ý CV bằng tiếng Anh (phải ghi synthetic case):**

> Developed an end-to-end 16-week synthetic manufacturing capacity case using SQL, Python linear programming, and Power BI-ready data models; reconciled 842.9k customer-order units, 835.1k shipments, and 117.9k units of interstage WIP; evaluated six capacity interventions and quantified service-cost trade-offs with scenario and stress analysis.

## 8. Hạn chế và bước tiếp theo để thành predictive decision tool

1. Backtest rolling-origin: tại W8 chỉ sử dụng dữ liệu đến W8 để ước lượng W9–W16; kiểm tra chênh lệch forecast và decision outcome. Bộ LP hiện có *look-ahead bias*.
2. Tích hợp lead time mua máy, performance ramp của máy mới và công suất OT tối đa theo công nhân/ca.
3. Mô hình hóa scheduling theo ca, transfer lag, batch setup, sequence-dependent processing, đặc biệt nếu P01 và P02 khác cycle time.
4. Thay cost assumptions bằng quotation, overtime policy, lost sales penalty và residual value; sau đó xây MILP cost-minimizing.
5. Kiểm tra/sửa data quality của inventory snapshot trước khi triển khai thường xuyên.

## 9. Các file để nghiên cứu

- `sql/01_sqlite_reproduce.sql`: SQL truy vấn trực tiếp SQLite đã đóng gói.
- `sql/02_sqlserver_ssms.sql`: T-SQL tương đương trên các schema `dbo_clean`/`stg` đang dùng.
- `python/run_project.py`: ETL, validation, LP, 6 scenario và export CSV.
- `python/stress_test.py`: 150 trial sensitivity experiment.
- `notebooks/Apple_GSM_Manufacturing_Case.ipynb`: notebook đã chạy, có bảng và biểu đồ.
- `outputs/dashboard.html`: dashboard HTML tương tác chạy offline.
- `outputs/*.csv`: các bảng dữ liệu kết quả.
- `powerbi/README_POWERBI.md` + `powerbi/MEASURES.dax`: dựng report Power BI Desktop.

## 10. Phụ lục Forward Planning — W17–W24 (để ra quyết định hướng tới tương lai)

Để không nhầm **counterfactual lịch sử** với **ra quyết định cho tương lai**, project có thêm module `python/forward_plan.py`, dùng **chỉ dữ liệu thực tế W1–W16** làm đầu vào dự báo:

- Forecast demand của P01 và P02 bằng hồi quy xu hướng tuyến tính sử dụng **W9–W16**; dự báo mới W17–W24 là **607.573** đơn vị (không phải đơn hàng đã được xác nhận).
- WIP, raw inventory, FG và backlog mở đầu W17 được lấy từ cuối W16. Trong đó backlog mở đầu = **7.816** đơn vị và WIP trước Grinding = **117.938**.
- Yield kế hoạch là yield gộp từ W13–W16; machine operating minutes kế hoạch là bình quân W13–W16. Receipts giả định tiếp diễn bình quân W13–W16. Đây là các giả định, không phải future actuals.
- Máy đầu tư giả định đặt ở W17, lead time 3 tuần và vận hành từ W20. Không dùng thông tin kết quả thực tế W17–W24 (vì chưa có).

### 10.1. Kết quả mô phỏng planning horizon W17–W24

| Forward scenario | Fulfilled units | Unfulfilled cuối W24 | Fulfillment trên nhu cầu mới + backlog mở đầu |
|---|---:|---:|---:|
| F0 Năng lực hiện tại | 420.007 | 195.382 | 68,3% |
| F1 OT 10% Cutting/Grinding | 461.902 | 153.487 | 75,1% |
| F2 Thêm Grinding từ W20 | 465.589 | 149.801 | 75,7% |
| F3 OT + Grinding từ W20 | 481.299 | 134.091 | 78,2% |
| F4 Thêm Grinding + Cutting từ W20 | 465.589 | 149.801 | 75,7% |
| F5 OT + thêm Grinding + Cutting | 481.299 | 134.091 | 78,2% |

Trong F3, stage load tại tuần 24 là Cutting **94,1%**, Grinding **87,0%**, Polishing **100,0%**, Inspection **83,6%**. Kết quả cho thấy khi mở rộng Grinding, giới hạn có thể dịch sang **Polishing**. Đặc biệt, mua thêm một máy Cutting không cải thiện kết quả so với phương án chỉ mua Grinding, vì Cutting đã tạo lượng WIP đầu vào lớn. Đây là minh họa quan trọng về **bottleneck migration** và tránh CAPEX sai chỗ.

**Cảnh báo:** forecast xu hướng tuyến tính từ 8 điểm dữ liệu rất mong manh, có thể phóng đại tăng trưởng. Tất cả các phương án trong bảng vẫn thiếu hàng đáng kể dưới forecast này. Không được khuyến nghị mua máy thật dựa trên bảng một cách máy móc: phải kiểm tra demand commitments, các kịch bản forecast, vật tư, planned downtime và ROI nhiều quý.

### 10.2. Vì sao project này có cả actual và future?

**W1–W16:** bằng chứng kiểm tra vấn đề, quality audit và counterfactual replay để hiểu có thể đã ra quyết định khác thế nào.  
**W17–W24:** mô hình planning dùng historical data làm input để ra quyết định cho giai đoạn chưa xảy ra, minh họa khả năng dự báo và trade-off trong supply management.  
**Bước tiếp theo nếu triển khai thật:** rolling-origin backtesting (train W1–W8 → test W9–W12; train W1–W12 → test W13–W16), dùng forecast error để lập demand scenarios, và tối ưu lead time đầu tư với chi phí có thật.

Dữ liệu của module này: `outputs/forward_demand_forecast_W17_W24.csv`, `outputs/forward_service_W17_W24.csv`, `outputs/forward_capacity_W17_W24.csv`, `outputs/forward_scenario_summary_W17_W24.csv`; có tab riêng trong `outputs/dashboard.html` và hướng dẫn Power BI.
