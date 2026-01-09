# AI-Travel-Agent
An autonomous AI agent that plans travel itineraries, visualizes routes on maps, and generates Word documents
# 🧠 Autonomous AI Travel Agent

## 📖 Overview
This is a full-stack AI application powered by **DeepSeek LLM** and **Streamlit**. It acts as an autonomous travel planner that can:
1.  **Plan Itineraries**: Uses Chain-of-Thought (CoT) reasoning to break down travel plans.
2.  **Real-Time Data**: Integrates **Google Flights & Maps APIs** (via SerpApi) to fetch real prices and locations.
3.  **Visualize Routes**: Generates interactive maps with driving vs. transit time comparison.
4.  **Export Plans**: Automatically generates a formatted `.docx` Word document for the user.

## 🛠️ Tech Stack
- **Frontend**: Streamlit
- **AI Core**: DeepSeek (OpenAI-compatible API)
- **APIs**: SerpApi (Google Search Engine Results)
- **Visualization**: Folium (Maps)
- **File Handling**: python-docx

## 🚀 How to Run
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
