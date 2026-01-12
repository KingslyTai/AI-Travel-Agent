import json
import streamlit as st
from serpapi import GoogleSearch
import folium
# 引入其他模块
import config
from utils import create_word_doc

# ==========================================
# 工具函数 (完全保留逻辑)
# ==========================================

# 1. 机票搜索
def search_flights(origin, destination, date, return_date):
    st.toast(f"✈️ Checking Flights: {origin}->{destination} ({date})") 
    print(f"[后台] 查机票 {origin}-{destination} ({date})")
    params = {
        "engine": "google_flights", "departure_id": origin, "arrival_id": destination, 
        "outbound_date": date, "return_date": return_date, "currency": "MYR", "hl": "en", 
        "api_key": config.SERPAPI_API_KEY, "type": "1"
    }
    try:
        res = GoogleSearch(params).get_dict()
        if "best_flights" not in res: 
            return f"RESULT: No specific flights found for {date}. (HINT: Date might be too far ahead?)"
        f = res['best_flights'][0]
        return json.dumps({
            "date": date, "airline": f['flights'][0]['airline'], 
            "price_per_adult": f['price'], "duration": f['total_duration']
        })
    except: return f"Error searching flights for {date}"

# 2. 酒店搜索
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
                hotels.append(f"- {name} | Price: {price}")
        return "\n".join(hotels) if hotels else "No hotels found"
    except: return "Error searching hotels"

# 3. 景点搜索
def search_attractions(city, keyword=None):
    st.toast(f"🎡 Checking Sights: {city}")
    q = f"top sights in {city}" if not keyword else f"best {keyword} in {city}"
    params = {"engine": "google_maps", "q": q, "type": "search", "hl": "en", "api_key": config.SERPAPI_API_KEY}
    try:
        res = GoogleSearch(params).get_dict()
        results = []
        for r in res.get("local_results", [])[:5]:
            title = r.get('title', 'Unknown')
            rating = r.get('rating', 'N/A')
            results.append(f"- {title} ({rating}⭐)")
        return "\n".join(results)
    except: return "Error searching attractions"

# 4. 美食搜索
def search_restaurants(city, food_type="local food"):
    st.toast(f"🍜 Checking Food: {city}")
    params = {"engine": "google_maps", "q": f"best {food_type} in {city}", "type": "search", "hl": "en", "api_key": config.SERPAPI_API_KEY}
    try:
        res = GoogleSearch(params).get_dict()
        return "\n".join([f"- {r.get('title')} ({r.get('rating')}⭐)" for r in res.get("local_results", [])[:5]])
    except: return "Error searching food"

# 5. 通用搜索
def search_general_web(query):
    st.toast(f"🧠 Brain: Googling '{query}'...")
    params = {"engine": "google", "q": query, "hl": "en", "gl": "my", "api_key": config.SERPAPI_API_KEY}
    try:
        res = GoogleSearch(params).get_dict()
        snippets = [f"- {r.get('title')}: {r.get('snippet')}" for r in res.get("organic_results", [])[:3]]
        return "\n".join(snippets) if snippets else "No web results found."
    except: return "Web search error."

# --- 辅助函数：获取经纬度 ---
def get_coordinates(location):
    params = {"engine": "google_maps", "q": location, "type": "search", "api_key": config.SERPAPI_API_KEY}
    try:
        res = GoogleSearch(params).get_dict()
        if "local_results" in res and res["local_results"]:
            gps = res["local_results"][0].get("gps_coordinates", {})
            return gps.get("latitude"), gps.get("longitude"), res["local_results"][0].get("title", location)
    except: pass
    return None, None, location

