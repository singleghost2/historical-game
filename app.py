import streamlit as st
import sqlite3
import json
from datetime import datetime
import pydeck as pdk
import geopandas as gpd
import pandas as pd

# 初始化会话状态
if 'game_state' not in st.session_state:
    st.session_state.game_state = {
        'year': 1930,
        'month': 1,
        'military_power': 100,
        'political_power': 100,
        'economic_power': 100,
        'controlled_territories': {
            'central_government': ['jiangsu', 'zhejiang', 'anhui', 'jiangxi', 'hubei', 'hunan', 'sichuan'],
            'communist': ['jiangxi', 'fujian'],
            'japanese': []
        }
    }

# 省份数据
PROVINCES = {
    'jiangsu': {'name': '江苏', 'center': [118.8, 32.0]},
    'zhejiang': {'name': '浙江', 'center': [120.2, 30.3]},
    'anhui': {'name': '安徽', 'center': [117.3, 31.8]},
    'jiangxi': {'name': '江西', 'center': [115.9, 28.7]},
    'hubei': {'name': '湖北', 'center': [114.3, 30.6]},
    'hunan': {'name': '湖南', 'center': [112.9, 28.2]},
    'sichuan': {'name': '四川', 'center': [104.1, 30.7]},
    'fujian': {'name': '福建', 'center': [119.3, 26.1]},
    'manchuria': {'name': '东北', 'center': [125.4, 43.8]},
    'shandong': {'name': '山东', 'center': [117.0, 36.7]},
    'guangdong': {'name': '广东', 'center': [113.3, 23.1]},
    'guangxi': {'name': '广西', 'center': [108.3, 22.8]},
    'yunnan': {'name': '云南', 'center': [102.7, 25.0]},
    'guizhou': {'name': '贵州', 'center': [106.7, 26.6]},
    'shanxi': {'name': '山西', 'center': [112.6, 37.9]},
    'shaanxi': {'name': '陕西', 'center': [108.9, 34.3]},
    'gansu': {'name': '甘肃', 'center': [103.8, 36.0]},
    'qinghai': {'name': '青海', 'center': [101.8, 36.6]},
    'xinjiang': {'name': '新疆', 'center': [87.6, 43.8]},
    'taiwan': {'name': '台湾', 'center': [121.0, 23.5]}
}

# 加载中国省份地图数据
@st.cache_data
def load_province_boundaries():
    # 这里需要加载实际的地理数据文件
    # 使用 GeoJSON 格式的中国省份边界数据
    gdf = gpd.read_file("china_provinces.geojson") #TODO, 使用实际的china_provinces.geojson
    return gdf

def create_map_data():
    """创建地图数据"""
    try:
        # 加载省份边界数据
        gdf = load_province_boundaries()
        
        # 为每个省份添加颜色信息
        province_colors = []
        for _, row in gdf.iterrows():
            province_id = row['name']  # 假设GeoJSON中的属性名为'name'
            color = [100, 100, 100]  # 默认灰色
            
            # 根据控制势力设置颜色
            for faction, territories in st.session_state.game_state['controlled_territories'].items():
                if province_id in territories:
                    if faction == 'central_government':
                        color = [255, 0, 0, 140]  # 红色（半透明）
                    elif faction == 'communist':
                        color = [0, 0, 255, 140]  # 蓝色（半透明）
                    elif faction == 'japanese':
                        color = [255, 255, 0, 140]  # 黄色（半透明）
                    break
            province_colors.append(color)
        
        gdf['color'] = province_colors
        
        # 转换为pydeck可用的格式
        provinces_data = json.loads(gdf.to_json())
        return provinces_data
        
    except Exception as e:
        st.error(f"加载地图数据时出错: {str(e)}")
        return None

# 历史事件数据
HISTORICAL_EVENTS = {
    "1930": {
        "1": [
            {
                "title": "测试事件",
                "description": "这是一个测试事件，用于验证事件系统是否正常工作。",
                "choices": [
                    {
                        "text": "选择选项1",
                        "consequences": {
                            "military_power": +10,
                            "political_power": -5,
                            "economic_power": +5
                        }
                    },
                    {
                        "text": "选择选项2",
                        "consequences": {
                            "military_power": -5,
                            "political_power": +10,
                            "economic_power": -5
                        }
                    }
                ]
            }
        ]
    },
    "1931": {
        "9": [
            {
                "title": "九一八事变",
                "description": "日本关东军发动了奉天事变，意图侵占东北...",
                "choices": [
                    {
                        "text": "实行不抵抗政策",
                        "consequences": {
                            "military_power": -20,
                            "political_power": -10,
                            "territories": {
                                "japanese": ["manchuria"]
                            }
                        }
                    },
                    {
                        "text": "立即武力反击",
                        "consequences": {
                            "military_power": -30,
                            "political_power": +10
                        }
                    }
                ]
            }
        ]
    }
}

