"""
🚀 CORE AGENT APPLICATION (DAY 03: CHATBOT VS REACT AGENT)
Thực thi so sánh giữa Chatbot Baseline (Cấp 2) và ReAct Agent kết nối MCP Server (Cấp 3).
Đề tài: Trợ lý Tư vấn Sức khỏe Vinmec (tra cứu lịch bác sĩ & đặt lịch khám).
"""

import json
import os
import sys
import time
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from mcp_server import MCPAcademicServer
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    REACT_AGENT_SYSTEM_PROMPT,
    MAX_ITERATIONS
)
from providers import get_llm_provider

load_dotenv()

def load_test_cases():
    """Tải danh sách 5 test cases từ config/test_cases.json hoặc config/test_cases.example.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    if not os.path.exists(config_path):
        example_path = os.path.join(base_dir, "config", "test_cases.example.json")
        if os.path.exists(example_path):
            print("⚠️ [CONFIG NOTICE]: Chưa thấy file 'config/test_cases.json'. Đang dùng mẫu 'config/test_cases.example.json'.")
            print("👉 Hãy chạy: copy config/test_cases.example.json config/test_cases.json và viết test cases theo đề tài của bạn!\n")
            config_path = example_path
        else:
            config_path = "test_cases.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_waterfall_trace(trace_data: list, filename: str = "trace_waterfall.json", label: str = "Waterfall Trace"):
    """Ghi vết log ra file docs/<filename> (mặc định docs/trace_waterfall.json cho test suite nộp bài)"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    trace_path = os.path.join(docs_dir, filename)
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, ensure_ascii=False, indent=2)
    print(f"📊 [OBSERVABILITY]: Đã lưu {len(trace_data)} sự kiện {label} tại '{trace_path}'!")


def run_baseline_chatbot(user_query: str, provider) -> str:
    """Chạy Chatbot gốc (Cấp 2) không có công cụ gọi Tool. Trả về câu trả lời để so sánh với Agent."""
    print(f"\n💬 [CHATBOT BASELINE - CẤP 2] Câu hỏi: {user_query}")
    start = time.time()
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot phản hồi ({round((time.time() - start) * 1000)} ms):\n{response}")
    return response


