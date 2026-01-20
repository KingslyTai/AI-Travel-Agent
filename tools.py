import json
import streamlit as st
from serpapi import GoogleSearch
import folium
import config
from utils import create_word_doc
from openai import OpenAI  # 🟢 [新增] 引入 OpenAI 库用于分析
from folium.plugins import AntPath, BeautifyIcon # 🟢 [新增] 引入高级地图插件

# 🟢 [新增] 初始化 DeepSeek Client (专用于 tools 内部分析)
try:
    client = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
except Exception as e:
    client = None
    print(f"Tools Client Init Error: {e}")

# ==========================================
# 🟢 核心修复: 带兜底的图片获取器
# ==========================================
def fetch_google_image(query):
    """
    Plan A: 去 Google Images 搜图 (只取 thumbnail 防止防盗链)
    """
    return None

    # 👇 你的原始代码都保留在这里 👇
    print(f"[后台] 正在尝试搜图: {query}...")
    params = {
        "engine": "google_images",
        "q": query,
        "api_key": config.SERPAPI_API_KEY,
        "num": 1
    }
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        if "images_results" in results and len(results["images_results"]) > 0:
            return results["images_results"][0].get("thumbnail")
    except Exception as e:
        print(f"[后台] 搜图失败: {e}")
        pass
    return None

def format_image_markdown(title, img_url):
    """
    格式化为 Markdown 图片。
    """
    if img_url:
        # 前后加换行，确保图片独占一行
        return f"\n\n![{title}]({img_url})\n\n"
    return ""

# ==========================================
# 工具函数 (排版已优化)
# ==========================================

# 1. 机票搜索 (保持不变)
def search_flights(origin, destination, date, return_date):
    st.toast(f"✈️ Checking Flights: {origin}->{destination} ({date})") 
    print(f"[后台] 查机票 {origin}-{destination} ({date})")
    params = {"engine": "google_flights", "departure_id": origin, "arrival_id": destination, "outbound_date": date, "return_date": return_date, "currency": "MYR", "hl": "en", "api_key": config.SERPAPI_API_KEY, "type": "1"}
    try:
        res = GoogleSearch(params).get_dict()
        if "best_flights" not in res: return f"RESULT: No specific flights found for {date}."
        f = res['best_flights'][0]
        return json.dumps({"date": date, "airline": f['flights'][0]['airline'], "price_per_adult": f['price'], "duration": f['total_duration']})
    except: return f"Error searching flights for {date}"

# 2. 酒店搜索 (🟢 优化排版：标题 -> 图片 -> 价格)
def search_hotels(city, check_in_date, check_out_date, adults):
    st.toast(f"🏨 Checking Hotels: {city}")
    search_type = "Vacation Rentals" if adults > 2 else "Hotels"
    params = {"engine": "google_hotels", "q": f"{city} {search_type}", "check_in_date": check_in_date, "check_out_date": check_out_date, "adults": adults, "currency": "MYR", "hl": "en", "gl": "my", "api_key": config.SERPAPI_API_KEY}
    try:
        res = GoogleSearch(params).get_dict()
        hotels = []
        if "properties" in res:
            for h in res["properties"][:3]:
                name = h.get("name")
                price = h.get("rate_per_night", {}).get("lowest", "N/A")
                
                # 🟡 尝试 1: 精准搜
                safe_img = fetch_google_image(f"{name} {city} hotel building")
                # 🟡 尝试 2: 兜底搜
                if not safe_img:
                    safe_img = fetch_google_image(f"{name} {city}")

                img_md = format_image_markdown(name, safe_img)
                
                # 🟢 [修改] 移除了 system_instruction，只保留干净的内容
                item_str = f"### 🏨 {name}\n{img_md}- **Price:** {price}"
                hotels.append(item_str)
                
        # 使用分割线连接，更清晰
        return "\n\n---\n\n".join(hotels) if hotels else "No hotels found"
    except Exception as e:
        print(f"Error: {e}") 
        return "Error searching hotels"

# 3. 景点搜索 (🟢 优化排版：标题 -> 图片 -> 评分)
def search_attractions(city, keyword=None):
    st.toast(f"🎡 Checking Sights: {city}")
    q = f"top sights in {city}" if not keyword else f"best {keyword} in {city}"
    params = {"engine": "google_maps", "q": q, "type": "search", "hl": "en", "api_key": config.SERPAPI_API_KEY}
    try:
        res = GoogleSearch(params).get_dict()
        results = []
        # 保持你想要的 10 个结果
        for r in res.get("local_results", [])[:10]:
            title = r.get('title', 'Unknown')
            rating = r.get('rating', 'N/A')
            
            # 双重保险找图
            original_thumb = r.get("thumbnail")
            high_res_img = fetch_google_image(f"{title} {city} scenery")
            final_img = high_res_img if high_res_img else original_thumb
            
            img_md = format_image_markdown(title, final_img)

            # 🟢 [修改] 移除了 system_instruction，只保留干净的内容
            item_str = f"### 🎡 {title}\n{img_md}- **Rating:** {rating}⭐"
            results.append(item_str)
            
        return "\n\n---\n\n".join(results)
    except: return "Error searching attractions"

