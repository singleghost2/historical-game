import traceback
import streamlit as st
import json
import os
import graphviz
from openai import OpenAI
from config import LLM_CONFIG

# 设置页面为宽屏模式
st.set_page_config(layout="wide")

# 配置OpenAI客户端
client = OpenAI(
    base_url=LLM_CONFIG["api_base"],
    api_key=LLM_CONFIG["api_key"]
)

def load_events():
    """加载事件数据"""
    try:
        with open('events.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"events": {}, "initial_event": None}

def save_events(events_data):
    """保存事件数据"""
    with open('events.json', 'w', encoding='utf-8') as f:
        json.dump(events_data, f, ensure_ascii=False, indent=4)

def create_new_event():
    """创建新事件的默认结构"""
    return {
        "id": "",
        "title": "",
        "description": "",
        "year": 1930,
        "month": 1,
        "choices": []
    }

def create_new_choice():
    """创建新选项的默认结构"""
    return {
        "id": "",
        "text": "",
        "consequences": {
            "military_power": 0,
            "political_power": 0,
            "economic_power": 0,
            "territories": {}
        },
        "next_event": None
    }

def create_event_graph(events_data):
    """创建事件关系图"""
    try:
        dot = graphviz.Digraph(comment='事件树')
        dot.attr(rankdir='TB')  # 从上到下布局
        dot.attr('node', shape='box', style='rounded')
        
        # 添加所有事件节点
        for event_id, event in events_data['events'].items():
            # 设置节点样式
            if event_id == events_data['initial_event']:
                dot.node(event_id, f"{event['title']}\n({event['year']}年{event['month']}月)", 
                        style='filled', fillcolor='lightblue')
            else:
                dot.node(event_id, f"{event['title']}\n({event['year']}年{event['month']}月)")
        
        # 添加事件之间的连接
        for event_id, event in events_data['events'].items():
            for option in event['choices']:
                if option['next_event']:
                    dot.edge(event_id, option['next_event'], label=option['text'])
        
        # 使用二进制模式获取输出
        svg_data = dot.pipe(format='svg')
        return svg_data.decode('utf-8', errors='replace')
    except Exception as e:
        st.error(f"生成事件树时出错: {str(e)}")
        return None

import pysnooper 

def generate_events_from_text(text):
    """使用大模型根据文本生成事件树"""
    try:
        # 构建提示词
        prompt = f"""
        请根据以下历史事件描述，生成一个事件树结构。每个事件应该包含：
        1. 事件ID（格式：event_X）
        2. 事件标题
        3. 事件描述
        4. 发生年份和月份
        5. 1-2个选项，每个选项包含：
           - 选项文本
           - 军事、政治、经济影响
           - 后续事件ID
        
        请以JSON格式输出，格式如下：
        {{
            "events": {{
                "event_1": {{
                    "id": "event_1",
                    "title": "事件标题",
                    "description": "事件描述",
                    "year": 1930,
                    "month": 1,
                    "choices": [
                        {{
                            "id": "choice_1",
                            "text": "选项文本",
                            "consequences": {{
                                "military_power": 10,
                                "political_power": -5,
                                "economic_power": 0,
                                "territories": {{}}
                            }},
                            "next_event": "event_2"
                        }},
                        {{
                            "id": "choice_2",
                            "text": "另一个选项文本",
                            "consequences": {{
                                "military_power": -5,
                                "political_power": 10,
                                "economic_power": 5,
                                "territories": {{}}
                            }},
                            "next_event": "event_3"
                        }}
                    ]
                }},
                "event_2": {{
                    "id": "event_2",
                    "title": "后续事件标题",
                    "description": "后续事件描述",
                    "year": 1930,
                    "month": 2,
                    "choices": [
                        {{
                            "id": "choice_3",
                            "text": "选项文本",
                            "consequences": {{
                                "military_power": 0,
                                "political_power": 0,
                                "economic_power": 0,
                                "territories": {{}}
                            }},
                            "next_event": "event_4"
                        }}
                    ]
                }},
                "event_3": {{
                    "id": "event_3",
                    "title": "另一个后续事件标题",
                    "description": "另一个后续事件描述",
                    "year": 1930,
                    "month": 2,
                    "choices": [
                        {{
                            "id": "choice_4",
                            "text": "选项文本",
                            "consequences": {{
                                "military_power": 0,
                                "political_power": 0,
                                "economic_power": 0,
                                "territories": {{}}
                            }},
                            "next_event": "event_4"
                        }}
                    ]
                }},
                "event_4": {{
                    "id": "event_4",
                    "title": "最终事件标题",
                    "description": "最终事件描述",
                    "year": 1930,
                    "month": 3,
                    "choices": []
                }}
            }},
            "initial_event": "event_1"
        }}

        注意事项：
        1. 每个事件都应该有唯一的ID
        2. 选项的next_event必须指向已存在的事件ID
        3. 事件之间应该形成合理的时间顺序
        4. 不同选项可能导致不同的事件分支
        5. 最终事件（没有后续事件的事件）的choices应该为空数组
        6. 所有事件都应该通过选项连接起来，不能有孤立的事件
        7. 军事、政治、经济影响的数值范围在-20到20之间
        8. 事件的时间顺序要合理，后续事件的年月不能早于前导事件
        9. 每个事件最多可以有3个选项

        历史事件描述：
        {text}
        """
        
        # 调用大模型API
        response = client.chat.completions.create(
            model=LLM_CONFIG["model"],
            messages=[
                {"role": "system", "content": "你是一个历史事件分析专家，擅长将历史事件转化为结构化的事件树。你需要确保生成的事件树具有合理的时间顺序和因果关系。"},
                {"role": "user", "content": prompt}
            ],
            temperature=LLM_CONFIG["temperature"],
            max_tokens=LLM_CONFIG["max_tokens"],
            stream=True  # 启用流式输出
        )
        
        # 逐步输出生成的内容
        full_response = ""
        output_placeholder = st.empty()  # 创建一个占位符
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                chunk_message = chunk.choices[0].delta.content
                full_response += chunk_message
                output_placeholder.markdown(full_response)  # 更新占位符内容
        
        # 解析生成的JSON
        generated_events = json.loads(full_response)
    except Exception as e:
        traceback.print_exc()
        st.error(f"生成事件树时出错: {str(e)}")
        return None

# 加载事件数据
if 'events_data' not in st.session_state:
    st.session_state.events_data = load_events()

# 确保所有选项都有完整的consequences结构
for event in st.session_state.events_data["events"].values():
    for choice in event["choices"]:
        if "consequences" not in choice:
            choice["consequences"] = {
                "military_power": 0,
                "political_power": 0,
                "economic_power": 0,
                "territories": {}
            }
        else:
            for key in ["military_power", "political_power", "economic_power"]:
                if key not in choice["consequences"]:
                    choice["consequences"][key] = 0
            if "territories" not in choice["consequences"]:
                choice["consequences"]["territories"] = {}

# 页面标题
st.title("民国史诗 - 事件编辑器")

# 添加自动生成事件树的输入框和按钮
with st.expander("自动生成事件树", expanded=False):
    input_text = st.text_area("请输入历史事件描述：", height=200)
    if st.button("生成事件树"):
        if input_text:
            with st.spinner("正在生成事件树..."):
                generated_events = generate_events_from_text(input_text)
                if generated_events:
                    st.session_state.events_data = generated_events
                    save_events(st.session_state.events_data)
                    st.success("事件树生成成功！")
                    st.rerun()
        else:
            st.warning("请输入历史事件描述")

# 创建三列布局
col1, col2, col3 = st.columns([1, 1, 1])

# 左侧列：事件列表和基本操作
with col1:
    st.subheader("事件列表")
    
    # 添加新事件按钮
    if st.button("添加新事件"):
        new_event = create_new_event()
        st.session_state.events_data["events"][f"new_event_{len(st.session_state.events_data['events'])}"] = new_event
        save_events(st.session_state.events_data)
    
    # 选择要编辑的事件
    selected_event = st.selectbox(
        "选择事件",
        options=list(st.session_state.events_data["events"].keys()),
        format_func=lambda x: st.session_state.events_data["events"][x]["title"] or x,
        key="event_selector"
    )
    
    # 设置初始事件
    st.subheader("初始事件设置")
    initial_event = st.selectbox(
        "选择初始事件",
        options=list(st.session_state.events_data["events"].keys()),
        index=list(st.session_state.events_data["events"].keys()).index(st.session_state.events_data["initial_event"]) if st.session_state.events_data["initial_event"] else 0
    )
    if initial_event != st.session_state.events_data["initial_event"]:
        st.session_state.events_data["initial_event"] = initial_event
        save_events(st.session_state.events_data)

# 中间列：事件编辑
with col2:
    if selected_event:
        st.subheader("事件编辑")
        event = st.session_state.events_data["events"][selected_event]
        
        # 基本信息编辑
        new_id = st.text_input("事件ID", event["id"])
        new_title = st.text_input("事件标题", event["title"])
        new_description = st.text_area("事件描述", event["description"])
        new_year = st.number_input("发生年份", min_value=1930, max_value=1940, value=event["year"])
        new_month = st.number_input("发生月份", min_value=1, max_value=12, value=event["month"])
        
        # 选项编辑
        st.subheader("选项编辑")
        for i, choice in enumerate(event["choices"]):
            st.write(f"选项 {i+1}")
            col_id, col_text = st.columns([1, 2])
            with col_id:
                choice["id"] = st.text_input(f"选项ID###{i}", choice["id"])
            with col_text:
                choice["text"] = st.text_input(f"选项文本###{i}", choice["text"])
            
            # 后果编辑
            st.write("选项后果")
            col_m, col_p, col_e = st.columns(3)
            with col_m:
                choice["consequences"]["military_power"] = st.number_input(
                    f"军事力量变化###{i}",
                    value=choice["consequences"]["military_power"]
                )
            with col_p:
                choice["consequences"]["political_power"] = st.number_input(
                    f"政治影响变化###{i}",
                    value=choice["consequences"]["political_power"]
                )
            with col_e:
                choice["consequences"]["economic_power"] = st.number_input(
                    f"经济实力变化###{i}",
                    value=choice["consequences"]["economic_power"]
                )
            
            # 后续事件
            available_events = list(st.session_state.events_data["events"].keys())
            choice["next_event"] = st.selectbox(
                f"后续事件###{i}",
                options=["无"] + available_events,
                index=0 if not choice["next_event"] else available_events.index(choice["next_event"]) + 1
            )
            if choice["next_event"] == "无":
                choice["next_event"] = None
            
            # 删除选项按钮
            if st.button(f"删除选项###{i}"):
                event["choices"].pop(i)
                save_events(st.session_state.events_data)
                st.rerun()
        
        # 添加新选项按钮
        if st.button("添加新选项"):
            event["choices"].append(create_new_choice())
            save_events(st.session_state.events_data)
            st.rerun()
        
        # 更新事件数据
        if st.button("保存事件"):
            # 如果ID发生变化，需要重新创建事件
            if new_id != event["id"] and new_id:
                st.session_state.events_data["events"][new_id] = st.session_state.events_data["events"].pop(selected_event)
                selected_event = new_id
            
            event = st.session_state.events_data["events"][selected_event]
            event.update({
                "id": new_id,
                "title": new_title,
                "description": new_description,
                "year": new_year,
                "month": new_month
            })
            
            save_events(st.session_state.events_data)
            st.success("事件已保存！")
        
        # 删除事件按钮
        if st.button("删除事件"):
            del st.session_state.events_data["events"][selected_event]
            if st.session_state.events_data["initial_event"] == selected_event:
                st.session_state.events_data["initial_event"] = None
            save_events(st.session_state.events_data)
            st.rerun()

# 右侧列：事件树可视化
with col3:
    st.subheader("事件树可视化")
    if st.session_state.events_data["events"]:
        try:
            graph_svg = create_event_graph(st.session_state.events_data)
            if graph_svg:
                # 使用HTML组件显示SVG，并添加点击事件
                st.components.v1.html(f"""
                    <div id="event-graph" style="width: 100%; height: 600px; overflow: auto;">
                        {graph_svg}
                    </div>
                    <script>
                        document.querySelectorAll('#event-graph g.node').forEach(node => {{
                            node.style.cursor = 'pointer';
                            node.addEventListener('click', function() {{
                                const eventId = this.querySelector('title').textContent;
                                const select = document.querySelector('select[aria-label="选择事件"]');
                                if (select) {{
                                    select.value = eventId;
                                    select.dispatchEvent(new Event('change'));
                                }}
                            }});
                        }});
                    </script>
                """, height=600)
        except Exception as e:
            st.error(f"生成事件树时出错: {str(e)}")
    else:
        st.info("暂无事件数据，请添加事件。")
