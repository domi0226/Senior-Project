import streamlit as st
import json
import urllib.parse
import os
import re
import plotly.graph_objects as go

# =====================================================================
# 🌐 網頁全域視覺配置
# =====================================================================
st.set_page_config(page_title="Steam Recommender", layout="centered")

steam_premium_css = """
<style>
    .stApp {
        background: linear-gradient(180deg, #1b2838 0%, #101822 100%) !important;
        color: #c7d5e0 !important;
        font-family: "Motiva Sans", Arial, Helvetica, sans-serif;
    }
    h1, h2, h3, h4, p, label {
        color: #ffffff !important;
    }
    .stSelectbox div[data-baseweb="select"], 
    .stMultiSelect div[data-baseweb="select"],
    .stTextInput input {
        background-color: #121e2c !important;
        border: 1px solid #2a475e !important;
        color: #dcdedf !important;
    }
    div.stButton > button:first-child {
        background: linear-gradient( to right, #2196F3 0%, #0d47a1 100%) !important;
        color: #ffffff !important;
        border: none !important;
        width: 100%;
        padding: 12px;
        font-weight: bold;
        font-size: 16px;
    }
    .submit-btn > button:first-child {
        background: linear-gradient( to right, #a4d007 0%, #536f00 100%) !important;
    }
    .more-btn > button:first-child {
        background: linear-gradient( to right, #47b5ff 0%, #1363df 100%) !important;
    }
    .reset-btn > button:first-child {
        background: linear-gradient( to right, #61677a 0%, #393e46 100%) !important;
    }
    .steam-status-box {
        background-color: rgba(22, 34, 49, 0.9) !important;
        border: 1px solid #3a5b78 !important;
        padding: 16px;
        margin-top: 10px;
        margin-bottom: 25px;
        border-radius: 4px;
    }
    .game-card {
        background: rgba(22, 34, 49, 0.6) !important;
        border: 1px solid #233c51 !important;
        padding: 16px;
        margin-bottom: 14px;
        border-radius: 4px;
        transition: transform 0.2s, border-color 0.2s;
    }
    .game-card:hover {
        border-color: #66c0f4 !important;
        background: rgba(22, 34, 49, 0.9) !important;
    }
    .game-title-link {
        color: #66c0f4 !important;
        font-size: 19px;
        text-decoration: none;
        font-weight: bold;
    }
    .meta-text {
        color: #8f98a0 !important;
        font-size: 13px;
        margin-top: 4px;
    }
    .dynamic-notice {
        color: #ffcc00 !important;
        font-weight: bold;
        background: rgba(255, 204, 0, 0.08);
        padding: 12px;
        border-left: 4px solid #ffcc00;
        margin-bottom: 20px;
        font-size: 14px;
    }
    .association-reason {
        background: rgba(102, 192, 244, 0.08);
        border-left: 3px solid #66c0f4;
        padding: 8px 12px;
        margin: 8px 0 6px 0;
        font-size: 13px;
        color: #66c0f4;
        border-radius: 0 4px 4px 0;
    }
</style>
"""
st.markdown(steam_premium_css, unsafe_allow_html=True)

st.title("Steam 大數據關聯分析推薦系統")
st.write("---")

# 初始化 Session State
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'cluster_id' not in st.session_state:
    st.session_state.cluster_id = None
if 'cluster_name' not in st.session_state:
    st.session_state.cluster_name = ""
if 'show_count' not in st.session_state:
    st.session_state.show_count = 6
if 'calculated_recommendations' not in st.session_state:
    st.session_state.calculated_recommendations = []

# =====================================================================
# ⚡ 讀取真實 JSON 快取機制 (對接你剛轉換完的 apriori_rules.json)
# =====================================================================
json_file = 'apriori_rules.json'
@st.cache_data
def load_json_rules():
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}
global_rules_db = load_json_rules()

# 數字對應中文客群標籤的字典
cluster_mapping = {
    0: "獨玩劇情折扣黨",
    1: "校園連線競技團",
    2: "佛系高自由孤狼",
    3: "硬核重度沙盒黨",
    4: "精緻多元探索者",
    5: "療癒派對休閒團"
}