def run_react_agent(user_query: str, provider, mcp_server: MCPAcademicServer) -> list:
    """
    [REACT AGENT LOOP - TASK 2.2] Thực thi vòng lặp Thought -> Action -> Observation với MCP Server.
    Hỗ trợ ĐA BƯỚC: sau mỗi Observation, lịch sử Action/Observation được nạp lại cho LLM để
    LLM tự quyết định gọi tool tiếp theo hay đưa ra Final Answer.
    Trả về danh sách trace log của phiên thực thi.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")

    step = 0
    trace_logs = []
    history = []            # Chuỗi messages assistant(tool_calls) + tool(observation) cho các vòng sau
    tools_list = mcp_server.list_tools()
    finished = False

    while step < MAX_ITERATIONS:
        step += 1
        step_start_time = time.time()
        print(f"\n--- 🔄 Vòng lặp ReAct Loop (Step {step}/{MAX_ITERATIONS}) ---")

        # Gọi LLM với Native Tool Calling Specs + lịch sử ReAct trước đó
        llm_response = provider.generate_with_tools(
            user_query, tools_list, system_prompt=REACT_AGENT_SYSTEM_PROMPT, history=history
        )
        llm_latency_ms = round((time.time() - step_start_time) * 1000, 2)

        thought = llm_response.get("thought", "Đang suy luận...")
        print(f"🧠 [Thought]: {thought}")

        # Trường hợp 1: LLM quyết định trả lời bằng văn bản trực tiếp (Final Answer)
        if llm_response.get("type") == "text":
            final_content = llm_response.get("content", "")
            print(f"🏁 [Final Answer]: {final_content}")
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": thought,
                "output": final_content,
                "latency_ms": llm_latency_ms
            })
            finished = True
            break

        # Trường hợp 2: LLM đề xuất gọi Tool (Action)
        elif llm_response.get("type") == "tool_call":
            tool_name = llm_response.get("tool_name")
            arguments = llm_response.get("arguments", {})
            tool_call_id = llm_response.get("tool_call_id") or f"call_step{step}"

            print(f"🛠️ [Action Proposed]: {tool_name}({json.dumps(arguments, ensure_ascii=False)})")

            # Thực thi Tool qua MCP Server (JSON-RPC 2.0)
            tool_start_time = time.time()
            mcp_result = mcp_server.call_tool(tool_name, arguments)
            tool_latency_ms = round((time.time() - tool_start_time) * 1000, 2)
            obs_data = mcp_result.get("result", {})

            if not obs_data:
                print(f"👁️ [Observation từ MCP Server]: {{}}")
                print(f"⚠️ [CHÚ Ý]: MCP Server trả về kết quả rỗng! Học viên cần hoàn thành TODO 2.1 trong 'src/mcp_server.py'.")
                obs_data = {"status": "EMPTY", "message": "MCP Server chưa trả về dữ liệu (TODO 2.1)."}
            else:
                print(f"👁️ [Observation từ MCP Server]: {json.dumps(obs_data, ensure_ascii=False)}")

            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "TOOL_EXECUTION",
                "thought": thought,
                "tool_name": tool_name,
                "arguments": arguments,
                "mcp_server": mcp_result.get("server"),
                "observation": obs_data,
                "latency_ms": llm_latency_ms,
                "tool_latency_ms": tool_latency_ms
            })

            # Nạp Action + Observation vào lịch sử để LLM suy luận tiếp ở vòng sau
            history.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": tool_call_id,
                    "type": "function",
                    "function": {"name": tool_name, "arguments": json.dumps(arguments, ensure_ascii=False)}
                }]
            })
            history.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": json.dumps(obs_data, ensure_ascii=False)
            })
            # KHÔNG break: vòng lặp tiếp tục để LLM quyết định gọi tool tiếp hay trả lời

        else:
            print(f"⚠️ [CHÚ Ý]: Phản hồi LLM không hợp lệ: {llm_response}")
            break

    if not finished:
        msg = f"Agent dừng sau {MAX_ITERATIONS} vòng lặp mà chưa đưa ra câu trả lời cuối cùng."
        print(f"⛔ [MAX_ITERATIONS_REACHED]: {msg}")
        trace_logs.append({
            "step": step + 1,
            "query": user_query,
            "action_type": "MAX_ITERATIONS_REACHED",
            "thought": "Vượt quá số vòng lặp cho phép.",
            "output": msg,
            "latency_ms": 0.0
        })

    return trace_logs


if __name__ == "__main__":
    print("==========================================================")
    print("🏫 VINUNI AI COURSE - DAY 03 LAB: CHATBOT VS REACT AGENT (VINMEC HEALTHCARE)")
    print("==========================================================")
    
    provider = get_llm_provider()
    mcp_server = MCPAcademicServer()
    
    print(f"🔌 LLM Provider: {provider.__class__.__name__}")
    print(f"🌐 MCP Server: {mcp_server.server_name}\n")
    
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases thử nghiệm.\n")
    
    if "--interactive" in sys.argv:
        print("🎮 [INTERACTIVE MODE] Trò chuyện trực tiếp với ReAct Agent:")
        print("💡 Gợi ý câu hỏi thử nghiệm:")
        print("   - Câu hỏi chung: 'Vinmec làm việc từ mấy giờ đến mấy giờ?'")
        print("   - Tra cứu lịch bác sĩ: 'Cho tôi xem lịch làm việc của các bác sĩ khoa Tim mạch'")
        print("   - Đặt lịch khám: 'Đặt lịch khám với bác sĩ BS001 lúc 08:00 15/09/2026, tôi tên Huy, SĐT 0912345678'")
        print("   - Đa bước: 'Tôi muốn khám Nhi cho con, đặt giúp bác sĩ nào rảnh sớm nhất, tên Huy, SĐT 0912345678'")
        print("   - Gõ 'exit' hoặc 'quit' để kết thúc phiên trò chuyện.")
        print("   (Trace của phiên chat được lưu riêng tại docs/trace_interactive.json, không ghi đè trace nộp bài.)\n")
        session_traces = []
        while True:
            try:
                user_input = input("👤 Khách hàng hỏi: ").strip()
                if not user_input or user_input.lower() in ["exit", "quit"]:
                    print("👋 Tạm biệt! Kết thúc phiên trò chuyện.")
                    break
                logs = run_react_agent(user_input, provider, mcp_server)
                session_traces.extend(logs)
                save_waterfall_trace(session_traces, filename="trace_interactive.json", label="Interactive Trace")
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Đã thoát phiên tương tác.")
                break
    elif "--all" in sys.argv:
        run_baseline = "--no-baseline" not in sys.argv
        print("🚀 [TEST SUITE MODE] Kiểm tra 5 Test Cases"
              + (" — so sánh Chatbot Cấp 2 vs ReAct Agent Cấp 3:" if run_baseline else ":"))
        if run_baseline:
            print("   (Thêm cờ --no-baseline để bỏ qua Chatbot Baseline, chỉ chạy Agent.)")
        completed_count = 0
        todo_count = 0
        all_traces = []
        comparisons = []

        for tc in tests:
            print(f"\n==================================================")
            print(f"🧪 [{tc['id']}] Loại test: {tc['type']} (Độ phức tạp: {tc['complexity']})")
            print(f"📌 Kỳ vọng: {tc['expected_behavior']}")
            
            if tc["question"].strip().startswith("TODO"):
                print(f"⏸️ [CHƯA KÍCH HOẠT - ĐANG LÀ TODO]:")
                print(f"   {tc['question']}")
                print(f"   👉 Hãy mở file 'config/test_cases.json' để viết câu hỏi thực tế cho Test Case này!")
                todo_count += 1
            else:
                # Cấp 2: Chatbot Baseline (không tool) -> Cấp 3: ReAct Agent (MCP tools) trên cùng câu hỏi
                chatbot_answer = run_baseline_chatbot(tc["question"], provider) if run_baseline else None
                logs = run_react_agent(tc["question"], provider, mcp_server)
                all_traces.extend(logs)
                completed_count += 1

                tools_called = [e["tool_name"] for e in logs if e["action_type"] == "TOOL_EXECUTION"]
                final = next((e["output"] for e in logs if e["action_type"] == "FINAL_ANSWER"), "")
                comparisons.append({
                    "id": tc["id"],
                    "type": tc["type"],
                    "question": tc["question"],
                    "chatbot_baseline_level2": chatbot_answer,
                    "react_agent_level3": {
                        "react_steps": len(logs),
                        "tools_called_via_mcp": tools_called,
                        "final_answer": final
                    }
                })

        print(f"\n==================================================")
        print(f"📊 [KẾT QUẢ TEST SUITE]: Đã thực thi {completed_count}/{len(tests)} Test Cases | {todo_count} Test Cases đang chờ điền câu hỏi (TODO)")
        if all_traces:
            save_waterfall_trace(all_traces)
        if comparisons:
            save_waterfall_trace(comparisons, filename="chatbot_vs_agent.json", label="so sánh Chatbot vs Agent")
            print("\n📋 [BẢNG SO SÁNH CHATBOT (CẤP 2) VS REACT AGENT (CẤP 3)]")
            print(f"{'TC':<6}{'Loại':<24}{'Chatbot (Cấp 2)':<18}{'Agent gọi Tool qua MCP (Cấp 3)':<48}{'Vòng ReAct'}")
            for c in comparisons:
                tools = " -> ".join(c["react_agent_level3"]["tools_called_via_mcp"]) or "(không cần tool)"
                print(f"{c['id']:<6}{c['type']:<24}{'không có tool':<18}{tools:<48}{c['react_agent_level3']['react_steps']}")
        print(f"💡 Để trò chuyện trực tiếp từng câu: Chạy 'python src/app.py --interactive'")
    else:
        # Chế độ mặc định khi chỉ gõ 'python src/app.py'
        print("ℹ️ HƯỚNG DẪN SỬ DỤNG CHƯƠNG TRÌNH:")
        print("  1. Chat trực tiếp liên tục:   python src/app.py --interactive")
        print("  2. Chạy toàn bộ Test Cases:    python src/app.py --all\n")
        
        sample_query = tests[1]["question"]
        print(f"--- 🏁 DEMO CHẠY THỬ 1 TEST CASE MẪU (TC02: Tra cứu lịch bác sĩ) ---")
        logs = run_react_agent(sample_query, provider, mcp_server)
        save_waterfall_trace(logs)
        print("\n💡 Hãy thử ngay lệnh: python src/app.py --interactive để chat trực tiếp!")
