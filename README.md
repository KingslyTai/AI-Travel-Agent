# 🌍 Autonomous AI Travel Agent

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B)
![AI](https://img.shields.io/badge/AI-DeepSeek%20LLM-green)
![Architecture](https://img.shields.io/badge/Pattern-Function%20Calling-purple)

An intelligent, full-stack travel planning assistant powered by **DeepSeek LLM** and **Function Calling**. 

Unlike traditional chatbots, this agent possesses **autonomy**: it intelligently analyzes user intent, executes external tools (Maps, Flights, Hotels) in real-time, and orchestrates complex travel data into a visualized itinerary.

---

## 🚀 Key Capabilities

### 🧠 1. Autonomous Reasoning (Function Calling)
The core of this agent is its ability to "think" before acting. It uses **LLM Function Calling** to dynamically select the right tool for the job—whether it's searching for live flight data or calculating traffic routes—without hard-coded decision trees.

### 🗺️ 2. Dynamic Route Visualization
Instead of static text, the agent generates interactive maps using **Folium** and **AntPath**. It visualizes the entire day's itinerary with animated traffic flow indicators, providing a clear spatial understanding of the trip.

### ✈️ 3. Real-Time Data Grounding
Integrates **Google Flights, Hotels, and Maps APIs** (via SerpApi) to fetch up-to-the-minute pricing, ratings, and location data, ensuring the itinerary is actionable and accurate.

### 💾 4. Secure Cloud Persistence
Built with **Firebase Authentication** and **Firestore**, allowing users to securely log in, save their chat history, and resume planning sessions across devices.

### 📄 5. Automated Itinerary Export
One-click generation of formatted **.docx** travel documents, summarizing the entire AI-generated plan for offline use.

---

## 🛠️ Tech Stack & Architecture

| Component | Technology Used |
| :--- | :--- |
| **Frontend UI** | Streamlit (Python-based Web Framework) |
| **LLM Engine** | DeepSeek Chat (OpenAI-Compatible API) |
| **Agent Logic** | Function Calling (Tool Use / ReAct Pattern) |
| **Backend DB** | Firebase (Auth & Cloud Firestore) |
| **External APIs** | SerpApi (Google Search Engine Results) |
| **Visualization** | Folium, Streamlit-Folium |

---

## 📦 Installation & Setup

1.  **Clone the repository**
    ```bash
    git clone [https://github.com/KingslyTai/Autonomous-AI-Travel-Agent.git](https://github.com/KingslyTai/Autonomous-AI-Travel-Agent.git)
    cd Autonomous-AI-Travel-Agent
    ```

2.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configuration**
    * Create a `config.py` file in the root directory.
    * Add your API keys (DeepSeek, SerpApi, Firebase):
        ```python
        DEEPSEEK_API_KEY = "your_key_here"
        SERPAPI_API_KEY = "your_key_here"
        # Firebase credentials...
        ```

4.  **Run the Application**
    ```bash
    streamlit run app.py
    ```

---

## 📂 Project Structure

* `app.py`: Main application entry point handling UI and session state.
* `tools.py`: Contains the **Tool Definitions** and **Function Calling** logic (The "Brain").
* `db.py`: Handles Firebase interactions for user management.
* `utils.py`: Utility functions for document generation.

---

## 👨‍💻 Author

**Tai Wen Han**
* **Role**: Software Engineer | AI Application Developer
* **Email**: wenhan.tai@gmail.com
* **GitHub**: [Kingsly Tai](https://github.com/KingslyTai)

---

*Project developed to demonstrate advanced LLM integration and Full-Stack Engineering capabilities.*
