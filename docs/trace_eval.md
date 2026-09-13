# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Nguyễn Vũ Huy  
> **Mã Sinh Viên / Mã Học viên:** 2A202602662  
> **Chủ đề Lựa chọn:** Gợi ý 4.3 — *Trợ lý Tư vấn Sức khỏe Vinmec* (Tra cứu lịch làm việc bác sĩ chuyên khoa & Đặt lịch khám bệnh)  
> **LLM Provider nghiệm thu:** OpenAI `gpt-4o-mini` (Native Tool Calling) — MCP Server: `vinmec-healthcare-mcp-server`

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** | 4 / 5 | Yêu cầu "đặt lịch với bác sĩ khoa Nhi rảnh sớm nhất" bắt buộc Agent chia thành 2 bước nối tiếp: (1) tra cứu danh sách bác sĩ + khung giờ trống của khoa → (2) chọn `doctor_id` và slot sớm nhất rồi mới đặt lịch. Không thể làm trong 1 lời gọi vì `book_appointment` cần `doctor_id` chỉ có sau khi tra cứu. Chưa đạt 5 vì chuỗi suy luận tối đa 2–3 bước, chưa có bước đối chiếu/ràng buộc phức tạp (ví dụ: kiểm tra bảo hiểm, lịch sử khám). |
| **2. Tool Interaction** | 5 / 5 | Hệ thống bắt buộc kết nối dữ liệu bên ngoài qua MCP Server: lịch làm việc bác sĩ và khung giờ trống là dữ liệu thời gian thực thay đổi liên tục, LLM không thể tự "biết". Đặt lịch là hành động ghi (write action) tạo `booking_id`, không thể mô phỏng bằng sinh văn bản. Cả 2 tool (1 tra cứu + 1 hành động) đều thiết yếu. |
| **3. Dynamic Decision** | 4 / 5 | Bước tiếp theo phụ thuộc hoàn toàn vào Observation: nếu tra cứu trả `SUCCESS` → Agent trích `doctor_id`/slot để đặt lịch; nếu `NOT_FOUND` (khoa không tồn tại, TC05) → Agent dừng, thông báo lịch sự và gợi ý các khoa hiện có thay vì bịa dữ liệu. Việc chọn bác sĩ nào / khung giờ nào cũng do Agent quyết định từ dữ liệu trả về. Trừ 1 điểm vì số nhánh quyết định còn ít (SUCCESS / NOT_FOUND). |
| **4. Long Horizon Goal** | 3 / 5 | Agent phải giữ mục tiêu "đặt được lịch khám" xuyên suốt 3 vòng lặp ReAct (tra cứu → đặt lịch → tổng hợp), đồng thời nhớ tên và SĐT bệnh nhân từ câu hỏi ban đầu để dùng ở bước 2. Tuy nhiên mỗi phiên chỉ kéo dài trong 1 truy vấn, chưa có Memory dài hạn giữa các phiên (nhắc lịch, tái khám) nên chỉ ở mức trung bình. |
| **TỔNG ĐIỂM AGENTIC FIT** | **16 / 20** | *Tổng điểm > 12/20 → Bài toán rất phù hợp triển khai Agentic System (ReAct Agent), vượt trội so với Chatbot Cấp 2 chỉ sinh văn bản.* |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

> ⚠️ **YÊU CẦU NGHIỆM THU:** Đã cấu hình `.env` với `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4o-mini` và `OPENAI_API_KEY` thật. Khi chạy `python src/app.py --all`, terminal in `🔌 LLM Provider: OpenAIProvider`, không xuất hiện cảnh báo fallback về Mock. Toàn bộ 10 sự kiện trong `docs/trace_waterfall.json` đều do OpenAI sinh ra (trường `thought` bắt đầu bằng `OpenAI quyết định gọi công cụ...` / `OpenAI phản hồi trực tiếp...`).

### 2.1. Trace tiêu biểu — TC04 (Multi-step ReAct: Tra cứu → Đặt lịch → Final Answer)

