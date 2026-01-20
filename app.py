import streamlit as st
import json
from openai import OpenAI
from streamlit_folium import st_folium
import streamlit.components.v1 as components 

# 🟢 导入模块
import config
import db
import tools
import utils

# ==========================================
# 1. 页面基础设置
# ==========================================
st.set_page_config(page_title="AI 智能旅行管家 (Pro版)", page_icon="🌍", layout="wide")

try:
    client = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
except Exception as e:
    st.error("API Key 配置有误，请检查代码。")
    st.stop()

# ==========================================
# 2. 状态管理
# ==========================================
if "user_info" not in st.session_state: st.session_state["user_info"] = None
if "current_prefs" not in st.session_state: st.session_state["current_prefs"] = []

# 初始化 sidebar_selector 防止警告
if "sidebar_selector" not in st.session_state:
    st.session_state["sidebar_selector"] = st.session_state["current_prefs"]

# 初始化人数 (默认值)
initial_counts = {"count_Adults": 1, "count_Kids": 0, "count_Baby": 0, "count_Elder": 0, "count_OKU": 0}
for k, v in initial_counts.items():
    if k not in st.session_state:
        st.session_state[k] = v

if "chat_history" not in st.session_state: st.session_state["chat_history"] = []
if "current_chat_id" not in st.session_state: st.session_state["current_chat_id"] = None
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "system", "content": config.SYSTEM_PROMPT},
        {"role": "assistant", "content": "Hello! I am your AI Agent. Select your travel style on the left!"}
    ]
if "download_buffer" not in st.session_state: st.session_state["download_buffer"] = None
if "map_data" not in st.session_state: st.session_state["map_data"] = None
if "traffic_data" not in st.session_state: st.session_state["traffic_data"] = None
if "saved_map_html" not in st.session_state: st.session_state["saved_map_html"] = None 

# ==========================================
# 🟢 辅助函数区域
# ==========================================

# 1. 同步历史记录
def sync_history_to_db():
    if st.session_state["user_info"]:
        email = st.session_state["user_info"]["email"]
        history = st.session_state["chat_history"]
        db.save_chat_history(email, history)

# 2. 删除历史记录
def delete_chat_history(index):
    if 0 <= index < len(st.session_state["chat_history"]):
        st.session_state["chat_history"].pop(index)
        if st.session_state["current_chat_id"] == index:
            st.session_state["current_chat_id"] = None
            st.session_state["messages"] = [{"role": "system", "content": config.SYSTEM_PROMPT},{"role": "assistant", "content": "Chat deleted."}]
            st.session_state["download_buffer"] = None
            st.session_state["map_data"] = None
            st.session_state["traffic_data"] = None
            st.session_state["saved_map_html"] = None 
        elif st.session_state["current_chat_id"] is not None and st.session_state["current_chat_id"] > index:
            st.session_state["current_chat_id"] -= 1
        sync_history_to_db()

# 🟢 New Chat 的逻辑
def handle_new_chat():
    # A. 尝试保存当前对话
    if len(st.session_state["messages"]) > 2:
        user_first_msg = "New Chat"
        for msg in st.session_state["messages"]:
            if isinstance(msg, dict) and msg["role"] == "user":
                user_first_msg = msg.get("content", "")[:15] + "..."
                break
            elif not isinstance(msg, dict) and msg.role == "user":
                user_first_msg = msg.content[:15] + "..."
                break     
        
        current_map_html = None
        if st.session_state["map_data"]:
            current_map_html = st.session_state["map_data"].get_root().render()
        elif st.session_state["saved_map_html"]:
            current_map_html = st.session_state["saved_map_html"]

        if st.session_state["user_info"]:
            learned_tags = tools.analyze_preferences_from_chat(st.session_state["messages"])
            if learned_tags:
                email = st.session_state["user_info"]["email"]
                new_all_tags = db.merge_user_preferences(email, learned_tags)
                if new_all_tags:
                    st.session_state["user_info"]["preferences"] = new_all_tags
                    st.session_state["current_prefs"] = new_all_tags
                    st.session_state["sidebar_selector"] = new_all_tags

        history_item = {
            "title": user_first_msg, 
            "messages": st.session_state["messages"], 
            "itinerary_content": None,
            "map_html": current_map_html if current_map_html else None,  # 确保有值
            "traffic_data": st.session_state["traffic_data"] if st.session_state["traffic_data"] else None
        }

        if st.session_state["current_chat_id"] is None:
            st.session_state["chat_history"].insert(0, history_item)
        
        sync_history_to_db()
    
    # B. 重置对话状态
    st.session_state["messages"] = [{"role": "system", "content": config.SYSTEM_PROMPT}, {"role": "assistant", "content": "Hello! Where are we going today?"}]
    st.session_state["current_chat_id"] = None
    st.session_state["download_buffer"] = None
    st.session_state["map_data"] = None 
    st.session_state["traffic_data"] = None 
    st.session_state["saved_map_html"] = None 