def get_current_events():
    """获取当前时间点的事件"""
    year = str(st.session_state.game_state['year'])
    month = str(st.session_state.game_state['month'])
    
    if year in HISTORICAL_EVENTS and month in HISTORICAL_EVENTS[year]:
        return HISTORICAL_EVENTS[year][month]
    return []

def process_choice(choice):
    """处理玩家的选择"""
    consequences = choice['consequences']
    
    # 更新游戏状态
    for key, value in consequences.items():
        if key == 'territories':
            # 处理领土变化
            for faction, territories in value.items():
                st.session_state.game_state['controlled_territories'][faction].extend(territories)
        elif key in st.session_state.game_state:
            st.session_state.game_state[key] += value
    
    # 推进时间
    st.session_state.game_state['month'] += 1
    if st.session_state.game_state['month'] > 12:
        st.session_state.game_state['month'] = 1
        st.session_state.game_state['year'] += 1

def reset_game():
    """重置游戏状态"""
    st.session_state.game_state = {
        'year': 1930,
        'month': 1,
        'military_power': 100,
        'political_power': 100,
        'economic_power': 100,
        'controlled_territories': {
            'central_government': ['jiangsu', 'zhejiang', 'anhui', 'jiangxi', 'hubei', 'hunan', 'sichuan'],
            'communist': ['jiangxi', 'fujian'],
            'japanese': []
        }
    }

# 设置页面标题
st.title("民国史诗 - 历史策略游戏")

# 创建两列布局
col1, col2 = st.columns([2, 1])

# 左侧列显示地图
with col1:
    st.subheader("中国地图")
    
    # 创建地图数据
    map_data = create_map_data()
    
    if map_data:
        # 创建地图层
        layer = pdk.Layer(
            'GeoJsonLayer',
            data=map_data,
            get_fill_color='color',
            get_line_color=[0, 0, 0, 255],
            get_line_width=1000,
            pickable=True,
            filled=True,
            extruded=False,
            wireframe=True
        )
        
        # 设置地图视图
        view_state = pdk.ViewState(
            latitude=35.0,
            longitude=105.0,
            zoom=3,
            pitch=0,
            bearing=0
        )
        
        # 渲染地图
        st.pydeck_chart(pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip={
                'html': '<b>省份:</b> {name}',
                'style': {
                    'color': 'white'
                }
            }
        ))
    else:
        st.error("无法加载地图数据，请确保地图数据文件存在且格式正确。")

# 右侧列显示游戏状态和事件
with col2:
    # 显示游戏状态
    st.subheader("游戏状态")
    st.write(f"年份：{st.session_state.game_state['year']}年{st.session_state.game_state['month']}月")
    st.write(f"军事力量：{st.session_state.game_state['military_power']}")
    st.write(f"政治影响：{st.session_state.game_state['political_power']}")
    st.write(f"经济实力：{st.session_state.game_state['economic_power']}")
    
    # 显示势力范围
    st.subheader("势力范围")
    for faction, territories in st.session_state.game_state['controlled_territories'].items():
        if faction == 'central_government':
            st.write("国民政府控制：")
        elif faction == 'communist':
            st.write("共产党控制：")
        elif faction == 'japanese':
            st.write("日本控制：")
        st.write(", ".join([PROVINCES[t]['name'] for t in territories]))
    
    # 重置按钮
    if st.button("重置游戏"):
        reset_game()
        st.rerun()
    
    # 显示当前事件
    st.subheader("当前事件")
    current_events = get_current_events()
    
    if current_events:
        for event in current_events:
            st.write(f"### {event['title']}")
            st.write(event['description'])
            
            # 显示选项按钮
            for choice in event['choices']:
                if st.button(choice['text']):
                    process_choice(choice)
                    st.rerun()
    else:
        st.write("当前没有事件")
        st.write("请继续推进时间，等待新的事件发生。") 