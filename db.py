import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st

# 1. 连接 Firebase
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate("firebase_key.json") 
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"🔥 Firebase 连接失败: {e}")

db = firestore.client()

# ==========================================
# 🟢 辅助工具：数据清洗
# ==========================================
def serialize_messages(messages):
    """
    把 OpenAI 的对象转换成纯字典
    """
    clean_msgs = []
    for msg in messages:
        if isinstance(msg, dict):
            clean_msgs.append(msg)
        elif hasattr(msg, 'model_dump'):
            clean_msgs.append(msg.model_dump())
        elif hasattr(msg, 'to_dict'):
            clean_msgs.append(msg.to_dict())
        else:
            clean_msgs.append({
                "role": getattr(msg, "role", "assistant"), 
                "content": str(getattr(msg, "content", ""))
            })
    return clean_msgs

# ==========================================
# 🟢 用户管理
# ==========================================

def create_user(email, password, preferences):
    users_ref = db.collection("users")
    doc = users_ref.document(email).get()
    
    if doc.exists:
        return False, "❌ 该邮箱已被注册！请直接登录。"
    
    users_ref.document(email).set({
        "email": email,
        "password": password,
        "preferences": preferences,
        "created_at": firestore.SERVER_TIMESTAMP
    })
    return True, "✅ 注册成功！已自动登录。"

def authenticate_user(email, password):
    doc_ref = db.collection("users").document(email)
    doc = doc_ref.get()
    
    if not doc.exists:
        return None, "❌ 账号不存在，请先注册。"
    
    user_data = doc.to_dict()
    if user_data.get("password") == password:
        return user_data, "✅ 登录成功！"
    else:
        return None, "❌ 密码错误，请重试。"

def update_preferences(email, new_preferences):
    db.collection("users").document(email).update({
        "preferences": new_preferences
    })

# ==========================================
# 🟢 核心升级：改用 Subcollection (子集合) 存储
# ==========================================

def save_chat_history(email, history):
    """
    将聊天记录列表拆分，保存到 users/{email}/chats/ 子集合中
    """
    try:
        # 1. 获取 'chats' 子集合的引用
        chats_ref = db.collection("users").document(email).collection("chats")
        
        # 2. 批量写入 (Batch Write) 以提高性能
        batch = db.batch()
        
        # 3. 先把旧的文档标记为删除 (为了保持跟前端列表完全同步，防止删了的对话还在)
        # 注意：对于超大量数据，全删全写效率不高，但在 MVP 阶段这是保证数据一致性最稳妥的方法
        old_docs = chats_ref.list_documents()
        for doc in old_docs:
            batch.delete(doc)
            
        # 4. 遍历当前的 history 列表，一个个存进去
        for i, chat in enumerate(history):
            # 使用 chat_0, chat_1 作为 ID，确保顺序
            doc_ref = chats_ref.document(f"chat_{i}")
            
            clean_data = {
                "title": chat.get("title", "New Chat"),
                "itinerary_content": chat.get("itinerary_content"),
                "messages": serialize_messages(chat["messages"]),
                "order_index": i, # 记录顺序
                "updated_at": firestore.SERVER_TIMESTAMP
            }
            batch.set(doc_ref, clean_data)
        
        # 5. 提交所有更改
        batch.commit()
        
        # 顺便把旧的 'chat_history' 大字段删掉，节省空间 (清理旧数据)
        db.collection("users").document(email).update({
            "chat_history": firestore.DELETE_FIELD
        })
        
        print(f"✅ [DB] Saved {len(history)} chats to subcollection for {email}")
        return True
    except Exception as e:
        print(f"❌ [DB] Error saving history: {e}")
        return False

def load_chat_history(email):
    """
    从 users/{email}/chats/ 子集合读取聊天记录，并组装成列表
    """
    try:
        # 1. 获取 'chats' 子集合
        chats_ref = db.collection("users").document(email).collection("chats")
        
        # 2. 获取所有文档
        docs = chats_ref.stream()
        
        # 3. 组装成列表
        loaded_history = []
        for doc in docs:
            data = doc.to_dict()
            # 兼容旧逻辑：确保有 messages 字段
            if "messages" not in data: continue
            
            # 为了确保顺序，我们可以把 ID (chat_0, chat_1) 取出来排序
            # 但这里我们直接用存进去的 index 排序更稳
            chat_obj = {
                "title": data.get("title", "New Chat"),
                "itinerary_content": data.get("itinerary_content"),
                "messages": data.get("messages", []),
                "order_index": data.get("order_index", 0)
            }
            loaded_history.append(chat_obj)
            
        # 4. 按 order_index 排序，确保列表顺序不乱
        loaded_history.sort(key=lambda x: x["order_index"])
        
        # 5. 如果子集合是空的，尝试读取一下旧格式 (为了兼容老用户数据)
        if not loaded_history:
            old_doc = db.collection("users").document(email).get()
            if old_doc.exists:
                old_data = old_doc.to_dict()
                if "chat_history" in old_data:
                    print("⚠️ [DB] Migrating from old format...")
                    return old_data["chat_history"]

        return loaded_history
    except Exception as e:
        print(f"Error loading history: {e}")
        return []

# ==========================================
# 🟢 [新增] 偏好学习功能：合并标签
# ==========================================
def merge_user_preferences(email, new_tags):
    """
    将 AI 新学到的标签合并到用户的现有标签中 (去重)
    """
    try:
        doc_ref = db.collection("users").document(email)
        doc = doc_ref.get()
        
        if doc.exists:
            current_prefs = doc.to_dict().get("preferences", [])
            # 使用集合 Set 进行合并去重，然后再转回列表
            updated_prefs = list(set(current_prefs + new_tags))
            
            doc_ref.update({
                "preferences": updated_prefs
            })
            return updated_prefs
        return []
    except Exception as e:
        print(f"Error merging preferences: {e}")
        return []