import streamlit as st
import json
from openai import OpenAI
from streamlit_folium import st_folium

# 🟢 导入我们拆分好的模块
import config
import tools
import utils

# ==========================================
# 1. 页面基础设置
# ==========================================
st.set_page_config(page_title="AI 智能旅行管家 (自主思考版)", page_icon="🧠", layout="wide")

# 初始化客户端 (使用 config 中的 Key)
try:
    client = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
except Exception as e:
    st.error("API Key 配置有误，请检查代码。")
    st.stop()

# ==========================================
# 3. 状态管理 (Session State)
# ==========================================

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "current_chat_id" not in st.session_state:
    st.session_state["current_chat_id"] = None
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "system", "content": config.SYSTEM_PROMPT},
        {"role": "assistant", "content": "Hello! I am your Autonomous AI Agent. Where are we going today?"}
    ]
if "download_buffer" not in st.session_state: 
    st.session_state["download_buffer"] = None
if "map_data" not in st.session_state: 
    st.session_state["map_data"] = None
if "traffic_data" not in st.session_state: 
    st.session_state["traffic_data"] = None

# 👇 专门处理删除逻辑的函数 (保留在 app.py 方便 UI 调用)
def delete_chat_history(index):
    if 0 <= index < len(st.session_state["chat_history"]):
        st.session_state["chat_history"].pop(index)
        
        if st.session_state["current_chat_id"] == index:
            st.session_state["current_chat_id"] = None
            st.session_state["messages"] = [
                {"role": "system", "content": config.SYSTEM_PROMPT},
                {"role": "assistant", "content": "Chat deleted."}
            ]
            st.session_state["download_buffer"] = None
            st.session_state["map_data"] = None 
            st.session_state["traffic_data"] = None
        elif st.session_state["current_chat_id"] is not None and st.session_state["current_chat_id"] > index:
            st.session_state["current_chat_id"] -= 1

# ==========================================
# 🔴 Sidebar UI (侧边栏)
# ==========================================
with st.sidebar:
    st.title("🗂️ Control Panel")
    
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        # 自动保存旧对话
        if len(st.session_state["messages"]) > 2:
            user_first_msg = "New Chat"
            for msg in st.session_state["messages"]:
                if msg["role"] == "user":
                    content = msg.get("content", "")
                    user_first_msg = content[:15] + "..."
                    break
            
            if st.session_state["current_chat_id"] is None:
                st.session_state["chat_history"].insert(0, {
                    "title": user_first_msg,
                    "messages": st.session_state["messages"],
                    "itinerary_content": None
                })
        
        # 重置 (使用 config 中的 prompt)
        st.session_state["messages"] = [
            {"role": "system", "content": config.SYSTEM_PROMPT},
            {"role": "assistant", "content": "Hello! Where are we going today?"}
        ]
        st.session_state["current_chat_id"] = None
        st.session_state["download_buffer"] = None
        st.session_state["map_data"] = None 
        st.session_state["traffic_data"] = None 
        st.rerun()

    # 下载按钮
    if st.session_state.get("download_buffer"):
        st.markdown("---")
        st.success("✅ 行程单已生成！")
        st.download_button(
            label="📥 下载 Word 行程单 (.docx)",
            data=st.session_state["download_buffer"],
            file_name="My_Trip_Plan.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary"
        )

    st.markdown("---")
    st.subheader("🕒 History")

    if not st.session_state["chat_history"]:
        st.caption("No history yet")
    
    # 历史记录列表
    for i, chat in enumerate(st.session_state["chat_history"]):
        col1, col2 = st.columns([0.85, 0.15]) 
        with col1:
            if st.button(f"💬 {chat['title']}", key=f"hist_{i}", use_container_width=True):
                if len(st.session_state["messages"]) > 2 and st.session_state["current_chat_id"] is None:
                     temp_title = "Unsaved"
                     for m in st.session_state["messages"]:
                         if m["role"] == "user":
                             temp_title = m.get("content", "")[:15] + "..."
                             break
                     st.session_state["chat_history"].insert(0, {
                         "title": temp_title, 
                         "messages": st.session_state["messages"],
                         "itinerary_content": None
                     })

                st.session_state["messages"] = chat["messages"]
                st.session_state["current_chat_id"] = i
                
                # 恢复内容 (调用 utils 中的 create_word_doc)
                saved_content = chat.get("itinerary_content")
                if saved_content:
                    st.session_state["download_buffer"] = utils.create_word_doc(saved_content)
                else:
                    st.session_state["download_buffer"] = None
                
                st.rerun()
        
        with col2:
            st.button("🗑️", key=f"del_{i}", on_click=delete_chat_history, args=(i,))

