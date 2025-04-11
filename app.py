import streamlit as st
import sqlite3
import json
import os
from datetime import datetime
import pydeck as pdk
import geopandas as gpd
import pandas as pd

# 初始化会话状态
if 'game_state' not in st.session_state:
    st.session_state.game_state = {
        'military_power': 100,
        'political_power': 100,
        'economic_power': 100,
        'controlled_territories': {
            'central_government': ['江苏', '浙江', '安徽', '江西', '湖北', '湖南', '四川'],
            'communist': ['江西', '福建'],
            'japanese': []
        },
        'events': {},  # 添加events字段
        'current_event_id': None  # 添加当前事件ID字段
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

# 加载中国省份地图数据， 后续还可以加载更多的数据
@st.cache_data
def load_province_boundaries():
    # 这里需要加载实际的地理数据文件
    # 使用 GeoJSON 格式的中国省份边界数据
    gdf = gpd.read_file("china_provinces.geojson") 
    return gdf

def create_map_data():
    """创建地图数据"""
    try:
        # 加载省份边界数据
        gdf = load_province_boundaries()
        
        # 打印省份名称列表，用于调试
        st.write("地图中的省份名称：")
        st.write(gdf['name'].tolist())
        
        # 打印控制的地区列表，用于调试
        st.write("控制的地区：")
        for faction, territories in st.session_state.game_state['controlled_territories'].items():
            st.write(f"{faction}: {territories}")
        
        # 为每个省份添加颜色信息
        province_colors = []
        for _, row in gdf.iterrows():
            province_name = row['name']  # 假设GeoJSON中的属性名为'name'
            color = [100, 100, 100, 140]  # 默认灰色（半透明）
            
            # 根据控制势力设置颜色
            for faction, territories in st.session_state.game_state['controlled_territories'].items():
                if province_name in territories:
                    if faction == 'central_government':
                        color = [0, 0, 255, 140]  # 蓝色（半透明）
                    elif faction == 'communist':
                        color = [255, 0, 0, 140]  # 红色（半透明）
                    elif faction == 'japanese':
                        color = [255, 255, 0, 140]  # 黄色（半透明）
                    break
            province_colors.append(color)
        
        gdf['color'] = province_colors
        
        # 转换为pydeck可用的格式
        provinces_data = json.loads(gdf.to_json())
        
        # 创建事件地点标记
        event_locations = []
        current_events = get_current_events()
        if current_events:
            for event in current_events:
                for location in event.get('location', []):
                    if location in PROVINCES:
                        event_locations.append({
                            'name': PROVINCES[location]['name'],
                            'coordinates': PROVINCES[location]['center']
                        })
        
        return provinces_data, event_locations
        
    except Exception as e:
        st.error(f"加载地图数据时出错: {str(e)}")
        return None, None

# 历史事件数据
HISTORICAL_EVENTS = {}

def get_current_time():
    """获取当前时间"""
    if not st.session_state.game_state['current_event_id']:
        return None, None
        
    current_event = st.session_state.game_state['events']['events'].get(st.session_state.game_state['current_event_id'])
    if not current_event:
        return None, None
        
    return current_event['year'], current_event['month']

def load_event_tree(file_path):
    """加载事件树文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            event_data = json.load(f)
            
        # 根据initial_event设置当前事件
        if 'initial_event' in event_data and 'events' in event_data:
            st.session_state.game_state['current_event_id'] = event_data['initial_event']
            
        # 将事件数据保存到game_state中
        st.session_state.game_state['events'] = event_data
            
        return event_data
    except Exception as e:
        st.error(f"加载事件树文件时出错: {str(e)}")
        return None

def get_current_events():
    """获取当前时间点的事件"""
    # 如果没有当前事件ID，返回空列表
    if not st.session_state.game_state['current_event_id']:
        return []
        
    # 从事件树中获取当前事件
    current_event = st.session_state.game_state['events']['events'].get(st.session_state.game_state['current_event_id'])
    if not current_event:
        return []
        
    return [{
        'title': current_event['title'],
        'description': current_event['description'],
        'location': current_event.get('location', []),
        'choices': current_event['choices']
    }]

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
    
    # 如果选项中有next_event，直接跳转到该事件
    if 'next_event' in choice and choice['next_event']:
        st.session_state.game_state['current_event_id'] = choice['next_event']
    else:
        # 如果没有下一个事件，查找下一个最近的事件
        next_event = None
        min_time_diff = float('inf')
        current_year, current_month = get_current_time()
        
        for event_id, event in st.session_state.game_state['events']['events'].items():
            event_time = event['year'] * 12 + event['month']
            current_time = current_year * 12 + current_month
            time_diff = event_time - current_time
            
            if time_diff > 0 and time_diff < min_time_diff:
                min_time_diff = time_diff
                next_event = event_id
        
        if next_event:
            st.session_state.game_state['current_event_id'] = next_event
        else:
            st.session_state.game_state['current_event_id'] = None

def reset_game():
    """重置游戏状态"""
    st.session_state.game_state = {
        'military_power': 100,
        'political_power': 100,
        'economic_power': 100,
        'controlled_territories': {
            'central_government': ['jiangsu', 'zhejiang', 'anhui', 'jiangxi', 'hubei', 'hunan', 'sichuan'],
            'communist': ['jiangxi', 'fujian'],
            'japanese': []
        },
        'events': {},  # 添加events字段
        'current_event_id': None  # 添加当前事件ID字段
    }

# 设置页面标题
st.title("民国史诗 - 历史策略游戏")

# 创建事件树选择区域
st.sidebar.title("事件树选择")

# 获取events文件夹中的所有json文件
event_files = [f for f in os.listdir("events") if f.endswith(".json")]

if event_files:
    selected_file = st.sidebar.selectbox(
        "选择事件树",
        options=event_files,
        format_func=lambda x: x.replace(".json", "")
    )
    
    if st.sidebar.button("加载事件树"):
        file_path = os.path.join("events", selected_file)
        loaded_events = load_event_tree(file_path)
        if loaded_events:
            st.session_state.game_state['events'] = loaded_events
            st.sidebar.success(f"已加载事件树：{selected_file}")
            st.rerun()
else:
    st.sidebar.info("events文件夹下暂无事件树文件")

# 创建两列布局
col1, col2 = st.columns([2, 1])

# 左侧列显示地图
with col1:
    st.subheader("中国地图")
    
    # 创建地图数据
    map_data, event_locations = create_map_data()
    
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
            wireframe=False,
            opacity=0.8
        )
        
        # 创建事件地点标记层
        if event_locations:
            marker_layer = pdk.Layer(
                'ScatterplotLayer',
                data=event_locations,
                get_position='coordinates',
                get_fill_color=[255, 0, 0],  # 红色标记
                get_radius=100000,  # 标记大小
                pickable=True,
                opacity=0.8
            )
            layers = [layer, marker_layer]
        else:
            layers = [layer]
        
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
            layers=layers,
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
    current_year, current_month = get_current_time()
    if current_year and current_month:
        st.write(f"年份：{current_year}年{current_month}月")
    else:
        st.write("当前没有事件")
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
        st.write(", ".join(territories))
    
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
