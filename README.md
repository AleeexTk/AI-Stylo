# 🧬 AI-Stylo Core: Personal Fashion OS

## AI Outfit Engine & Gamification Integration Layer

AI-Stylo is a system built under the **EvoPyramid "Architecture of Architectures"** paradigm.
It provides a robust core for fashion personalization, separating the business logic (Contracts, Emdeddings, Telemetry, Gamification) from the visual presentation layer (Vertex).

## 🚀 Two Presentation Modes (Vertices) on One Core

With AI-Stylo, one backend orchestrates entirely different user experiences:

1. **RPG Inventory Mode (`apps/web/streamlit_rpg/app.py`)** — An engaging, gamified standalone dashboard. Users build "outfits" in equipment slots, level up dynamic skills based on their actions, and explore fashion as a game.
2. **B2B Plugin Mode (`apps/web/streamlit_b2b/app.py`)** — A lightweight "Generate Outfit" widget designed for integration directly into partner stores' product cards, instantly boosting cross-sell.

## 🏗 System Invariants (The Core)

* **Contracts (`apps/core/contracts.py`)**: Strict data classes (`Item`, `Profile`, `Outfit`, `Event`) ensuring zero mess in state sharing.
* **Telemetry & Skills Engine (`apps/core/skills_engine.py`)**: A smart event-stream analyzer. Unlocks personality-driven skills ("Taste Stability", "Smart Buyer") only when achieved—no discouraging "locked" zeroes.
* **Partner Overrides**: Retailers can inject custom JSON `skill_pack.json` files to reward specific customer behavior (e.g., buying luxury brands or discounted items) securely, without altering Python logic.

## 🛠 How to Run

1. Clone and install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Launch the primary RPG demo:

   ```bash
   python main.py
   ```

*(Or directly run a specific mode using `streamlit run apps/web/streamlit_rpg/app.py` or `apps/web/streamlit_b2b/app.py`)*

## 📊 KPIs for Pilots

* **Engagement B2C**: ↑ Session length, ↑ Return rate (Retention via gamification).
* **Retail B2B**: ↑ Average Order Value (AOV), ↑ Add to Cart (ATC) proportion of "full outfits" vs "single items", ↓ Returns.

---
*Built according to safe EvoPyramid practices (Security + isolation).*

## 🔒 Access Control

This repository is a self-contained project **AI-Stylo** (powered by EvoPyramid init).
Access to this repository and permission to commit changes is strictly restricted to:

* [@AleeexTk](https://github.com/AleeexTk)
* [@sergiiriabokon](https://github.com/sergiiriabokon)

Direct access to the core `EvoPyramid` from this repository is intentionally restricted.
