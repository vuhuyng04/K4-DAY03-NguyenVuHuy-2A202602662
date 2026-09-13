"""
🔌 MULTI-PROVIDER LLM ADAPTER (Google Gemini, OpenAI & Offline Mock)
Hỗ trợ Native Tool Calling và chuyển đổi linh hoạt qua biến môi trường LLM_PROVIDER.
"""

import os
import sys
import json
import re
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

class BaseLLMProvider:
    """Interface cơ sở cho các LLM Provider hỗ trợ Native Tool Calling"""
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "",
                            history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Gọi LLM với Native Tool Calling.
        history: danh sách các lượt Action/Observation trước đó (chuẩn OpenAI messages:
                 assistant(tool_calls) + tool(tool_call_id, content)) để hỗ trợ ReAct đa bước.
        """
        raise NotImplementedError


class MockOfflineProvider(BaseLLMProvider):
    """Offline Mock Provider dùng để chạy thử mà không tốn API Key"""
    def __init__(self):
        self.model_name = "Offline-Mock-Model-2026"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return f"[Mock Chatbot Response]: Xin chào! Tôi đã nhận được câu hỏi '{prompt}'. (Chế độ Chatbot không có Tool tra cứu dữ liệu thời gian thực)."

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "",
                            history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        prompt_lower = prompt.lower()
        history = history or []
        called_tools = [m["tool_calls"][0]["function"]["name"] for m in history
                        if m.get("role") == "assistant" and m.get("tool_calls")]
        wants_booking = any(k in prompt_lower for k in ["đặt lịch", "đặt khám", "book"])

        # Các vòng sau: đã có Observation -> mô phỏng ReAct đa bước hoặc kết thúc
        if called_tools:
            if wants_booking and "book_appointment" not in called_tools:
                return {
                    "type": "tool_call",
                    "tool_name": "book_appointment",
                    "arguments": {"patient_name": "Khách hàng Mock", "phone": "0900000000",
                                  "doctor_id": "BS003", "datetime_str": "08:30 15/09/2026"},
                    "thought": "[Mock] Đã có kết quả tra cứu bác sĩ, tiếp tục gọi book_appointment để đặt lịch."
                }
            return {
                "type": "text",
                "content": "[Mock Agent Response]: Đã tổng hợp kết quả từ MCP Server và hoàn tất yêu cầu của bạn.",
                "thought": "[Mock] Đã nhận đủ Observation từ Tool, tổng hợp câu trả lời cuối cùng."
            }

        # Vòng đầu tiên: nhận diện intent gọi Tool
        doctor_id_match = re.search(r"\bbs\d{3}\b", prompt_lower)
        if wants_booking and doctor_id_match:
            return {
                "type": "tool_call",
                "tool_name": "book_appointment",
                "arguments": {"patient_name": "Khách hàng Mock", "phone": "0900000000",
                              "doctor_id": doctor_id_match.group(0).upper(), "datetime_str": "08:00 15/09/2026"},
                "thought": "[Mock] Người dùng yêu cầu đặt lịch và đã cung cấp mã bác sĩ. Gọi tool book_appointment."
            }
        elif any(k in prompt_lower for k in ["bác sĩ", "lịch", "khoa", "khám", "đặt"]):
            if "vũ trụ" in prompt_lower:
                specialty = "Vũ trụ"
            elif "nhi" in prompt_lower:
                specialty = "Nhi"
            elif "da liễu" in prompt_lower:
                specialty = "Da liễu"
            else:
                specialty = "Tim mạch"
            return {
                "type": "tool_call",
                "tool_name": "doctor_schedule_query",
                "arguments": {"specialty": specialty},
                "thought": f"[Mock] Người dùng muốn thông tin bác sĩ/lịch khám. Gọi tool doctor_schedule_query cho khoa {specialty}."
            }
        else:
            return {
                "type": "text",
                "content": "[Mock Agent Response]: Vinmec làm việc 07:00 - 17:00 từ Thứ Hai đến Thứ Bảy, Cấp cứu 24/7.",
                "thought": "[Mock] Câu hỏi chung về thông tin bệnh viện, trả lời trực tiếp không cần gọi Tool."
            }


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider (Native Tool Calling với Google GenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-2.5-flash"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(model=self.model_name, contents=contents)
            return response.text
        except Exception as e:
            return f"[Gemini Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "",
                            history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            print("ℹ️ [Gemini Provider]: Chưa tìm thấy GEMINI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt, history)

        # Gemini: nối các Action/Observation trước đó vào prompt dưới dạng ngữ cảnh ReAct
        if history:
            ctx_lines = []
            for m in history:
                if m.get("role") == "assistant" and m.get("tool_calls"):
                    fn = m["tool_calls"][0]["function"]
                    ctx_lines.append(f"Action: {fn['name']}({fn['arguments']})")
                elif m.get("role") == "tool":
                    ctx_lines.append(f"Observation: {m.get('content')}")
            prompt = (prompt + "\n\n[LỊCH SỬ REACT TRƯỚC ĐÓ]\n" + "\n".join(ctx_lines)
                      + "\nDựa vào Observation ở trên, hãy gọi tool tiếp theo nếu còn thiếu dữ liệu, hoặc trả lời cuối cùng.")
        
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            
            # Chuẩn hóa function declarations cho Gemini SDK
            function_declarations = []
            for tool in tools_schema:
                # Bỏ qua các tool schema chưa được định nghĩa hoàn chỉnh
                if not tool.get("name") or not tool.get("parameters"):
                    continue
                function_declarations.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {})
                })

            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                tools=[{"function_declarations": function_declarations}] if function_declarations else None,
                temperature=0.2
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

            # Kiểm tra xem Gemini có trả về Tool Call không
            if response.function_calls:
                call = response.function_calls[0]
                args = dict(call.args) if hasattr(call, 'args') and call.args else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.name,
                    "arguments": args,
                    "thought": f"Gemini quyết định gọi công cụ '{call.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": response.text or "",
                    "thought": "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }

        except Exception as e:
            print(f"⚠️ [Gemini API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt, history)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (Native Tool Calling với OpenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return "[OpenAI Error]: Chưa cấu hình OPENAI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(model=self.model_name, messages=messages)
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[OpenAI Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "",
                            history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            print("ℹ️ [OpenAI Provider]: Chưa tìm thấy OPENAI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt, history)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)

            tools = []
            for tool in tools_schema:
                if not tool.get("name"):
                    continue
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {})
                    }
                })

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            # Nạp lịch sử Action/Observation của các vòng ReAct trước (hỗ trợ đa bước)
            if history:
                messages.extend(history)

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                temperature=0.2
            )

            msg = response.choices[0].message
            if msg.tool_calls:
                call = msg.tool_calls[0]
                args = json.loads(call.function.arguments) if call.function.arguments else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.function.name,
                    "arguments": args,
                    "tool_call_id": call.id,
                    "thought": (msg.content.strip() + " | " if msg.content else "")
                               + f"OpenAI quyết định gọi công cụ '{call.function.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": msg.content or "",
                    "thought": "OpenAI phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }
        except Exception as e:
            print(f"⚠️ [OpenAI API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt, history)


def get_llm_provider() -> BaseLLMProvider:
    """Factory function khởi tạo Provider theo LLM_PROVIDER env variable"""
    provider_type = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    if provider_type == "gemini":
        key = os.getenv("GEMINI_API_KEY")
        if key and key != "your_gemini_api_key_here":
            return GeminiProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if key and key != "your_openai_api_key_here":
            return OpenAIProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "mock":
        return MockOfflineProvider()
    else:
        return MockOfflineProvider()