Câu hỏi: *"Con tôi cần khám khoa Nhi, hãy đặt giúp tôi lịch với bác sĩ khoa Nhi nào có khung giờ trống sớm nhất. Tôi tên Nguyễn Vũ Huy, số điện thoại 0912345678."*

```json
[
  {
    "step": 1,
    "action_type": "TOOL_EXECUTION",
    "thought": "OpenAI quyết định gọi công cụ 'doctor_schedule_query' với tham số: {\"specialty\": \"Nhi\"}",
    "tool_name": "doctor_schedule_query",
    "arguments": { "specialty": "Nhi" },
    "mcp_server": "vinmec-healthcare-mcp-server",
    "observation": {
      "status": "SUCCESS",
      "specialty": "Nhi",
      "data": [
        {
          "doctor_id": "BS003",
          "doctor_name": "BS.CKII Lê Minh Châu",
          "specialty": "Nhi",
          "room": "P.105 - Tòa B",
          "available_slots": ["08:30 15/09/2026", "11:00 15/09/2026", "16:00 15/09/2026"]
        },
        {
          "doctor_id": "BS004",
          "doctor_name": "ThS.BS Phạm Quốc Dũng",
          "specialty": "Nhi",
          "room": "P.107 - Tòa B",
          "available_slots": ["09:30 15/09/2026", "14:30 16/09/2026"]
        }
      ]
    },
    "latency_ms": 920.05,
    "tool_latency_ms": 0.03
  },
  {
    "step": 2,
    "action_type": "TOOL_EXECUTION",
    "thought": "OpenAI quyết định gọi công cụ 'book_appointment' với tham số: {\"patient_name\": \"Nguyễn Vũ Huy\", \"phone\": \"0912345678\", \"doctor_id\": \"BS003\", \"datetime_str\": \"08:30 15/09/2026\"}",
    "tool_name": "book_appointment",
    "arguments": {
      "patient_name": "Nguyễn Vũ Huy",
      "phone": "0912345678",
      "doctor_id": "BS003",
      "datetime_str": "08:30 15/09/2026"
    },
    "mcp_server": "vinmec-healthcare-mcp-server",
    "observation": {
      "status": "SUCCESS",
      "booking_id": "VM-BS003-5678",
      "doctor_name": "BS.CKII Lê Minh Châu",
      "specialty": "Nhi",
      "room": "P.105 - Tòa B",
      "datetime": "08:30 15/09/2026",
      "slot_confirmed": true,
      "message": "Đặt lịch thành công cho bệnh nhân Nguyễn Vũ Huy (SĐT 0912345678) khám Nhi với BS.CKII Lê Minh Châu lúc 08:30 15/09/2026 tại P.105 - Tòa B."
    },
    "latency_ms": 1049.13,
    "tool_latency_ms": 0.05
  },
  {
    "step": 3,
    "action_type": "FINAL_ANSWER",
    "thought": "OpenAI phản hồi trực tiếp bằng văn bản (không cần gọi công cụ).",
    "output": "Tôi đã đặt lịch khám cho con bạn như sau:\n\n- **Bác sĩ**: BS.CKII Lê Minh Châu\n- **Chuyên khoa**: Nhi\n- **Thời gian**: 08:30 ngày 15/09/2026\n- **Phòng khám**: P.105 - Tòa B\n- **Mã đặt lịch**: VM-BS003-5678\n\nBạn vui lòng đến quầy lễ tân để xác nhận lịch khám. Nếu cần thêm thông tin gì, hãy cho tôi biết nhé!",
    "latency_ms": 2197.45
  }
]
```

**Phân tích:** Agent tự chọn bác sĩ `BS003` và khung giờ `08:30 15/09/2026` (slot sớm nhất trong Observation bước 1) để đặt lịch ở bước 2, đồng thời giữ đúng tên + SĐT bệnh nhân từ câu hỏi ban đầu — thể hiện đầy đủ chuỗi **Thought → Action → Observation → Thought → Action → Observation → Final Answer**.

### 2.2. Trace edge case — TC05 (Anti-Hallucination với `NOT_FOUND`)