# =====================================================================
# 🔮 決策分類模型
# =====================================================================
def predict_cluster_id(gender, hours, budget, motivation):
    if gender == '男':
        if '競技（PVP）' in motivation or hours in ['15~30hr', '30hr以上']:
            return 1
        elif budget in ['1001~3000元', '3000元以上'] or '喜歡挑戰' in motivation:
            return 0
        else:
            return 2
    else: 
        if '打發時間' in motivation or '放鬆' in motivation:
            return 5
        elif '喜歡高自由度' in motivation or '經營建造' in motivation:
            return 3
        else:
            return 4

# =====================================================================
# 🎯 第二階段：根據客群動態跳出的「代表性焦點大作池」
# =====================================================================
cluster_game_pool = {
    0: ["Elden Ring（艾爾登法環）", "黑神話：悟空", "Cyberpunk 2077（電馭叛客 2077）", "GTA V（俠盜獵車手 5）", "Monster Hunter（魔物獵人）", "The Witcher 3: Wild Hunt（巫師 3：狂獵）", "Red Dead Redemption 2（碧血狂殺 2）", "Dark Souls Series（黑暗靈魂系列）", "Cities: Skylines（都市：天際線）", "Stardew Valley（星露谷物語）", "Tomb Raider Trilogy（古墓奇兵三部曲）"],
    1: ["Counter-Strike 2（絕對武力 CS2）", "Apex Legends（Apex 英雄）", "PUBG: Battlegrounds（絕地求生）", "Tom Clancy's Rainbow Six Siege（虹彩六號：圍攻行動）", "GTA V（俠盜獵車手 5）", "Elden Ring（艾爾登法環）", "Battlefield 1 / Battlefield V（戰地風雲 1 / 5）", "Team Fortress 2（絕地要塞 2）", "Lethal Company（致命公司）", "Overcooked! 2（煮過頭 2）", "Minecraft"],
    2: ["GTA V（俠盜獵車手 5）", "The Witcher 3: Wild Hunt（巫師 3：狂獵）", "Monster Hunter（魔物獵人）", "Elden Ring（艾爾登法環）", "Cyberpunk 2077（電馭叛客 2077）", "黑神話：悟空", "Red Dead Redemption 2（碧血狂殺 2）", "Fallout 4（異塵餘生 4）", "Euro Truck Simulator 2（歐洲卡車模擬 2）", "Cities: Skylines（都市：天際線）"],
    3: ["Cities: Skylines（都市：天際線）", "Stardew Valley（星露谷物語）", "The Sims 4（模擬市民 4）", "Minecraft", "Overcooked! 2（煮過頭 2）", "GTA V（俠盜獵車手 5）", "Age of Empires （世紀帝國 ）", "Civilization VI（文明帝國 6）", "Euro Truck Simulator 2（歐洲卡車模擬 2）", "Lethal Company（致命公司）", "Fall Guys（糖豆人）"],
    4: ["The Sims 4（模擬市民 4）", "Overcooked! 2（煮過頭 2）", "Stardew Valley（星露谷物語）", "Minecraft", "Cities: Skylines（都市：天際線）", "GTA V（俠盜獵車手 5）", "Party Animals（動物派對）", "Human: Fall Flat（一起來捉弄人）", "Dead by Daylight（黎明殺機）", "Rocket League（火箭聯盟）"],
    5: ["Overcooked! 2（煮過頭 2）", "The Sims 4（模擬市民 4）", "Stardew Valley（星露谷物語）", "Minecraft", "Cities: Skylines（都市：天際線）", "Party Animals（動物派對）", "Fall Guys（糖豆人）", "Among Us（我們之中）", "Monster Hunter（魔物獵人）", "Left 4 Dead 2（惡靈勢力 2）"]
}

# =====================================================================
# 📋 第一階段：問卷輸入 (已拔除 Email 欄位)
# =====================================================================
st.markdown("### 1. 填寫基本客群分析問卷")
col1, col2 = st.columns(2)

