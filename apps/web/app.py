import streamlit as st
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
import hashlib
import io
import json
import random

# Настройка страницы
st.set_page_config(page_title="🧬 Personal Fashion OS", layout="wide", page_icon="🧬")
st.title("🧬 Personal Fashion OS")
st.caption("Твій стиль. Твоя екіпіровка. Як у грі.")

# ---------- Модель эмбеддингов ----------
@st.cache_resource
def load_model():
    return SentenceTransformer("all-mpnet-base-v2")

model = load_model()

# ---------- Вспомогательные функции ----------
def now_iso():
    return datetime.utcnow().isoformat()

def hash_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]

def normalize_price(x):
    try:
        return float(str(x).replace(",", ".").strip())
    except:
        return None

def log_event(event_type: str, payload: dict = None):
    st.session_state.events.append({
        "ts": now_iso(),
        "type": event_type,
        "payload": payload or {},
    })

# ---------- Инициализация состояния ----------
def init_state():
    # Профиль пользователя (FashionDNA)
    if "profile" not in st.session_state:
        st.session_state.profile = {
            "user_id": "demo_user",
            "base_vector": None,
            "try_vector": None,
            "use_try": False,
            "brand_affinities": {},
            "budget_profile": {"min": 50, "max": 600, "usual": 150},
            "update_count": 0,
            "similarity_history": [],
            "onboarding_done": False,          # флаг, что микро-опрос пройден
            "fav_color": "#4A90E2",             # акцентный цвет (по умолчанию синий)
            "style_pref": "casual",              # casual / street / minimal / classic / sport
        }
    # Слоты экипировки (текущий образ)
    if "slots" not in st.session_state:
        st.session_state.slots = {
            "top": None,
            "bottom": None,
            "shoes": None,
            "accessory": None,
        }
    # Вишлист (для сохранения)
    if "wishlist" not in st.session_state:
        st.session_state.wishlist = set()
    # События (лог)
    if "events" not in st.session_state:
        st.session_state.events = []
    # Каталоги: catalog_id -> {items, emb, meta}
    if "catalogs" not in st.session_state:
        st.session_state.catalogs = {}
    # Текущий каталог
    if "current_catalog" not in st.session_state:
        st.session_state.current_catalog = None
    # Временное хранилище для карусели выбора
    if "slot_selection" not in st.session_state:
        st.session_state.slot_selection = None   # какой слот сейчас выбираем
    # Для микро-опроса: храним этап
    if "onboarding_step" not in st.session_state:
        st.session_state.onboarding_step = 0 if not st.session_state.profile["onboarding_done"] else -1

init_state()
profile = st.session_state.profile

# ---------- Микро-опрос ----------
if not profile["onboarding_done"]:
    with st.container():
        st.markdown("## 🎮 Налаштуй свій стиль за 30 секунд")

        step = st.session_state.onboarding_step

        if step == 0:
            st.markdown("### 1. Твій улюблений колір")
            cols = st.columns(5)
            colors = {
                "Синій": "#4A90E2",
                "Зелений": "#50B883",
                "Чорний": "#2C3E50",
                "Білий": "#ECF0F1",
                "Рожевий": "#E84393",
            }
            for i, (name, code) in enumerate(colors.items()):
                with cols[i]:
                    if st.button(name, key=f"color_{name}"):
                        profile["fav_color"] = code
                        st.session_state.onboarding_step = 1
                        st.rerun()

        elif step == 1:
            st.markdown("### 2. Який стиль тобі ближче?")
            styles = ["Casual", "Street", "Minimal", "Classic", "Sport"]
            cols = st.columns(len(styles))
            for i, style in enumerate(styles):
                with cols[i]:
                    if st.button(style, key=f"style_{style}"):
                        profile["style_pref"] = style.lower()
                        st.session_state.onboarding_step = 2
                        st.rerun()

        elif step == 2:
            st.markdown("### 3. Твій бюджет на образ (грн)")
            budget = st.slider("", 0, 10000, (500, 3000), step=100)
            if st.button("Далі"):
                profile["budget_profile"]["min"] = budget[0]
                profile["budget_profile"]["max"] = budget[1]
                profile["budget_profile"]["usual"] = (budget[0] + budget[1]) // 2
                st.session_state.onboarding_step = 3
                st.rerun()

        elif step == 3:
            st.markdown("### 4. Твій розмір (необов'язково)")
            size = st.selectbox("Оберіть розмір", ["XS", "S", "M", "L", "XL", "Пропустити"])
            if st.button("Завершити"):
                if size != "Пропустити":
                    profile["size"] = size
                profile["onboarding_done"] = True
                st.session_state.onboarding_step = -1
                log_event("onboarding_complete", profile)
                st.rerun()
    st.stop()  # Останавливаем дальнейший рендеринг, пока опрос не пройден

