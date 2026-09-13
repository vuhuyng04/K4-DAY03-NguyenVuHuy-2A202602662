"""
🔌 MODEL CONTEXT PROTOCOL (MCP) SERVER MODULE
Mô phỏng kiến trúc MCP Server (Client-Server Architecture) cung cấp công cụ chuẩn hóa.
"""

import json
import sys
from typing import Dict, Any, List
from tools import TOOLS_SCHEMA, dispatch_tool_call

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class MCPAcademicServer:
    """
    Giả lập MCP Server tuân thủ chuẩn giao thức Model Context Protocol
    """
    def __init__(self, server_name: str = "vinmec-healthcare-mcp-server"):
        self.server_name = server_name
        self.version = "2026.1.0"
        
    def list_tools(self) -> List[Dict[str, Any]]:
        """Trả về danh sách các Tools chuẩn giao thức MCP"""
        return TOOLS_SCHEMA
        
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        [TASK 2.1] HỌC VIÊN HOÀN THIỆN HÀM THỰC THI TOOL TRÊN MCP SERVER
        Thực thi request gọi Tool theo chuẩn MCP JSON-RPC
        """
        # 1. Chuyển yêu cầu tới Tool Router (Execution Layer) -> nhận chuỗi JSON kết quả
        raw_result = dispatch_tool_call(tool_name, arguments or {})

        # 2. Parse chuỗi JSON thành Python dict (phòng trường hợp tool trả về text thuần)
        try:
            content = json.loads(raw_result)
        except (json.JSONDecodeError, TypeError):
            content = {"status": "RAW_TEXT", "content": str(raw_result)}

        # 3. Đóng gói phản hồi theo chuẩn JSON-RPC 2.0 của giao thức MCP
        return {
            "jsonrpc": "2.0",
            "server": self.server_name,
            "tool": tool_name,
            "result": content
        }


if __name__ == "__main__":
    print("==========================================================")
    print("🔌 KIỂM THỬ ĐỘC LẬP MCP SERVER (vinmec-healthcare-mcp-server)")
    print("==========================================================")

    server = MCPAcademicServer()
    tools = server.list_tools()
    print(f"✅ Khởi tạo thành công MCP Server: {server.server_name} (Version: {server.version})")
    print(f"📦 Số lượng Tools công bố: {len(tools)}")

    # Kiểm tra trạng thái TODO 1.2 (Tool Schema)
    book_tool = next((t for t in tools if t.get("name") == "book_appointment"), None)
    if not book_tool or not book_tool.get("parameters", {}).get("properties"):
        print("⏳ [TODO 1.2]: Tool 'book_appointment' chưa được định nghĩa properties trong 'src/tools.py'.")
    else:
        print(f"✅ [TODO 1.2]: Tool 'book_appointment' đã có schema đầy đủ (required: {book_tool['parameters'].get('required')}).")

    # Kiểm tra trạng thái TODO 2.1 (call_tool)
    test_result = server.call_tool("doctor_schedule_query", {"specialty": "Tim mạch"})
    if not test_result:
        print("⏳ [TODO 2.1]: Hàm call_tool() đang trả về rỗng. Học viên hãy hoàn thiện TODO 2.1 trong 'src/mcp_server.py'!")
    else:
        print(f"✅ [TODO 2.1]: Test dispatch tool 'doctor_schedule_query' thành công:")
        print(f"   Phản hồi JSON-RPC: {json.dumps(test_result, ensure_ascii=False)}")
