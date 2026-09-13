"""
🛠️ TOOL DEFINITIONS & EXECUTION BACKEND
Mã nguồn chứa danh sách Tool Schemas (JSON Schema) và Execution Layer phục vụ cho MCP Server.
Đề tài: Trợ lý Tư vấn Sức khỏe Vinmec — tra cứu lịch bác sĩ chuyên khoa & đặt lịch khám bệnh.
"""

import json
from typing import Dict, Any

# ==============================================================================
# 1. KHAI BÁO TOOL SCHEMAS CHUẨN NATIVE JSON SCHEMA (TASK 1.2)
# ==============================================================================

TOOLS_SCHEMA = [
    # Tool 1: Công cụ TRA CỨU — lịch làm việc bác sĩ theo chuyên khoa
    {
        "name": "doctor_schedule_query",
        "description": (
            "Tra cứu danh sách bác sĩ và lịch làm việc (khung giờ còn trống) tại Bệnh viện Vinmec "
            "theo chuyên khoa. Dùng tool này TRƯỚC khi đặt lịch nếu chưa biết mã bác sĩ (doctor_id)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "specialty": {
                    "type": "string",
                    "description": "Tên chuyên khoa cần tra cứu (ví dụ: 'Tim mạch', 'Nhi', 'Da liễu')"
                },
                "doctor_name": {
                    "type": "string",
                    "description": "Tên bác sĩ để lọc kết quả (tùy chọn, ví dụ: 'Nguyễn Văn An')"
                }
            },
            "required": ["specialty"]
        }
    },

    # Tool 2: Công cụ HÀNH ĐỘNG — đặt lịch khám bệnh (TODO 1.2 đã hoàn thiện)
    {
        "name": "book_appointment",
        "description": (
            "Đặt lịch khám bệnh tại Bệnh viện Vinmec cho bệnh nhân với một bác sĩ cụ thể. "
            "Yêu cầu phải có mã bác sĩ (doctor_id) hợp lệ lấy từ kết quả doctor_schedule_query."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "patient_name": {
                    "type": "string",
                    "description": "Họ và tên bệnh nhân đặt lịch (ví dụ: 'Nguyễn Vũ Huy')"
                },
                "phone": {
                    "type": "string",
                    "description": "Số điện thoại liên hệ của bệnh nhân (ví dụ: '0912345678')"
                },
                "doctor_id": {
                    "type": "string",
                    "description": "Mã bác sĩ cần đặt lịch (ví dụ: 'BS001')"
                },
                "datetime_str": {
                    "type": "string",
                    "description": "Thời gian khám mong muốn theo định dạng 'HH:MM DD/MM/YYYY' (ví dụ: '09:00 15/09/2026')"
                }
            },
            "required": ["patient_name", "phone", "doctor_id", "datetime_str"]
        }
    }
]

# ==============================================================================
# 2. MÔ PHỎNG DỮ LIỆU & HÀM THỰC THI TOOL (EXECUTION LAYER)
# ==============================================================================

# Cơ sở dữ liệu mô phỏng: chuyên khoa -> danh sách bác sĩ & khung giờ còn trống
MOCK_DATABASE = {
    "tim mạch": [
        {
            "doctor_id": "BS001",
            "doctor_name": "PGS.TS Nguyễn Văn An",
            "specialty": "Tim mạch",
            "room": "P.201 - Tòa A",
            "available_slots": ["08:00 15/09/2026", "10:30 15/09/2026", "14:00 16/09/2026"]
        },
        {
            "doctor_id": "BS002",
            "doctor_name": "TS.BS Trần Thị Bình",
            "specialty": "Tim mạch",
            "room": "P.203 - Tòa A",
            "available_slots": ["09:00 15/09/2026", "15:30 15/09/2026"]
        }
    ],
    "nhi": [
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
    ],
    "da liễu": [
        {
            "doctor_id": "BS005",
            "doctor_name": "BS.CKI Hoàng Thu Hà",
            "specialty": "Da liễu",
            "room": "P.302 - Tòa A",
            "available_slots": ["10:00 15/09/2026", "13:30 16/09/2026"]
        }
    ]
}

# Tra cứu nhanh bác sĩ theo mã
DOCTOR_INDEX = {doc["doctor_id"]: doc for docs in MOCK_DATABASE.values() for doc in docs}


def execute_doctor_schedule_query(specialty: str, doctor_name: str = "") -> str:
    """Thực thi tra cứu lịch làm việc bác sĩ theo chuyên khoa (lọc thêm theo tên nếu có)"""
    key = specialty.strip().lower().replace("khoa ", "")
    doctors = MOCK_DATABASE.get(key)
    if not doctors:
        return json.dumps({
            "status": "NOT_FOUND",
            "specialty": specialty,
            "available_specialties": [d[0]["specialty"] for d in MOCK_DATABASE.values()],
            "message": f"Vinmec hiện không có chuyên khoa '{specialty}' trong hệ thống đặt lịch."
        }, ensure_ascii=False)

    if doctor_name:
        name_lower = doctor_name.strip().lower()
        doctors = [d for d in doctors if name_lower in d["doctor_name"].lower()]
        if not doctors:
            return json.dumps({
                "status": "NOT_FOUND",
                "specialty": specialty,
                "message": f"Không tìm thấy bác sĩ '{doctor_name}' thuộc chuyên khoa '{specialty}'."
            }, ensure_ascii=False)

    return json.dumps({
        "status": "SUCCESS",
        "specialty": doctors[0]["specialty"],
        "data": doctors
    }, ensure_ascii=False)


def execute_book_appointment(patient_name: str, phone: str, doctor_id: str, datetime_str: str) -> str:
    """Thực thi đặt lịch khám bệnh với bác sĩ theo mã bác sĩ"""
    doctor = DOCTOR_INDEX.get(doctor_id.strip().upper())
    if not doctor:
        return json.dumps({
            "status": "NOT_FOUND",
            "doctor_id": doctor_id,
            "message": f"Mã bác sĩ '{doctor_id}' không tồn tại. Hãy tra cứu lịch bác sĩ trước khi đặt lịch."
        }, ensure_ascii=False)

    slot_ok = datetime_str.strip() in doctor["available_slots"]
    return json.dumps({
        "status": "SUCCESS",
        "booking_id": f"VM-{doctor['doctor_id']}-{phone[-4:]}",
        "patient_name": patient_name,
        "phone": phone,
        "doctor_id": doctor["doctor_id"],
        "doctor_name": doctor["doctor_name"],
        "specialty": doctor["specialty"],
        "room": doctor["room"],
        "datetime": datetime_str,
        "slot_confirmed": slot_ok,
        "message": (
            f"Đặt lịch thành công cho bệnh nhân {patient_name} (SĐT {phone}) khám {doctor['specialty']} "
            f"với {doctor['doctor_name']} lúc {datetime_str} tại {doctor['room']}."
            + ("" if slot_ok else " Lưu ý: khung giờ này không nằm trong lịch trống, bệnh viện sẽ gọi xác nhận lại.")
        )
    }, ensure_ascii=False)


# Router gọi tool thực tế
TOOL_ROUTER = {
    "doctor_schedule_query": execute_doctor_schedule_query,
    "book_appointment": execute_book_appointment
}

def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Hàm trung chuyển thực thi tool"""
    if tool_name in TOOL_ROUTER:
        try:
            return TOOL_ROUTER[tool_name](**arguments)
        except Exception as e:
            return json.dumps({"status": "EXECUTION_ERROR", "error": str(e)}, ensure_ascii=False)
    return json.dumps({"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại!"}, ensure_ascii=False)