# 4. 美食搜索 (保持不变，因为之前已经优化过 Header Image 了)
def search_restaurants(city, food_type):
    st.toast(f"🍜 Checking Food: {food_type} in {city}")
    universal_food_image = fetch_google_image(f"{food_type} {city} close up food")
    params = {"engine": "google_maps", "q": f"best {food_type} in {city}", "type": "search", "hl": "en", "api_key": config.SERPAPI_API_KEY}
    try:
        res = GoogleSearch(params).get_dict()
        results = []
        if universal_food_image:
            header_image = format_image_markdown(f"{food_type} Image", universal_food_image)
            # 🟢 [修改] 移除了 system_note，只保留干净的内容
            intro = f"### 🍽️ {food_type} in {city}\n{header_image}\n**Recommended Places:**\n"
            results.append(intro)
        else:
            results.append(f"### 🍽️ {food_type} in {city}\n**Recommended Places:**\n")
        
        for r in res.get("local_results", [])[:3]: 
            title = r.get('title')
            rating = r.get('rating', 'N/A')
            address = r.get('address', '')
            results.append(f"- **{title}** ({rating}⭐)\n  📍 {address}")
        return "\n".join(results)
    except: return "Error searching food"

# 5. 通用搜索 (保持不变)
def search_general_web(query):
    st.toast(f"🧠 Brain: Googling '{query}'...")
    params = {"engine": "google", "q": query, "hl": "en", "gl": "my", "api_key": config.SERPAPI_API_KEY}
    try:
        res = GoogleSearch(params).get_dict()
        snippets = [f"- {r.get('title')}: {r.get('snippet')}" for r in res.get("organic_results", [])[:3]]
        return "\n".join(snippets) if snippets else "No web results found."
    except: return "Web search error."

# --- 辅助函数：获取经纬度 (🟢 全面升级版: 列表+详情页双重检测) ---
def get_coordinates(location):
    print(f"🔍 Searching coordinates for: {location}")
    params = {"engine": "google_maps", "q": location, "type": "search", "api_key": config.SERPAPI_API_KEY}
    try:
        res = GoogleSearch(params).get_dict()
        
        # 🟢 情况 1: Google 返回了一个列表 (local_results)
        if "local_results" in res and res["local_results"]:
            gps = res["local_results"][0].get("gps_coordinates", {})
            return gps.get("latitude"), gps.get("longitude"), res["local_results"][0].get("title", location)
            
        # 🟢 情况 2: Google 直接返回了详情页 (place_results) -> 这就是你缺失的部分！
        if "place_results" in res:
            gps = res["place_results"].get("gps_coordinates", {})
            title = res["place_results"].get("title", location)
            return gps.get("latitude"), gps.get("longitude"), title
            
    except Exception as e:
        print(f"⚠️ Coord Error for {location}: {e}")
        pass
    return None, None, location

# 2. 交通查询
def get_directions(start_lat, start_lng, end_lat, end_lng):
    start = f"{start_lat},{start_lng}"
    end = f"{end_lat},{end_lng}"
    results = {
        "0": {"icon": "🚗", "text": "驾车", "time": "N/A", "details": ""},
        "3": {"icon": "🚇", "text": "公交", "time": "N/A", "details": ""},
        "2": {"icon": "🚶", "text": "步行", "time": "N/A", "details": ""}
    }
    for mode_code, info in results.items():
        params = {"engine": "google_maps_directions", "start_coords": start, "end_coords": end, "travel_mode": mode_code, "api_key": config.SERPAPI_API_KEY}
        try:
            res = GoogleSearch(params).get_dict()
            if "directions" in res and res["directions"]:
                route = res["directions"][0]
                results[mode_code]["time"] = route.get("formatted_duration", "N/A")
                if mode_code == "3" and "legs" in route:
                    steps = route["legs"][0].get("steps", [])
                    transit_segs = [s["transit_details"]["line"]["short_name"] for s in steps if s.get("travel_mode") == "TRANSIT" and "transit_details" in s]
                    if transit_segs: results[mode_code]["details"] = f" ➤ [{' > '.join(transit_segs)}]"
        except: pass
    line1 = f"🚗 **驾车**: {results['0']['time']}" if results["0"]["time"] != "N/A" else "🚗 驾车: 无法到达"
    transit_str = f"🚇 **公交**: {results['3']['time']}{results['3']['details']}" if results["3"]["time"] != "N/A" else "🚇 公交: N/A"
    walk_str = f"🚶 **步行**: {results['2']['time']}" if results["2"]["time"] != "N/A" else "🚶 步行: N/A"
    
    # 🟢 [修复] 定义 line2，修复 NameError
    line2 = f"{transit_str} | {walk_str}"
    
    return f"{line1}\n\n{line2}"