# ---------- Основной интерфейс ----------
# Заголовок с персонализированным цветом
st.markdown(f"<style> .stButton>button {{ background-color: {profile['fav_color']}; color: white; }} </style>", unsafe_allow_html=True)

# Боковая панель для управления каталогом (можно скрыть, оставим компактно)
with st.sidebar:
    st.header("🗂️ Каталог")
    # Если нет каталогов, загружаем демо
    if not st.session_state.catalogs:
        # Создадим демо-товары (те же, что и раньше)
        demo_items = [
            {"id": "1", "name": "Оверсайз худи", "brand": "Balenciaga", "price": 4500, "description": "Чорний оверсайз худи, streetwear", "image": "https://picsum.photos/id/1015/400/500", "category": "top"},
            {"id": "2", "name": "Slim джинси", "brand": "Levi's", "price": 2700, "description": "Класичні сині джинси slim", "image": "https://picsum.photos/id/133/400/500", "category": "bottom"},
            {"id": "3", "name": "Білі кросівки", "brand": "Nike", "price": 3200, "description": "Мінімалістичні білі кросівки", "image": "https://picsum.photos/id/201/400/500", "category": "shoes"},
            {"id": "4", "name": "Шкіряна куртка", "brand": "Zara", "price": 5200, "description": "Коричнева шкіряна куртка", "image": "https://picsum.photos/id/251/400/500", "category": "top"},
            {"id": "5", "name": "Квіткова сукня", "brand": "H&M", "price": 2100, "description": "Міді сукня з квітковим принтом", "image": "https://picsum.photos/id/29/400/500", "category": "bottom"},
            {"id": "6", "name": "Широкі штани", "brand": "Uniqlo", "price": 1800, "description": "Бежеві wide-leg брюки", "image": "https://picsum.photos/id/1016/400/500", "category": "bottom"},
            {"id": "7", "name": "Кашеміровий светр", "brand": "COS", "price": 3900, "description": "Сірий м'який светр", "image": "https://picsum.photos/id/669/400/500", "category": "top"},
            {"id": "8", "name": "Кеди Converse", "brand": "Converse", "price": 2500, "description": "Чорні класичні кеди", "image": "https://picsum.photos/id/870/400/500", "category": "shoes"},
        ]
        # Добавим категорию для каждого товара (для слотов)
        st.session_state.catalogs["demo"] = {
            "items": demo_items,
            "emb": None,  # позже заполним
            "meta": {"source": "built-in", "count": len(demo_items)}
        }
        # Вычислим эмбеддинги для демо
        descs = [it["description"] for it in demo_items]
        embs = model.encode(descs, normalize_embeddings=True)
        st.session_state.catalogs["demo"]["emb"] = {demo_items[i]["id"]: embs[i] for i in range(len(demo_items))}
        st.session_state.current_catalog = "demo"

    # Выбор каталога
    catalog_ids = list(st.session_state.catalogs.keys())
    selected_catalog = st.selectbox("Активний каталог", catalog_ids, index=catalog_ids.index(st.session_state.current_catalog) if st.session_state.current_catalog in catalog_ids else 0)
    st.session_state.current_catalog = selected_catalog
    cat = st.session_state.catalogs[selected_catalog]
    items = cat["items"]
    item_emb = cat["emb"]

    # Кнопка сброса профиля (опционально)
    if st.button("♻️ Скинути профіль"):
        for key in ["profile", "slots", "wishlist", "events"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# ---------- Основная область ----------
# Разделим на две колонки: левая (аватар + слоты) и правая (панель управления)
left_col, right_col = st.columns([1, 1], gap="medium")

with left_col:
    st.subheader("🖼️ Твій образ")
    # Центральный аватар (можно заглушка)
    avatar_placeholder = st.empty()
    with avatar_placeholder.container():
        st.image("https://via.placeholder.com/400x500?text=Your+Look", use_container_width=True)
    # Слоты в виде сетки 2x2
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown("**Верх**")
        top_btn = st.button("➕" if st.session_state.slots["top"] is None else "🔄", key="slot_top")
        if st.session_state.slots["top"]:
            top_item = next((it for it in items if it["id"] == st.session_state.slots["top"]), None)
            if top_item:
                st.image(top_item["image"], width=100)
                st.caption(top_item["name"])
        else:
            st.caption("порожньо")

        st.markdown("**Низ**")
        bottom_btn = st.button("➕" if st.session_state.slots["bottom"] is None else "🔄", key="slot_bottom")
        if st.session_state.slots["bottom"]:
            bottom_item = next((it for it in items if it["id"] == st.session_state.slots["bottom"]), None)
            if bottom_item:
                st.image(bottom_item["image"], width=100)
                st.caption(bottom_item["name"])

    with col_s2:
        st.markdown("**Взуття**")
        shoes_btn = st.button("➕" if st.session_state.slots["shoes"] is None else "🔄", key="slot_shoes")
        if st.session_state.slots["shoes"]:
            shoes_item = next((it for it in items if it["id"] == st.session_state.slots["shoes"]), None)
            if shoes_item:
                st.image(shoes_item["image"], width=100)
                st.caption(shoes_item["name"])

        st.markdown("**Аксесуар**")
        acc_btn = st.button("➕" if st.session_state.slots["accessory"] is None else "🔄", key="slot_acc")
        if st.session_state.slots["accessory"]:
            acc_item = next((it for it in items if it["id"] == st.session_state.slots["accessory"]), None)
            if acc_item:
                st.image(acc_item["image"], width=100)
                st.caption(acc_item["name"])

    # Обработка нажатий на слоты (вызов карусели)
    # Мы будем использовать session_state для хранения текущего выбранного слота
    if top_btn:
        st.session_state.slot_selection = "top"
    if bottom_btn:
        st.session_state.slot_selection = "bottom"
    if shoes_btn:
        st.session_state.slot_selection = "shoes"
    if acc_btn:
        st.session_state.slot_selection = "accessory"

with right_col:
    st.subheader("⚙️ Панель керування")

    # Панель бюджета (слайдер с двумя значениями)
    st.markdown("**💰 Бюджет**")
    min_b, max_b = profile["budget_profile"]["min"], profile["budget_profile"]["max"]
    budget_range = st.slider(
        "Діапазон цін (грн)",
        min_value=0,
        max_value=10000,
        value=(min_b, max_b),
        step=100,
        key="budget_slider"
    )
    profile["budget_profile"]["min"], profile["budget_profile"]["max"] = budget_range

    # Пресеты стиля (чипсы)
    st.markdown("**🎯 Стиль**")
    style_options = ["Casual", "Street", "Minimal", "Classic", "Sport"]
    # Преобразуем текущий стиль в индекс для выбора
    current_style = profile["style_pref"].capitalize()
    if current_style not in style_options:
        current_style = "Casual"
    style_index = style_options.index(current_style) if current_style in style_options else 0
    selected_style = st.radio(
        "Оберіть стиль",
        style_options,
        index=style_index,
        horizontal=True,
        label_visibility="collapsed"
    )
    profile["style_pref"] = selected_style.lower()

    # Событие (контекст)
    st.markdown("**⚡ Подія**")
    event_options = ["Будній день", "Офіс", "Побачення", "Вечірка", "Подорож"]
    selected_event = st.selectbox("Оберіть подію", event_options, index=0, label_visibility="collapsed")

    # Кнопка генерації образу
    if st.button("🎲 Згенерувати образ", use_container_width=True):
        # Простая логика: выбираем случайные товары подходящих категорий и в пределах бюджета
        candidates = [it for it in items if budget_range[0] <= it["price"] <= budget_range[1]]
        # Разделим по категориям
        tops = [it for it in candidates if it.get("category") == "top"]
        bottoms = [it for it in candidates if it.get("category") == "bottom"]
        shoes = [it for it in candidates if it.get("category") == "shoes"]
        accs = [it for it in candidates if it.get("category") == "accessory"]

        if tops:
            st.session_state.slots["top"] = random.choice(tops)["id"]
        if bottoms:
            st.session_state.slots["bottom"] = random.choice(bottoms)["id"]
        if shoes:
            st.session_state.slots["shoes"] = random.choice(shoes)["id"]
        if accs:
            st.session_state.slots["accessory"] = random.choice(accs)["id"]

        log_event("generate_outfit", {"budget": budget_range, "style": selected_style, "event": selected_event})
        st.rerun()

    # Кнопка покупки
    total_price = 0
    filled_slots = []
    for slot_name, item_id in st.session_state.slots.items():
        if item_id:
            item = next((it for it in items if it["id"] == item_id), None)
            if item:
                total_price += item["price"]
                filled_slots.append(item["name"])
    if filled_slots:
        st.markdown(f"**🛒 Разом: {total_price} грн**")
        if st.button("Купити образ", use_container_width=True):
            # Здесь можно добавить редирект на корзину магазина
            st.success("Образ додано до кошика!")
            log_event("buy_outfit", {"items": filled_slots, "total": total_price})
    else:
        st.info("Оберіть речі або згенеруйте образ")

# ---------- Карусель выбора предмета для слота ----------
if st.session_state.slot_selection is not None:
    slot = st.session_state.slot_selection
    st.markdown(f"## Оберіть {slot}")

    # Получаем товары нужной категории
    cat_map = {"top": "top", "bottom": "bottom", "shoes": "shoes", "accessory": "accessory"}
    category = cat_map.get(slot, slot)
    candidates = [it for it in items if it.get("category") == category and budget_range[0] <= it["price"] <= budget_range[1]]

    if not candidates:
        st.warning("Немає товарів у цій категорії в межах бюджету")
        if st.button("Назад"):
            st.session_state.slot_selection = None
            st.rerun()
    else:
        # Покажем в виде сетки
        cols = st.columns(3)
        for idx, item in enumerate(candidates[:9]):  # ограничим 9
            with cols[idx % 3]:
                st.image(item["image"], width=150)
                st.caption(f"{item['name']} | {item['price']} грн")
                if st.button("Обрати", key=f"select_{item['id']}"):
                    st.session_state.slots[slot] = item["id"]
                    st.session_state.slot_selection = None
                    log_event("slot_selected", {"slot": slot, "item_id": item["id"]})
                    st.rerun()
        if st.button("Скасувати"):
            st.session_state.slot_selection = None
            st.rerun()
    st.stop()  # Останавливаем рендеринг основной страницы, пока выбираем

# ---------- Логи (для отладки) ----------
with st.expander("📎 Останні події"):
    if st.session_state.events:
        df = pd.DataFrame(st.session_state.events[-10:])
        st.dataframe(df, use_container_width=True, hide_index=True)
        if st.button("Експортувати логи"):
            st.download_button(
                "Завантажити events.jsonl",
                data="\n".join([json.dumps(e, ensure_ascii=False) for e in st.session_state.events]).encode("utf-8"),
                file_name="events.jsonl",
                mime="application/jsonl",
            )
    else:
        st.info("Подій поки немає")