with col1:
    user_gender = st.selectbox("性別指標", ['男', '女'])
    user_hours = st.selectbox("週均遊玩時數", ['5hr以下', '5~15hr', '15~30hr', '30hr以上'])

with col2:
    user_budget = st.selectbox("月均數位消費預算", ['0元', '1~500元', '501~1000元', '1001~3000元', '3000元以上'])
    user_motivations = st.multiselect("遊玩動機（多選）", ['放鬆', '打發時間', '競技（PVP）', '喜歡合作', '喜歡高自由度', '喜歡挑戰', '沉浸式劇情', '經營建造'])

if st.session_state.step == 1:
    st.write("")
    if st.button("下一步：進行特徵鎖定"):
        st.session_state.cluster_id = predict_cluster_id(user_gender, user_hours, user_budget, user_motivations)
        # 直接轉換成與 JSON 相符的中文客群名稱
        st.session_state.cluster_name = cluster_mapping.get(st.session_state.cluster_id, "獨玩劇情折扣黨")
        st.session_state.step = 2
        st.session_state.show_count = 6 
        st.calculated_recommendations = []
        st.rerun()

# =====================================================================
# 🎮 第二階段：動態下拉選單與 Apriori 子集比對
# =====================================================================
if st.session_state.step >= 2:
    st.write("---")
    st.markdown(f"""
    <div class="steam-status-box">
        <div style="font-size: 16px; color: #66c0f4; font-weight: bold;">
              【分類模型分析完畢！您的遊戲遊玩分類是：{st.session_state.cluster_name}】
        </div>
    </div>
    """, unsafe_allow_html=True)

    # =====================================================================
    # 📊 圖表區：雷達圖 + 圓餅圖
    # =====================================================================

    # 各客群六維雷達圖數值定義（0~10）
    radar_data = {
        0: [7, 2, 6, 9, 3, 8],
        1: [9, 7, 4, 3, 5, 4],
        2: [4, 2, 9, 7, 5, 5],
        3: [3, 5, 10, 4, 6, 4],
        4: [4, 8, 6, 5, 8, 5],
        5: [3, 9, 4, 3, 10, 6],
    }
    radar_labels = ['競技性', '合作性', '自由度', '劇情深度', '休閒感', '預算敏感度']

    st.markdown("<div style=\'color:#66c0f4;font-weight:bold;font-size:14px;margin-bottom:4px;\'>🕸️ 您的遊戲人格雷達圖</div>", unsafe_allow_html=True)
    vals = radar_data[st.session_state.cluster_id]
    vals_closed = vals + [vals[0]]
    labels_closed = radar_labels + [radar_labels[0]]
    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=vals_closed,
        theta=labels_closed,
        fill="toself",
        fillcolor="rgba(102,192,244,0.2)",
        line=dict(color="#66c0f4", width=2),
        name=st.session_state.cluster_name
    ))
    fig_radar.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 10], tickfont=dict(color="#8f98a0", size=9), gridcolor="#2a475e"),
            angularaxis=dict(tickfont=dict(color="#c7d5e0", size=11), gridcolor="#2a475e")
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        margin=dict(l=40, r=40, t=20, b=20),
        height=320
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    st.write("")
    st.markdown("###  2. 您曾持有 or 遊玩過哪些 Steam 核心焦點大作？")
    st.markdown(f"<div class='dynamic-notice'> 系統已為您的客群動態精選出代表性大作。若都沒玩過，直接留空點擊提交即可！</div>", unsafe_allow_html=True)

    current_pool = cluster_game_pool[st.session_state.cluster_id]
    
    played_games = st.multiselect(
        label="點擊此處選擇您玩過的遊戲：",
        options=current_pool,
        placeholder="Choose options"
    )

    st.write("---")
    
    if st.session_state.step == 2:
        st.markdown("<div class='submit-btn'>", unsafe_allow_html=True)
        if st.button("確認提交並生成推薦報告"):
            # 撈取該客群專屬的關聯規則
            rules = global_rules_db.get(st.session_state.cluster_name, [])
            
            # 清洗並處理玩家已擁有的遊戲集合
            played_set = set([g.strip() for g in played_games])
            
            recommended_pool = []
            seen_recommendations = set()

            # 🛠️ 1. 核心比對演算法：Apriori 子集比對
            if len(played_set) > 0:
                for rule in rules:
                    antecedents = [x.strip() for x in rule.get("antecedents", [])]
                    consequents = rule.get("consequents", "").strip()
                    
                    # 學術邏輯：如果規則中的前項遊戲組合，完全是玩家玩過遊戲的「子集」
                    if set(antecedents).issubset(played_set):
                        # 且推薦的遊戲玩家目前沒玩過，也還沒被推薦過
                        if consequents not in played_set and consequents not in seen_recommendations:
                            seen_recommendations.add(consequents)
                            recommended_pool.append({
                                "game": consequents,
                                "lift": rule.get("lift", 0),
                                "confidence": rule.get("confidence", 0),
                                "antecedents": antecedents,   # ← 新增：保留觸發的前項遊戲
                                "type": "關聯規則精準推薦"
                            })
            
            # 將關聯分析推薦的遊戲，按照「提升度 (Lift)」由大到小排序（含金量最高）
            recommended_pool = sorted(recommended_pool, key=lambda x: x["lift"], reverse=True)

            # ← 改動：final_recommendations 改為存 dict，保留關聯來源資訊
            final_recommendations = []
            for item in recommended_pool:
                final_recommendations.append({
                    "game": item["game"],
                    "reason": item["antecedents"],
                    "lift": item["lift"]
                })

            # 📦 2. 冷啟動補底機制：如果關聯規則不夠多，用熱門客群池塞滿，確保使用者不會看到空白
            backup_pool = {
                0: ["黑神話：悟空", "Elden Ring（艾爾登法環）", "Cyberpunk 2077（電馭叛客 2077）", "Red Dead Redemption 2（碧血狂殺 2）", "Monster Hunter（魔物獵人）", "Dark Souls Series（黑暗靈魂系列）", "The Witcher 3: Wild Hunt（巫師 3：狂獵）", "Fallout 4（異塵餘生 4）", "GTA V（俠盜獵車手 5）", "Civilization VI（文明帝國 6）"],
                1: ["Counter-Strike 2（絕對武力 CS2）", "Apex Legends（Apex 英雄）", "PUBG: Battlegrounds（絕地求生）", "Tom Clancy's Rainbow Six Siege（虹彩六號：圍攻行動）", "Battlefield 1 / Battlefield V（戰地風雲 1 / 5）", "Team Fortress 2（絕地要塞 2）", "GTA V（俠盜獵車手 5）", "Elden Ring（艾爾登法環）", "Lethal Company（致命公司）"],
                2: ["GTA V（俠盜獵車手 5）", "The Witcher 3: Wild Hunt（巫師 3：狂獵）", "Red Dead Redemption 2（碧血狂殺 2）", "Cyberpunk 2077（電馭叛客 2077）", "黑神話：悟空", "Monster Hunter（魔物獵人）", "Elden Ring（艾爾登法環）", "Fallout 4（異塵餘生 4）", "Euro Truck Simulator 2（歐洲卡車模擬 2）"],
                3: ["Cities: Skylines（都市：天際線）", "Stardew Valley（星露谷物語）", "The Sims 4（模擬市民 4）", "Minecraft", "Civilization VI（文明帝國 6）", "Age of Empires （世紀帝國 ）", "Overcooked! 2（煮過頭 2）", "雙人成行（It Takes Two）", "Human: Fall Flat（一起來捉弄人）", "GTA V（俠盜獵車手 5）"],
                4: ["The Sims 4（模擬市民 4）", "Overcooked! 2（煮過頭 2）", "Stardew Valley（星露谷物語）", "Minecraft", "Party Animals（動物派對）", "雙人成行（It Takes Two）", "Human: Fall Flat（一起來捉弄人）", "Fall Guys（糖豆人）", "Cities: Skylines（都市：天際線）", "Among Us（我們之中）"],
                5: ["Overcooked! 2（煮過頭 2）", "The Sims 4（模擬市民 4）", "Stardew Valley（星露谷物語）", "Fall Guys（糖豆人）", "Among Us（我們之中）", "Party Animals（動物派對）", "Human: Fall Flat（一起來捉弄人）", "Minecraft", "雙人成行（It Takes Two）", "Cities: Skylines（都市：天際線）"]
            }

            already_in = set(item["game"] for item in final_recommendations)
            for bg in backup_pool[st.session_state.cluster_id]:
                if bg not in played_set and bg not in already_in:
                    # 冷啟動補底的遊戲不帶關聯來源
                    final_recommendations.append({
                        "game": bg,
                        "reason": [],
                        "lift": None
                    })

            st.session_state.calculated_recommendations = final_recommendations
            st.session_state.step = 3
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# =====================================================================
# 🏆 第三階段：動態分頁展示區 (已拔除信箱成功提示)
# =====================================================================
if st.session_state.step == 3:
    st.markdown("### 3. 基於雙軌模型之個人化推薦結果")

    # 🔗 核心字串清洗函數：拔除 Steam 無法識別的括號註解
    def clean_game_name(full_name):
        cleaned = re.sub(r'[\uff08\(].*?[\uff09\)]', '', full_name)
        return cleaned.strip()

    game_descriptions = {
        "Elden Ring（艾爾登法環）": "2022 年度最佳遊戲！由宮崎英高與喬治·R·R·馬丁聯手打造的黑暗奇幻開放世界，講求極具挑戰性的魂系戰術與宏大破碎的歷史史詩。",
        "黑神話：悟空": "現象級東方魔幻動作 RPG！以《西遊記》為背景，玩家扮演「天命人」踏上充滿危險與驚奇的西行之路，具備頂級的畫面視覺與爽快多變的棍法法術戰鬥。",
        "Dark Souls Series（黑暗靈魂系列）": "硬核動作 RPG 的受死經典。以高難度關卡設計、碎片化敘事及深奧的世界觀著稱，每一次擊敗頭目都能帶來無與倫比的成就感。",
        "Monster Hunter（魔物獵人）": "硬核共鬥遊戲代表作！玩家作為獵人追蹤並狩獵巨大的魔物，利用採集素材打造更強的武器防具，講求技術、破壞部位與團隊完美協作。",
        "Monster Hunter: World（魔物獵人：世界）": "讓系列走向全球的巔峰巨作。擁有生態系極其擬真的無縫開放地圖，流暢的動態狩獵與豐富的武器派生，是多人共鬥的必玩聖經。",
        "Counter-Strike 2（絕對武力 CS2）": "全球射擊競技的無冕之王。基於 Source 2 引擎全面進化，講求極致精準的槍法、團隊戰術、經濟控管以及煙霧彈等物理互動。",
        "Apex Legends（Apex 英雄）": "節奏極快的三人團隊大逃殺。結合了各具獨特戰術技能的英雄角色，擁有無與倫比的滑鏟、滑索等流暢位移與激烈的近身槍戰。",
        "PUBG: Battlegrounds（絕地求生）": "戰術大逃殺的始祖。百人空投孤島，從一無所有開始搜刮物資、規劃安全區跑毒路線，講求真實彈道生存與中遠距離對槍。",
        "Tom Clancy's Rainbow Six Siege（虹彩六號：圍攻行動）": "高科技室內近身反恐攻防戰。主打全地圖牆面與地板的可破壞機制，防守方佈置陷阱、進攻方無人機偵查，策略性極高的硬核射擊。",
        "戰地風雲 5": "體驗規模宏大的二戰百人戰場。結合步兵、坦克、飛機的多兵種協同作戰，擁有極佳的畫面破壞效果與戰場沉浸感。",
        "Battlefield 1 / Battlefield V（戰地風雲 1 / 5）": "全面性的大戰場射擊遊戲。逼真再現了一戰與二戰的慘烈戰役，以海陸空載具大亂鬥以及極具震撼力的破壞物理效果聞名。",
        "Team Fortress 2（絕地要塞 2）": "Valve 旗下的長壽經典美式卡通風射擊遊戲。擁有多種個性鮮明且職責明確的兵種，主打幽默歡樂的團隊推車與奪旗攻防。",
        "GTA V（俠盜獵車手 5）": "史上最暢銷的開放世界神作。在洛聖都展開三位主角的犯罪生涯，線上模式（GTA Online）更提供無限延伸的合作、競技與社交建造體驗。",
        "Cyberpunk 2077（電馭叛客 2077）": "極致沉浸的未來科幻世界。在充滿霓虹燈與改裝科技的「夜城」中展開冒險，擁有豐富的分支劇情、高自由度的義體改造與深刻的角色故事。",
        "The Witcher 3: Wild Hunt（巫師 3：狂獵）": "當代劇情神作 RPG。扮演利維亞的傑洛特在龐大的奇幻世界中尋找預言之子，充滿了道德灰色地帶的深刻抉擇與令人難忘的支線故事。",
        "Red Dead Redemption 2（碧血狂殺 2）": "寫實開放世界的巔峰之作。體驗美國西部時代末期亞瑟·摩根與幫派的興衰，細節多到令人讚嘆，劇情宏大且極具情感渲染力。",
        "Fallout 4（異塵餘生 4）": "經典廢土風格的開放世界角色扮演遊戲。玩家作為避難所倖存者在核爆後的波士頓荒原尋找兒子，主打建立據點與戰鬥系統。",
        "上古卷軸 5": "奇幻 RPG 的永恆不朽之作。扮演傳說中的「龍裔」在天際省自由冒險，擁有極其龐大的主支線任務，以及近乎無限擴充的玩家 Mod 生態。",
        "Cities: Skylines（都市：天際線）": "現代城市模擬建造的絕對經典。玩家從規劃道路、劃定區域到管理水電交通、稅收與政策，體驗從溫馨小鎮發展到超級大都市的完整經營樂趣。",
        "Stardew Valley（星露谷物語）": "療癒感滿分的一流鄉村生活模擬。繼承爺爺的荒廢農場，開始墾荒、種植、畜牧、釣魚、挖礦，並與鵜鶘鎮的居民建立深厚的友誼與浪漫情緣。",
        "The Sims 4（模擬市民 4）": "終極人生沙盒模擬！自由創造獨一無二的人物外觀與個性，親手設計夢幻豪宅，並掌控他們在職場、社交、戀愛中的精彩人生大小事。",
        "Minecraft": "擁有無限可能的方塊世界.在生存模式中採集、防禦魔物，或在創造模式中利用無限資源蓋出城堡、重現世界奇觀，自由度超乎想像。",
        "模擬城市": "經典的老牌都市計畫遊戲。著重於宏觀的都市發展、經濟供需與災難應變，是無數模擬建造玩家的啟盟之作。",
        "Age of Empires （世紀帝國 ）": "風靡全球的經典歷史即時戰略遊戲（RTS）。玩家需要調配村民採集資源、升級時代、建立軍隊並指揮排兵布陣，在戰場上用智謀稱霸。",
        "Civilization VI（文明帝國 6）": "「再一回合就天亮」的魔性回合制策略遊戲。玩家扮演歷史領袖，從石器時代開始發展文明，透過科學、文化、軍事或宗教手段稱霸世界。",
        "Palworld（幻獸帕魯）": "結合開放世界生存、建造與神奇生物搜集的現象級作品。玩家可以與奇妙生物「帕魯」並肩作戰，或是指派牠們在工廠進行自動化流水線生产。",
        "Overcooked! 2（煮過頭 2）": "歡樂與混亂兼具的經典派對遊戲。與好友攜手在移動的地板、傳送帶或失火的廚房中切菜、炒菜並出餐，極度考驗團隊默契（與友情）。",
        "Party Animals（動物派對）": "基於物理引擎的超萌動物大亂鬥！操控毛茸茸的貓咪、小狗或恐龍互毆、用武器把對手扔出場外，玩起來充滿魔性笑料，極適合聚會。",
        "Human: Fall Flat（一起來捉弄人）": "面條人風格的魔性物理合作解謎遊戲。操控走路搖晃、雙手黏性的軟泥角色，靠著攀爬與推拉機關闖關，過程中往往充斥著互相陷害的歡笑聲。",
        "Fall Guys（糖豆人）": "大型多人線上歡樂闖關綜藝秀。數十位玩家操控笨拙的糖豆人越過各種混亂的障礙機關，在淘汰賽中爭奪唯一的冠軍皇冠。",
        "Among Us（我們之中）": "太空版的「狼人殺」心理戰！船員們需要一邊修復太空船，一邊透過討論與投票，揪出潛伏在隊伍中密謀暗殺所有人的偽裝者。",
        "雙人成行（It Takes Two）": "純雙人合作的動作冒險天花板。關卡設計精妙絕倫且絕不重複，將射擊、解謎、格鬥與感人的夫妻婚姻故事完美結合，必玩神作。",
        "Euro Truck Simulator 2（歐洲卡車模擬 2）": "極致放鬆的駕駛模擬遊戲。扮演卡車司機穿梭在寫實的歐洲各大城市間，一邊欣賞沿途風景、收聽電台，一邊建立自己的物流帝國。",
        "Lethal Company（致命公司）": "極度歡樂的合作科幻恐怖遊戲。與隊友前往廢棄工業星球撿垃圾，在躲避各種詭異怪物的同時達成公司的業績指標，極度考驗溝通。物超所值。",
        "Tomb Raider Trilogy（古墓奇兵三部曲）": "經典動作冒險大作。見證蘿拉·卡芙特從青澀女孩成長為傳奇探險家的重啟三部曲，充滿精彩的遺跡解謎、荒野求生與流暢刺激的戰鬥。"
    }
    default_desc = "Steam 平台上深受好評的經典熱門大作，具備高遊戲性與龐大的社群討論度，強烈推薦加入您的願望清單！"

    visible_recommendations = st.session_state.calculated_recommendations[:st.session_state.show_count]

    # ← 改動：item 現在是 dict，拆出 game / reason / lift 三個欄位
    for idx, item in enumerate(visible_recommendations):
        game         = item["game"]
        reason_games = item.get("reason", [])
        lift_val     = item.get("lift")

        search_keyword = clean_game_name(game)
        encoded_name   = urllib.parse.quote(search_keyword)
        steam_link     = f"https://store.steampowered.com/search/?term={encoded_name}"
        desc           = game_descriptions.get(game, default_desc)

        # 有關聯規則命中：顯示「有玩過 A 的人也玩過此遊戲」；冷啟動補底：不顯示
        if reason_games and lift_val is not None:
            games_str = "、".join(reason_games)
            reason_block = (
                '<div class="association-reason">'
                f'👥 有玩過 <b>{games_str}</b> 的人，也普遍玩過此遊戲'
                '</div>'
            )
        else:
            reason_block = ""

        card_html = (
            '<div class="game-card">'
            f'<a class="game-title-link" href="{steam_link}" target="_blank">精選推薦 {idx+1:02d}：{game}</a>'
            + reason_block +
            f'<div style="color:#dcdedf;font-size:14px;margin-top:6px;line-height:1.5;"><b>遊戲簡介：</b>{desc}</div>'
            '<div class="meta-text" style="margin-top:8px;border-top:1px solid rgba(255,255,255,0.05);padding-top:4px;font-size:11px;">'
            '數據來源：Google用戶表單 及 Steam 關聯規則大數據庫庫'
            '</div>'
            '</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)

    st.write("---")
    
    btn_col1, btn_col2 = st.columns(2)
    
    with btn_col1:
        if len(st.session_state.calculated_recommendations) > st.session_state.show_count:
            st.markdown("<div class='more-btn'>", unsafe_allow_html=True)
            if st.button("以上都不喜歡，看更多推薦遊戲 (+6)"):
                st.session_state.show_count += 6
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("已為您探測完本客群大數據庫中的所有關聯大作！")
            
    with btn_col2:
        st.markdown("<div class='reset-btn'>", unsafe_allow_html=True)
        if st.button("重新進行模型分析問卷"):
            st.session_state.step = 1
            st.session_state.show_count = 6
            st.session_state.calculated_recommendations = []
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)