def generate_map_with_traffic(locations_list):
    if len(locations_list) < 1: return "Need at least 1 location."
    st.toast(f"🗺️ Visualizing Route: {', '.join(locations_list)}...")
    
    # 1. 获取坐标
    coords = []
    for loc in locations_list:
        lat, lng, name = get_coordinates(loc)
        if lat and lng: 
            coords.append([lat, lng, name])
        else:
            # 🟢 [新增] 如果找不到，在界面上弹窗警告
            st.warning(f"⚠️ 无法找到地点: '{loc}'，已自动跳过。")
            print(f"❌ Failed to find: {loc}")
    
    if not coords: return "Could not find valid coordinates for any location."
    if len(coords) < 2: 
        st.warning("⚠️ 只找到了 1 个有效地点，无法绘制路线。请尝试提供更准确的地点名称。")

    # 2. 创建地图中心
    m = folium.Map(location=[coords[0][0], coords[0][1]], zoom_start=13)

    # 3. 绘制路线和标记
    route_points = [] # 只存纯经纬度用于画线
    traffic_info = []

    for i in range(len(coords)):
        lat, lng, name = coords[i]
        route_points.append([lat, lng])
        
        # 🟢 [升级] 智能图标样式
        # 起点：绿色 Play 图标
        # 终点：红色 Flag 图标
        # 中间：蓝色数字图标
        if i == 0:
            icon_color = 'green'
            icon_shape = 'play'
            marker_html = f'<div style="font-size: 12pt; color: white; text-align: center;">🚀</div>'
        elif i == len(coords) - 1:
            icon_color = 'red'
            icon_shape = 'flag'
            marker_html = f'<div style="font-size: 12pt; color: white; text-align: center;">🏁</div>'
        else:
            icon_color = 'blue'
            icon_shape = 'number'
            marker_html = f'<div style="font-size: 12pt; color: white; text-align: center; font-weight: bold;">{i+1}</div>'

        # 🟢 [升级] 使用自定义 HTML 图标 (类似你参考图里的圆点)
        icon = folium.DivIcon(
            icon_size=(30, 30),
            icon_anchor=(15, 15),
            html=f"""
                <div style="
                    background-color: {icon_color}; 
                    width: 30px; 
                    height: 30px; 
                    border-radius: 50%; 
                    border: 2px solid white; 
                    box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                ">
                {marker_html}
                </div>
            """
        )

        # 添加标记
        folium.Marker(
            [lat, lng], 
            popup=f"<b>{i+1}. {name}</b>", 
            tooltip=f"{i+1}. {name}", # 鼠标悬停显示名字
            icon=icon
        ).add_to(m)

        # 4. 计算路段信息 (保持原有逻辑)
        if i < len(coords) - 1:
            next_lat, next_lng, next_name = coords[i+1]
            travel_str = get_directions(lat, lng, next_lat, next_lng)
            traffic_info.append(f"🚩 **{name} ➡️ {next_name}**")
            traffic_info.append(travel_str)

    # 🟢 [核心升级] 蚂蚁行军路线 (AntPath)
    # 这会在地图上画出一条流动的虚线，指示方向，非常有科技感
    AntPath(
        locations=route_points,
        dash_array=[10, 20],
        delay=1000,
        color='#FF005E', # 类似你参考图的粉红色
        pulse_color='#FFFFFF',
        weight=5,
        opacity=0.8
    ).add_to(m)

    # 保存数据
    st.session_state["map_data"] = m
    st.session_state["traffic_data"] = "\n\n".join(traffic_info)
    return "Map Generated with Animated Route!"

# 👇 保存函数 (保持不变)
def save_itinerary(content):
    doc_buffer = create_word_doc(content)
    st.session_state["download_buffer"] = doc_buffer
    if st.session_state["current_chat_id"] is not None:
        chat_id = st.session_state["current_chat_id"]
        if 0 <= chat_id < len(st.session_state["chat_history"]):
            st.session_state["chat_history"][chat_id]["itinerary_content"] = content
    try:
        with open("My_Trip_Plan.txt", "w", encoding="utf-8") as f: f.write(content)
    except: pass
    return "✅ Itinerary saved! Check the sidebar to download."