# ==========================================
# 🟢 核心逻辑：UI 辅助函数
# ==========================================
def render_counter(label, session_key, min_val=0):
    c1, c2, c3, c4 = st.columns([2.5, 1, 0.8, 1])
    with c1: st.write(f"**{label}**") 
    with c2:
        if st.button("➖", key=f"dec_{session_key}"):
            if st.session_state[session_key] > min_val:
                st.session_state[session_key] -= 1
                st.rerun() 
    with c3: st.markdown(f"<div style='text-align:center; padding-top:5px; font-weight:bold;'>{st.session_state[session_key]}</div>", unsafe_allow_html=True)
    with c4:
        if st.button("➕", key=f"inc_{session_key}"):
            st.session_state[session_key] += 1
            st.rerun() 

def auto_sync_style():
    new_prefs = st.session_state.get("sidebar_selector", [])
    st.session_state["current_prefs"] = new_prefs
    if st.session_state["user_info"]:
        email = st.session_state["user_info"]["email"]
        old_prefs = st.session_state["user_info"].get("preferences", [])
        if set(new_prefs) != set(old_prefs):
            db.update_preferences(email, new_prefs)
            st.session_state["user_info"]["preferences"] = new_prefs

# ==========================================
# 🟢 登录弹窗 (修复了 Logout 逻辑)
# ==========================================
@st.dialog("🔐 账户中心 (Account)")
def login_dialog():
    if st.session_state["user_info"]:
        st.success(f"当前已登录: {st.session_state['user_info']['email']}")
        
        if st.button("🚪 退出登录 (Logout)", type="primary", use_container_width=True):
            sync_history_to_db()
            st.session_state["user_info"] = None
            st.session_state["current_prefs"] = []
            st.session_state["sidebar_selector"] = [] 
            st.session_state["chat_history"] = []
            st.session_state["messages"] = [{"role": "system", "content": config.SYSTEM_PROMPT}, {"role": "assistant", "content": "Hello! I am your AI Agent. Select your travel style on the left!"}]
            st.session_state["current_chat_id"] = None
            
            # 🟢 [关键修复] 登出时必须手动清除地图数据，否则它们会残留在 Session 里
            st.session_state["map_data"] = None
            st.session_state["traffic_data"] = None
            st.session_state["saved_map_html"] = None
            st.session_state["download_buffer"] = None
            
            for k in initial_counts.keys(): st.session_state[k] = initial_counts[k]
            st.rerun()
    else:
        tab1, tab2 = st.tabs(["Login", "Register"])
        with tab1: 
            email_in = st.text_input("Email", key="d_l_email")
            pass_in = st.text_input("Password", type="password", key="d_l_pass")
            if st.button("登录 (Sign In)", use_container_width=True):
                user, msg = db.authenticate_user(email_in, pass_in)
                if user:
                    st.session_state["user_info"] = user
                    prefs = user.get("preferences", [])
                    st.session_state["current_prefs"] = prefs
                    st.session_state["sidebar_selector"] = prefs 
                    try:
                        history = db.load_chat_history(user["email"])
                        st.session_state["chat_history"] = history
                    except: pass
                    st.session_state["messages"] = [{"role": "system", "content": config.SYSTEM_PROMPT}, {"role": "assistant", "content": "Hello! Welcome back! Where are we going today?"}]
                    st.session_state["current_chat_id"] = None
                    st.session_state["download_buffer"] = None
                    st.session_state["map_data"] = None 
                    st.session_state["traffic_data"] = None 
                    st.session_state["saved_map_html"] = None 
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        with tab2:
            new_email = st.text_input("New Email", key="d_r_email")
            new_pass = st.text_input("New Password", type="password", key="d_r_pass")
            travel_tags = ["🍱 美食 (Foodie)", "💆‍♂️ 放松 (Relax)", "🌲 大自然 (Nature)", "🛍️ 购物 (Shopping)", "🏛️ 历史 (History)", "🎒 穷游 (Budget)", "💎 奢华 (Luxury)", "👨‍👩‍👧‍👦 亲子 (Family)", "📸 拍照打卡 (Insta-worthy)"]
            reg_prefs = st.multiselect("Select Tags", travel_tags, default=st.session_state.get("current_prefs", []))
            if st.button("注册 (Create Account)", use_container_width=True):
                if new_email and new_pass:
                    success, msg = db.create_user(new_email, new_pass, reg_prefs)
                    if success: st.success("✅ 注册成功！请切换到 Login 页面进行登录。")
                    else: st.error(msg)
                else: st.warning("Please fill all fields.")