# 2. 核心升级：分组显示 (驾车独立，公交+走路合并)
def get_directions(start_lat, start_lng, end_lat, end_lng):
    start = f"{start_lat},{start_lng}"
    end = f"{end_lat},{end_lng}"
    
    results = {
        "0": {"icon": "🚗", "text": "驾车", "time": "N/A", "details": ""},
        "3": {"icon": "🚇", "text": "公交", "time": "N/A", "details": ""},
        "2": {"icon": "🚶", "text": "步行", "time": "N/A", "details": ""}
    }
    
    for mode_code, info in results.items():
        params = {
            "engine": "google_maps_directions",
            "start_coords": start,
            "end_coords": end,
            "travel_mode": mode_code, 
            "api_key": config.SERPAPI_API_KEY
        }
        try:
            res = GoogleSearch(params).get_dict()
            if "directions" in res and res["directions"]:
                route = res["directions"][0]
                duration = route.get("formatted_duration", "N/A")
                results[mode_code]["time"] = duration
                
                if mode_code == "3" and "legs" in route:
                    steps = route["legs"][0].get("steps", [])
                    transit_segments = []
                    for step in steps:
                        if step.get("travel_mode") == "TRANSIT" and "transit_details" in step:
                            td = step["transit_details"]
                            line_name = td.get("line", {}).get("short_name") or td.get("line", {}).get("name") or "Bus"
                            transit_segments.append(f"**{line_name}**") 
                    
                    if transit_segments:
                        results[mode_code]["details"] = f" ➤ [{' > '.join(transit_segments)}]"
        except: 
            pass 
            
    line1 = f"🚗 **驾车**: {results['0']['time']}" if results["0"]["time"] != "N/A" else "🚗 驾车: 无法到达"
    transit_str = f"🚇 **公交**: {results['3']['time']}{results['3']['details']}" if results["3"]["time"] != "N/A" else "🚇 公交: N/A"
    walk_str = f"🚶 **步行**: {results['2']['time']}" if results["2"]["time"] != "N/A" else "🚶 步行: N/A"
    
    line2 = f"{transit_str} &nbsp;&nbsp;|&nbsp;&nbsp; {walk_str}"
    return f"{line1}\n\n{line2}"

# 3. 地图生成
def generate_map_with_traffic(locations_list):
    if len(locations_list) < 1: return "Need at least 1 location."
    
    st.toast(f"🗺️ Calculating optimized routes for: {', '.join(locations_list)}...")
    
    coords = []
    for loc in locations_list:
        lat, lng, real_name = get_coordinates(loc)
        if lat and lng:
            coords.append((lat, lng, real_name))
            
    if not coords: return "Could not find coordinates."

    m = folium.Map(location=[coords[0][0], coords[0][1]], zoom_start=13)
    
    traffic_info = []
    
    for i in range(len(coords)):
        lat, lng, name = coords[i]
        
        folium.Marker(
            [lat, lng], 
            popup=name, 
            tooltip=f"{i+1}. {name}",
            icon=folium.Icon(color='red' if i==0 else 'blue', icon='info-sign')
        ).add_to(m)
        
        if i < len(coords) - 1:
            next_lat, next_lng, next_name = coords[i+1]
            travel_str = get_directions(lat, lng, next_lat, next_lng)
            traffic_info.append(f"🚩 **{name} ➡️ {next_name}**")
            traffic_info.append(travel_str) 
            folium.PolyLine(locations=[[lat, lng], [next_lat, next_lng]], color="blue", weight=4, opacity=0.6, dash_array='10').add_to(m)

    st.session_state["map_data"] = m
    st.session_state["traffic_data"] = "\n\n".join(traffic_info)
    
    return "Map Generated!"

# 👇 保存函数
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

# 工具列表 (Tools List)
tools_list = [
    {"type": "function", "function": {"name": "search_flights", "description": "Search flights", "parameters": {"type": "object", "properties": {"origin": {"type": "string"}, "destination": {"type": "string"}, "date": {"type": "string"}, "return_date": {"type": "string"}}, "required": ["origin", "destination", "date", "return_date"]}}},
    {"type": "function", "function": {"name": "search_hotels", "description": "Search hotels", "parameters": {"type": "object", "properties": {"city": {"type": "string"}, "check_in_date": {"type": "string"}, "check_out_date": {"type": "string"}, "adults": {"type": "integer"}}, "required": ["city", "check_in_date", "check_out_date", "adults"]}}},
    {"type": "function", "function": {"name": "search_attractions", "description": "Search attractions", "parameters": {"type": "object", "properties": {"city": {"type": "string"}, "keyword": {"type": "string"}}, "required": ["city"]}}},
    {"type": "function", "function": {"name": "search_restaurants", "description": "Search restaurants", "parameters": {"type": "object", "properties": {"city": {"type": "string"}, "food_type": {"type": "string"}}, "required": ["city"]}}},
    {"type": "function", "function": {"name": "search_general_web", "description": "Search Google for general info", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "save_itinerary", "description": "Generate Word document", "parameters": {"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]}}},
    {"type": "function", "function": {"name": "generate_map_with_traffic", "description": "Generate a map. ⚠️ ONLY use this if user explicitly asks for 'map' or 'route visualization'. Do not use by default.", "parameters": {"type": "object", "properties": {"locations_list": {"type": "array", "items": {"type": "string"}}}, "required": ["locations_list"]}}}
]