```json
[
  {
    "step": 1,
    "action_type": "TOOL_EXECUTION",
    "tool_name": "doctor_schedule_query",
    "arguments": { "specialty": "Vũ trụ" },
    "observation": {
      "status": "NOT_FOUND",
      "specialty": "Vũ trụ",
      "available_specialties": ["Tim mạch", "Nhi", "Da liễu"],
      "message": "Vinmec hiện không có chuyên khoa 'Vũ trụ' trong hệ thống đặt lịch."
    },
    "latency_ms": 1015.09
  },
  {
    "step": 2,
    "action_type": "FINAL_ANSWER",
    "output": "Xin lỗi, hiện tại Bệnh viện Vinmec không có chuyên khoa \"Vũ trụ\" trong hệ thống. Bạn có thể tham khảo các chuyên khoa khác như Tim mạch, Nhi, hoặc Da liễu. Nếu bạn cần thông tin về một chuyên khoa nào khác, hãy cho tôi biết!",
    "latency_ms": 1133.43
  }
]
```

### 2.3. Bảng tổng hợp 5 Test Cases (từ `docs/trace_waterfall.json`)

| TC | Loại | Số vòng ReAct | Tool đã gọi qua MCP | Observation status | Kết quả |
| :---: | :--- | :---: | :--- | :--- | :---: |
| TC01 | direct_query | 1 | *(không gọi tool)* | — | ✅ Trả lời trực tiếp giờ làm việc + quy trình khám |
| TC02 | single_tool_query | 2 | `doctor_schedule_query(Tim mạch)` | SUCCESS | ✅ Liệt kê 2 bác sĩ + khung giờ trống |
| TC03 | appointment_booking | 2 | `book_appointment(BS001, 08:00 15/09/2026)` | SUCCESS | ✅ Trả mã đặt lịch `VM-BS001-5678` |
| TC04 | multi_step_reasoning | 3 | `doctor_schedule_query(Nhi)` → `book_appointment(BS003)` | SUCCESS → SUCCESS | ✅ Đa bước, tự chọn slot sớm nhất |
| TC05 | edge_case_handling | 2 | `doctor_schedule_query(Vũ trụ)` | NOT_FOUND | ✅ Không bịa, gợi ý khoa hiện có |

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [x] Đã điền API Key thật trong `.env` và xác nhận Agent chạy mượt mà trên LLM API thật (OpenAI `gpt-4o-mini`).
- **Tổng số Test Cases đã chạy thành công:** **5 / 5** test cases.
- **Số lượt gọi Tool qua MCP Server chính xác:** **5** lượt (TC02: 1, TC03: 1, TC04: 2, TC05: 1) — tổng 10 sự kiện trace (5 `TOOL_EXECUTION` + 5 `FINAL_ANSWER`).
- **Đã thử nghiệm chế độ đàm thoại trực tiếp** `python src/app.py --interactive` thành công.
- **Kết quả đẩy Repo nộp bài:** [x] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

### Các task đã hoàn thành trong mã nguồn

| Task | File | Nội dung |
| :--- | :--- | :--- |
| 1.1 | `config/test_cases.json`, `docs/trace_eval.md` | 5 test case theo đề tài Vinmec; Scoring Matrix 16/20 |
| 1.2 | `src/tools.py` | 2 Tool Schema chuẩn JSON Schema (`doctor_schedule_query`, `book_appointment`) + Mock DB 3 khoa / 5 bác sĩ + Execution Layer |
| 2.1 | `src/mcp_server.py` | `call_tool()` gọi `dispatch_tool_call` → parse JSON → đóng gói JSON-RPC 2.0 (`jsonrpc`, `server`, `tool`, `result`) |
| 2.2 | `src/app.py`, `src/providers.py` | ReAct loop **đa bước**: nạp `history` (assistant tool_calls + tool observation) cho LLM ở vòng sau; trace ghi thêm `thought`, `mcp_server`, `tool_latency_ms`; xử lý `MAX_ITERATIONS_REACHED` |
| 3.1 | `docs/trace_waterfall.json` | 10 sự kiện từ OpenAI API thật |

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