# ==========================================
# 🟢 主界面
# ==========================================
st.title("🧠 My AI Travel Agent")
st.caption("Your personalized trip planner powered by AI")
st.markdown("---")

# ==========================================
# 🔴 Sidebar UI
# ==========================================
with st.sidebar:
    if st.session_state["user_info"]:
        user_name = st.session_state["user_info"]["email"].split("@")[0]
        if st.button(f"👤 {user_name} (Account)", use_container_width=True):
            login_dialog()
    else:
        if st.button("🔐 Login / Register", type="primary", use_container_width=True):
            login_dialog()
    
    st.markdown("---") 
    st.subheader("🛠️ Trip Settings")
    
    travel_tags = ["🍱 美食 (Foodie)", "💆‍♂️ 放松 (Relax)", "🌲 大自然 (Nature)", "🛍️ 购物 (Shopping)", "🏛️ 历史 (History)", "🎒 穷游 (Budget)", "💎 奢华 (Luxury)", "👨‍👩‍👧‍👦 亲子 (Family)", "📸 拍照打卡 (Insta-worthy)"]
    st.multiselect("Style (风格)", travel_tags, key="sidebar_selector", on_change=auto_sync_style)
    
    st.markdown("#### 👥 Group Size")
    with st.container():
        render_counter("Adults", "count_Adults", min_val=1)
        render_counter("Kids (4-12)", "count_Kids")
        render_counter("Baby (0-3)", "count_Baby")
        render_counter("Elder (60+)", "count_Elder")
        render_counter("OKU (Disabled)", "count_OKU")

    st.markdown("---")
    
    st.button("➕ New Chat", use_container_width=True, type="primary", on_click=handle_new_chat)

    if st.session_state.get("download_buffer"):
        st.download_button("📥 Download .docx", data=st.session_state["download_buffer"], file_name="Trip_Plan.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="primary")

    if st.session_state["chat_history"]:
        st.caption("History")
        for i, chat in enumerate(st.session_state["chat_history"]):
            col1, col2 = st.columns([0.8, 0.2]) 
            with col1:
                if st.button(f"💬 {chat['title']}", key=f"h_{i}"):
                     st.session_state["messages"] = chat["messages"]
                     st.session_state["current_chat_id"] = i
                     
                     st.session_state["saved_map_html"] = chat.get("map_html") 
                     st.session_state["traffic_data"] = chat.get("traffic_data")
                     st.session_state["map_data"] = None 

                     saved_content = chat.get("itinerary_content")
                     st.session_state["download_buffer"] = utils.create_word_doc(saved_content) if saved_content else None
                     st.rerun()
            with col2:
                st.button("✖", key=f"d_{i}", on_click=delete_chat_history, args=(i,))

# ==========================================
# 🧠 记忆注入
# ==========================================
curr_style = st.session_state.get("current_prefs", [])
curr_group = {
    "Adults": st.session_state["count_Adults"],
    "Kids": st.session_state["count_Kids"],
    "Baby": st.session_state["count_Baby"],
    "Elder": st.session_state["count_Elder"],
    "OKU": st.session_state["count_OKU"]
}

is_group_set = (curr_group["Kids"]>0 or curr_group["Baby"]>0 or curr_group["Elder"]>0 or curr_group["OKU"]>0 or curr_group["Adults"]>1)

if curr_style or is_group_set:
    style_str = ", ".join(curr_style) if curr_style else "Not specified"
    group_str_list = [f"{k}: {v}" for k,v in curr_group.items() if v > 0]
    group_str = ", ".join(group_str_list)
    constraints = []
    if curr_group["OKU"] > 0: constraints.append("MUST be Wheelchair Accessible.")
    if curr_group["Elder"] > 0: constraints.append("Low physical intensity.")
    if curr_group["Baby"] > 0: constraints.append("Stroller friendly, nursing breaks.")
    if curr_group["Kids"] > 0: constraints.append("Include kids activities.")
    constraints_str = " ".join(constraints) if constraints else "None"

    memory_block = f"""
    \n\n[📋 USER CONTEXT (Updated Settings)]
    - Travel Style: {style_str}
    - Group Composition: {group_str}
    - SPECIAL CONSTRAINTS: {constraints_str}
    (INSTRUCTION: Use these constraints for the NEXT response. Do not reply to this system update.)
    """
    if st.session_state["messages"] and isinstance(st.session_state["messages"][0], dict) and st.session_state["messages"][0]["role"] == "system":
        st.session_state["messages"][0]["content"] = config.SYSTEM_PROMPT + memory_block

# ==========================================
# 3. 主界面内容
# ==========================================
for i, msg in enumerate(st.session_state["messages"]):
    if isinstance(msg, dict):
        role = msg["role"]
        content = msg.get("content")
    else:
        role = msg.role
        content = msg.content
    
    if role == "system": continue

    if st.session_state.get(f"editing_{i}", False):
        with st.chat_message(role):
            new_content = st.text_area("Edit your message:", value=content, key=f"edit_area_{i}")
            col1, col2 = st.columns([1, 5])
            if col1.button("Save & Regenerate", key=f"save_{i}"):
                if isinstance(st.session_state["messages"][i], dict):
                    st.session_state["messages"][i]["content"] = new_content
                else:
                    st.session_state["messages"][i].content = new_content
                st.session_state["messages"] = st.session_state["messages"][:i+1]
                st.session_state[f"editing_{i}"] = False
                st.session_state["map_data"] = None
                st.session_state["traffic_data"] = None
                st.session_state["saved_map_html"] = None 
                st.session_state["download_buffer"] = None
                st.rerun()
            if col2.button("Cancel", key=f"cancel_{i}"):
                st.session_state[f"editing_{i}"] = False
                st.rerun()
    else:
        if content:
            with st.chat_message(role):
                st.write(content)
                if role == "user":
                    if st.button("✏️ Edit", key=f"edit_btn_{i}", help="Edit this message"):
                        st.session_state[f"editing_{i}"] = True
                        st.rerun()

if st.session_state.get("map_data") or st.session_state.get("saved_map_html"):
    with st.container():
        st.markdown("### 🗺️ Route Map")
        if st.session_state.get("traffic_data"):
            with st.expander("🚗 Traffic Details", expanded=True): st.markdown(st.session_state["traffic_data"])
        
        if st.session_state.get("map_data"):
            try: st_folium(st.session_state["map_data"], width=700, height=400, returned_objects=[])
            except: pass
        elif st.session_state.get("saved_map_html"):
            components.html(st.session_state["saved_map_html"], height=400)

if prompt := st.chat_input("Plan my trip to..."):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    history_item = {"title": prompt[:15] + "...", "messages": st.session_state["messages"], "itinerary_content": None, "map_html": None, "traffic_data": None}
    
    if st.session_state["current_chat_id"] is None:
        st.session_state["chat_history"].insert(0, history_item)
        st.session_state["current_chat_id"] = 0
    else:
        if st.session_state["current_chat_id"] >= len(st.session_state["chat_history"]):
            st.session_state["chat_history"].insert(0, history_item)
            st.session_state["current_chat_id"] = 0
        else:
            st.session_state["chat_history"][st.session_state["current_chat_id"]]["messages"] = st.session_state["messages"]
    st.rerun()

if st.session_state["messages"]:
    last_msg = st.session_state["messages"][-1]
    last_role = last_msg["role"] if isinstance(last_msg, dict) else last_msg.role
    
    if last_role == "user":
        with st.chat_message("assistant"):
            status_container = st.status("🧠 Agent is thinking...", expanded=True)
            messages = st.session_state["messages"]
            while True:
                response = client.chat.completions.create(model="deepseek-chat", messages=messages, tools=tools.tools_list)
                msg = response.choices[0].message
                if msg.tool_calls:
                    messages.append(msg)
                    should_rerun = False 
                    for tool in msg.tool_calls:
                        fn, args = tool.function.name, json.loads(tool.function.arguments)
                        status_container.write(f"👉 Action: **{fn}**")
                        res = None
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
                            if st.session_state.get("map_data") and st.session_state["current_chat_id"] is not None:
                                html_str = st.session_state["map_data"].get_root().render()
                                if st.session_state["current_chat_id"] < len(st.session_state["chat_history"]):
                                    st.session_state["chat_history"][st.session_state["current_chat_id"]]["map_html"] = html_str
                                    st.session_state["chat_history"][st.session_state["current_chat_id"]]["traffic_data"] = st.session_state["traffic_data"]
                                    sync_history_to_db()

                        elif fn == "get_weather_forecast": res = tools.get_weather_forecast(args["city"]); status_container.write("🌤️ Checked Weather!")
                        
                        messages.append({"role": "tool", "tool_call_id": tool.id, "content": str(res)})
                    if should_rerun: st.rerun()
                else:
                    final_content = msg.content
                    status_container.update(label="✅ Response Ready", state="complete", expanded=False)
                    st.markdown(final_content)
                    st.session_state["messages"].append({"role": "assistant", "content": final_content})
                    if st.session_state["current_chat_id"] is not None: 
                        if st.session_state["current_chat_id"] < len(st.session_state["chat_history"]):
                            st.session_state["chat_history"][st.session_state["current_chat_id"]]["messages"] = st.session_state["messages"]
                    sync_history_to_db()
                    break