# ==========================================
# 🟢 [新增] AI 自动分析偏好
# ==========================================
def analyze_preferences_from_chat(messages):
    """
    分析聊天记录，提取用户的潜在偏好标签
    """
    if not client: return []
    if not messages or len(messages) < 2:
        return []

    # 把聊天记录压缩成一段文本
    conversation_text = ""
    for msg in messages:
        # 兼容 dict 和 object
        if isinstance(msg, dict):
            role = msg.get("role", "")
            content = msg.get("content", "")
        else:
            role = getattr(msg, "role", "")
            content = getattr(msg, "content", "")
            
        # 只看用户的发言和 AI 的核心建议
        if role in ["user", "assistant"] and content:
            conversation_text += f"{role}: {content}\n"

    # 预定义的标签池
    valid_tags = ["🍱 美食 (Foodie)", "💆‍♂️ 放松 (Relax)", "🌲 大自然 (Nature)", 
                  "🛍️ 购物 (Shopping)", "🏛️ 历史 (History)", "🎒 穷游 (Budget)", 
                  "💎 奢华 (Luxury)", "👨‍👩‍👧‍👦 亲子 (Family)", "📸 拍照打卡 (Insta-worthy)"]
    
    tags_str = ", ".join(valid_tags)

    prompt = f"""
    Analyze the following travel conversation. 
    Identify if the USER demonstrates strong interest in any of these specific categories: {tags_str}.
    
    Rules:
    1. Only select tags that are STRONGLY implied by the user's questions or choices.
    2. If the user asks for cheap food, select "🎒 穷游 (Budget)" and "🍱 美食 (Foodie)".
    3. If the user mentions kids, select "👨‍👩‍👧‍👦 亲子 (Family)".
    4. Return ONLY a JSON list of strings. Example: ["🍱 美食 (Foodie)", "🎒 穷游 (Budget)"]
    5. If no strong preference is found, return [].
    
    Conversation:
    {conversation_text[-2000:]} 
    """

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        content = response.choices[0].message.content
        
        # 清洗数据
        if "```" in content:
            content = content.replace("```json", "").replace("```", "")
        
        extracted_tags = json.loads(content)
        return extracted_tags if isinstance(extracted_tags, list) else []
    except Exception as e:
        print(f"Error analyzing chat: {e}")
        return []

# 工具列表 (Tools List - 保持不变)
tools_list = [
    {"type": "function", "function": {"name": "search_flights", "description": "Search flights", "parameters": {"type": "object", "properties": {"origin": {"type": "string"}, "destination": {"type": "string"}, "date": {"type": "string"}, "return_date": {"type": "string"}}, "required": ["origin", "destination", "date", "return_date"]}}},
    {"type": "function", "function": {"name": "search_hotels", "description": "Search hotels", "parameters": {"type": "object", "properties": {"city": {"type": "string"}, "check_in_date": {"type": "string"}, "check_out_date": {"type": "string"}, "adults": {"type": "integer"}}, "required": ["city", "check_in_date", "check_out_date", "adults"]}}},
    {"type": "function", "function": {"name": "search_attractions", "description": "Search attractions", "parameters": {"type": "object", "properties": {"city": {"type": "string"}, "keyword": {"type": "string"}}, "required": ["city"]}}},
    {"type": "function", "function": {"name": "search_restaurants", "description": "Search for best restaurants serving a specific food type (e.g. 'Nasi Lemak', 'Sushi').", "parameters": {"type": "object", "properties": {"city": {"type": "string"}, "food_type": {"type": "string"}}, "required": ["city", "food_type"]}}},
    {"type": "function", "function": {"name": "search_general_web", "description": "Search Google for general info", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "save_itinerary", "description": "Generate Word document", "parameters": {"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]}}},
    # 🟢 [核心修改] 修改了 description，强制要求 AI 必须带上 City/Country，防止定位跑偏！
    {"type": "function", "function": {"name": "generate_map_with_traffic", "description": "Generate a map. ⚠️ ONLY use this if user explicitly asks for 'map'. IMPORTANT: You MUST append the City/Country to EACH location name in 'locations_list' to ensure accurate geocoding (e.g. use 'Ya Kun Kaya Toast, Singapore' instead of just 'Ya Kun Kaya Toast').", "parameters": {"type": "object", "properties": {"locations_list": {"type": "array", "items": {"type": "string"}}}, "required": ["locations_list"]}}}
]