# ==========================================
# 5. 聊天主界面
# ==========================================
st.title("🧠 My AI Travel Agent (Map Edition)")

# 1. 聊天记录显示
for msg in st.session_state["messages"]:
    if isinstance(msg, dict):
        role = msg["role"]
        content = msg.get("content")
    else:
        role = msg.role
        content = msg.content
    
    if role == "system": continue

    if content:
        if role == "user": st.chat_message("user").write(content)
        elif role == "assistant": st.chat_message("assistant").write(content)

# [UI] 地图显示区域
if st.session_state.get("map_data"):
    with st.container():
        st.markdown("### 🗺️ 路线地图 & 交通时间")
        if st.session_state.get("traffic_data"):
            with st.expander("🚗 查看详细交通耗时 (驾车 vs 公交)", expanded=True):
                st.markdown(st.session_state["traffic_data"])
        try:
            from streamlit_folium import st_folium
            st_folium(st.session_state["map_data"], width=700, height=400, returned_objects=[])
        except ImportError:
            st.error("⚠️ 缺少地图组件")

# ==========================================
# 核心逻辑
# ==========================================

# 2. 接收用户输入
if prompt := st.chat_input("Say something..."):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    
    if st.session_state["current_chat_id"] is None:
        st.session_state["chat_history"].insert(0, {
            "title": prompt[:15] + "...", 
            "messages": st.session_state["messages"],
            "itinerary_content": None
        })
        st.session_state["current_chat_id"] = 0
    else:
        st.session_state["chat_history"][st.session_state["current_chat_id"]]["messages"] = st.session_state["messages"]
    
    st.rerun()

# 3. AI 思考循环
if st.session_state["messages"] and st.session_state["messages"][-1]["role"] == "user":
    
    with st.chat_message("assistant"):
        status_container = st.status("🧠 Agent is thinking...", expanded=True)
        messages = st.session_state["messages"]
        
        while True:
            # 🟢 使用 tools.tools_list
            response = client.chat.completions.create(model="deepseek-chat", messages=messages, tools=tools.tools_list)
            msg = response.choices[0].message
            
            if msg.tool_calls:
                messages.append(msg)
                should_rerun = False 
                
                for tool in msg.tool_calls:
                    fn, args = tool.function.name, json.loads(tool.function.arguments)
                    status_container.write(f"👉 Action: **{fn}**")
                    
                    res = None
                    # 🟢 修改调用方式：tools.函数名
                    if fn == "search_flights": res = tools.search_flights(args["origin"], args["destination"], args["date"], args.get("return_date"))
                    elif fn == "search_hotels": res = tools.search_hotels(args["city"], args["check_in_date"], args.get("check_out_date"), args.get("adults", 1))
                    elif fn == "search_attractions": res = tools.search_attractions(args["city"], args.get("keyword"))
                    elif fn == "search_restaurants": res = tools.search_restaurants(args["city"], args.get("food_type"))
                    elif fn == "search_general_web": res = tools.search_general_web(args["query"])
                    elif fn == "save_itinerary": res = tools.save_itinerary(args["content"]); status_container.write("💾 Saved!")
                    elif fn == "generate_map_with_traffic": 
                        res = tools.generate_map_with_traffic(args["locations_list"])
                        status_container.write("🗺️ Map Drawn!")
                        should_rerun = True 
                    
                    messages.append({"role": "tool", "tool_call_id": tool.id, "content": str(res)})
                
                if should_rerun:
                    st.rerun()

            else:
                final_content = msg.content
                status_container.update(label="✅ Response Ready", state="complete", expanded=False)
                st.markdown(final_content)
                st.session_state["messages"].append({"role": "assistant", "content": final_content})
                
                if st.session_state["current_chat_id"] is not None:
                     st.session_state["chat_history"][st.session_state["current_chat_id"]]["messages"] = st.session_state["messages"]
                break