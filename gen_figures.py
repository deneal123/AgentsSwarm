"""
Генератор диаграмм для диссертации AgentsSwarm.
Запуск: python gen_figures.py
Выходные файлы: img/fig_*.png (300 dpi)

DEPRECATED: актуальные схемы хранятся в mmd/fig_*.mmd и рендерятся через
Mermaid CLI. Этот старый Matplotlib-генератор оставлен только как архивный
черновик и не должен перезаписывать финальные PNG.
"""
raise SystemExit(
    "gen_figures.py is deprecated. Render mmd/fig_*.mmd with Mermaid CLI "
    "using mmdc-puppeteer.json; keep fig_3_2/fig_3_9/fig_3_10 as manual screenshots."
)

import os
import textwrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe

OUT = "img"
os.makedirs(OUT, exist_ok=True)

# ── Цветовая схема из кодовой базы ─────────────────────────────────────────
C_USER   = '#ff6b6b'
C_ORCH   = '#ffa500'
C_AGENT  = '#52c41a'
C_MISS   = '#4a9eff'
C_VLLM   = '#9b59b6'
C_EXT    = '#e67e22'
C_REDIS  = '#9b59b6'
C_INFRA  = '#888888'
BG       = '#ffffff'

# ── Вспомогательные функции ────────────────────────────────────────────────
def fig_ax(w=12, h=7):
    f, a = plt.subplots(figsize=(w, h))
    a.set_xlim(0, 1); a.set_ylim(0, 1)
    a.axis('off')
    f.patch.set_facecolor(BG)
    a.set_facecolor(BG)
    return f, a

def box(ax, cx, cy, w, h, lines, color, fs=8.5, bold=False):
    """Прямоугольник с закруглёнными углами, цветная рамка, белый фон."""
    rect = FancyBboxPatch((cx - w/2, cy - h/2), w, h,
                          boxstyle="round,pad=0.012",
                          facecolor='#f8f8f8', edgecolor=color, linewidth=2)
    ax.add_patch(rect)
    text = "\n".join(lines)
    ax.text(cx, cy, text, ha='center', va='center', fontsize=fs,
            fontweight='bold' if bold else 'normal',
            multialignment='center', color='#222222')

def arr(ax, x0, y0, x1, y1, label='', color='#555555', lw=1.5,
        style='->', rad=0.0):
    """Стрелка между точками."""
    ax.annotate('', xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle=style, color=color,
                                lw=lw, connectionstyle=f'arc3,rad={rad}'))
    if label:
        mx, my = (x0+x1)/2, (y0+y1)/2
        ax.text(mx+0.01, my+0.01, label, fontsize=6.5, color='#444444',
                ha='left', va='bottom')

def darr(ax, x0, y0, x1, y1, label='', color='#555555'):
    """Двунаправленная стрелка."""
    arr(ax, x0, y0, x1, y1, label, color, style='<->')

def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=300, bbox_inches='tight', facecolor=BG)
    plt.close(fig)
    print(f"  saved: {path}")


# ══════════════════════════════════════════════════════════════════════════════
#  РИС. 2.1 — Общая схема взаимодействия компонентов системы AgentsSwarm
# ══════════════════════════════════════════════════════════════════════════════
def fig_2_1():
    f, a = fig_ax(13, 7)
    a.set_title("Рис. 2.1. Общая схема взаимодействия компонентов AgentsSwarm",
                fontsize=10, pad=8)

    # Column x-coords: 0.08  0.28  0.50  0.72  0.92
    # Row y-coords:    0.82  0.58  0.34  0.10

    # Пользователь
    box(a, 0.14, 0.82, 0.18, 0.10, ['Пользователь'], C_USER, bold=True)

    # Interface
    box(a, 0.14, 0.60, 0.20, 0.12,
        ['Interface', 'React + FastAPI + Celery', 'RabbitMQ + Redis + MinIO'], C_USER)

    # Orchestrator
    box(a, 0.44, 0.60, 0.20, 0.12,
        ['Orchestrator', 'FastAPI + Agents SDK', '9 специализированных агентов'], C_ORCH)

    # vLLM Service
    box(a, 0.44, 0.82, 0.20, 0.10,
        ['vLLM Service', 'Data Parallel · 2×V100'], C_VLLM)

    # MCP Servers
    box(a, 0.44, 0.35, 0.22, 0.12,
        ['MCP-серверы (×3)', 'mission-control :8010', 'mission-dispatch :8011',
         'ros-msp :8012'], C_REDIS)

    # Mission Control
    box(a, 0.72, 0.60, 0.20, 0.12,
        ['Mission Control', '(форк NVIDIA)', 'Behavior Tree · cuOpt'], C_MISS)

    # Mission Dispatch
    box(a, 0.72, 0.38, 0.20, 0.10,
        ['Mission Dispatch', '(форк NVIDIA)', 'VDA5050 очередь + MQTT'], C_MISS)

    # Isaac Sim + ROS2
    box(a, 0.72, 0.15, 0.22, 0.12,
        ['Isaac Sim + ROS 2', 'Carter Fleet · headless', 'rosbridge WebSocket'], C_AGENT)

    # SmolVLA Tools
    box(a, 0.88, 0.82, 0.18, 0.10,
        ['SmolVLA Tools', 'Эксп. модуль'], C_INFRA)

    # ─── Стрелки ───────────────────────────────────────────────────────────
    arr(a, 0.14, 0.77, 0.14, 0.66, 'запрос', C_USER)
    arr(a, 0.24, 0.60, 0.34, 0.60, 'POST /task\nWS events', C_USER)
    arr(a, 0.44, 0.77, 0.44, 0.66, 'OpenAI API', C_VLLM)
    arr(a, 0.44, 0.54, 0.44, 0.41, 'HTTP / MCP', C_ORCH)
    arr(a, 0.55, 0.60, 0.62, 0.60, 'HTTP', C_ORCH)
    arr(a, 0.55, 0.55, 0.63, 0.42, 'HTTP', C_ORCH)
    darr(a, 0.72, 0.54, 0.72, 0.43, 'VDA5050', C_MISS)
    arr(a, 0.72, 0.33, 0.72, 0.21, 'VDA5050\norder', C_MISS)
    arr(a, 0.44, 0.29, 0.61, 0.19, 'ROS2\ntopics', C_REDIS)

    # легенда
    handles = [
        mpatches.Patch(facecolor='#f8f8f8', edgecolor=C_USER,   lw=2, label='Пользователь / Interface'),
        mpatches.Patch(facecolor='#f8f8f8', edgecolor=C_ORCH,   lw=2, label='Orchestrator'),
        mpatches.Patch(facecolor='#f8f8f8', edgecolor=C_VLLM,   lw=2, label='vLLM Service'),
        mpatches.Patch(facecolor='#f8f8f8', edgecolor=C_REDIS,  lw=2, label='MCP-серверы / Redis'),
        mpatches.Patch(facecolor='#f8f8f8', edgecolor=C_MISS,   lw=2, label='Mission Control/Dispatch'),
        mpatches.Patch(facecolor='#f8f8f8', edgecolor=C_AGENT,  lw=2, label='Isaac Sim / ROS 2'),
    ]
    a.legend(handles=handles, loc='lower left', fontsize=7,
             framealpha=0.9, ncol=2)
    save(f, "fig_2_1_system_overview.png")


# ══════════════════════════════════════════════════════════════════════════════
#  РИС. 2.2 — Три MCP-сервера и зоны ответственности
# ══════════════════════════════════════════════════════════════════════════════
def fig_2_2():
    f, a = fig_ax(12, 5.5)
    a.set_title("Рис. 2.2. Три MCP-сервера: зоны ответственности и транспорт",
                fontsize=10, pad=8)

    # Orchestrator слева
    box(a, 0.10, 0.50, 0.14, 0.28,
        ['Orchestrator', 'Agents SDK', 'MCP-клиент'], C_ORCH, bold=True)

    # MCP серверы — три колонки
    box(a, 0.35, 0.72, 0.20, 0.14,
        ['mission-control-mcp', 'порт :8010', 'get_map · get_waypoints',
         'get_robot_status · list_robots'], C_REDIS)
    box(a, 0.35, 0.50, 0.20, 0.14,
        ['mission-dispatch-mcp', 'порт :8011', 'create_mission',
         'cancel_mission · get_status'], C_REDIS)
    box(a, 0.35, 0.28, 0.20, 0.14,
        ['ros-msp', 'порт :8012', 'publish_topic · read_topic',
         'get_topic_list'], C_REDIS)

    # Транспорт (SSE / stdio)
    box(a, 0.60, 0.50, 0.14, 0.22,
        ['Транспорт', 'SSE', '(HTTP)', '— или —', 'stdio'], '#888888')

    # Бэкенды
    box(a, 0.83, 0.72, 0.22, 0.12,
        ['Mission Control API', ':8050', 'Behavior Tree · cuOpt'], C_MISS)
    box(a, 0.83, 0.50, 0.22, 0.12,
        ['Mission Dispatch API', ':8052', 'VDA5050 очередь + MQTT'], C_MISS)
    box(a, 0.83, 0.28, 0.22, 0.12,
        ['rosbridge WebSocket', ':9090', 'ROS 2 топики / сервисы'], C_AGENT)

    # Стрелки Orchestrator → MCP
    for y in [0.72, 0.50, 0.28]:
        arr(a, 0.17, 0.50, 0.25, y, '', C_ORCH)
    # MCP → транспорт → бэкенды
    for y in [0.72, 0.50, 0.28]:
        arr(a, 0.45, y, 0.53, 0.50, '', C_REDIS)
        arr(a, 0.67, 0.50, 0.72, y, '', '#888888')

    a.text(0.47, 0.04,
           'MCP_TRANSPORT=sse → HTTP Server-Sent Events  |  MCP_TRANSPORT=stdio → локальный процесс',
           ha='center', fontsize=8, color='#555555', style='italic')
    save(f, "fig_2_2_mcp_servers.png")


# ══════════════════════════════════════════════════════════════════════════════
#  РИС. 2.3 — Маршрут команды: Orchestrator → VDA5050 → робот
# ══════════════════════════════════════════════════════════════════════════════
def fig_2_3():
    f, a = fig_ax(14, 4.0)
    a.set_title("Рис. 2.3. Маршрут команды от оркестратора до робота в Isaac Sim",
                fontsize=10, pad=8)

    steps = [
        (0.06, 'Orchestrator\n(MissionPlanner)', C_ORCH),
        (0.21, 'MCP-сервер\nmission-dispatch-mcp', C_REDIS),
        (0.36, 'Mission Dispatch\nAPI :8052', C_MISS),
        (0.50, 'MQTT-брокер\n(Mosquitto)', C_EXT),
        (0.64, 'VDA5050\nклиент робота', C_AGENT),
        (0.79, 'ROS 2\nNavigator', C_AGENT),
        (0.94, 'Isaac Sim\nCarter', C_AGENT),
    ]
    labels = [
        'HTTP / MCP', 'HTTP', 'MQTT\norder', 'VDA5050', 'ROS 2\nnav2', 'action'
    ]

    for i, (x, text, color) in enumerate(steps):
        box(a, x, 0.55, 0.12, 0.28, text.split('\n'), color, fs=8)
    for i in range(len(steps)-1):
        arr(a, steps[i][0]+0.06, 0.55, steps[i+1][0]-0.06, 0.55,
            labels[i] if i < len(labels) else '', '#555555')

    # Ответный путь (snipped)
    a.annotate('', xy=(0.36, 0.22), xytext=(0.64, 0.22),
               arrowprops=dict(arrowstyle='<-', color='#aaaaaa',
                               lw=1.2, linestyle='dashed'))
    a.text(0.50, 0.14, 'state (статус робота)', ha='center', fontsize=7.5,
           color='#888888', style='italic')
    save(f, "fig_2_3_command_route.png")


# ══════════════════════════════════════════════════════════════════════════════
#  РИС. 2.4 — Иерархия агентов оркестратора
# ══════════════════════════════════════════════════════════════════════════════
def fig_2_4():
    f, a = fig_ax(13, 6.5)
    a.set_title("Рис. 2.4. Иерархия агентов оркестратора AgentsSwarm",
                fontsize=10, pad=8)

    # Pipeline (верхний уровень)
    box(a, 0.50, 0.90, 0.22, 0.10,
        ['Pipeline', 'Planner → PlanRunner'], C_ORCH, bold=True)

    # Router
    box(a, 0.50, 0.73, 0.22, 0.10,
        ['Router Agent', 'классификация · handoff'], C_ORCH)

    # MapAnalyst (справа от Pipeline)
    box(a, 0.85, 0.90, 0.20, 0.10,
        ['MapAnalyst', 'vision-LLM · карта'], C_MISS)

    # 8 специализированных агентов в два ряда
    agents_row1 = [
        (0.10, 'Navigation\nнавигация к точке'),
        (0.26, 'Charging\nзарядка · докинг'),
        (0.42, 'Patrol\nпатрульный\nмаршрут'),
        (0.58, 'Inspection\nинспекция\nобъектов'),
    ]
    agents_row2 = [
        (0.18, 'FleetOps\nоперации флота\nаналитика'),
        (0.38, 'SwarmCoordinator\nпараллельная\nкоординация'),
        (0.58, 'RobotInfo\nстатус · батарея\nпозиция'),
        (0.78, 'General\nобщий чат\n(fallback)'),
    ]

    for x, text in agents_row1:
        box(a, x, 0.50, 0.14, 0.16, text.split('\n'), C_AGENT, fs=7.5)
        arr(a, 0.50, 0.68, x, 0.58, '', C_ORCH)

    for x, text in agents_row2:
        box(a, x, 0.25, 0.15, 0.16, text.split('\n'), C_AGENT, fs=7.5)
        arr(a, 0.50, 0.68, x, 0.33, '', C_ORCH)

    # Pipeline → Router
    arr(a, 0.50, 0.85, 0.50, 0.78, 'запрос', C_ORCH)
    # Pipeline → MapAnalyst
    arr(a, 0.61, 0.90, 0.75, 0.90, 'анализ\nкарты', C_ORCH)

    # MCP-серверы внизу
    box(a, 0.50, 0.06, 0.40, 0.08,
        ['MCP-серверы: mission-control-mcp · mission-dispatch-mcp · ros-msp'], C_REDIS, fs=7.5)
    for x, _ in agents_row1 + agents_row2:
        arr(a, x, 0.17, 0.50, 0.10, '', '#cccccc')

    a.text(0.50, -0.02,
           'Handoff через OpenAI Agents SDK  ·  Guardrails на входе и выходе',
           ha='center', fontsize=7.5, color='#666666', style='italic')
    save(f, "fig_2_4_agents.png")


# ══════════════════════════════════════════════════════════════════════════════
#  РИС. 2.5 — Жизненный цикл задачи и потоковая модель событий
# ══════════════════════════════════════════════════════════════════════════════
def fig_2_5():
    f, a = fig_ax(13, 5.5)
    a.set_title("Рис. 2.5. Жизненный цикл задачи и потоковая модель событий",
                fontsize=10, pad=8)

    # Состояния задачи (верхняя полоса)
    states = [
        (0.10, 'pending', '#cccccc'),
        (0.28, 'running', C_ORCH),
        (0.46, 'streaming\n(stream_chunk)', C_AGENT),
        (0.64, 'completed', C_MISS),
        (0.82, 'error', C_USER),
    ]
    for x, label, c in states:
        box(a, x, 0.80, 0.14, 0.12, label.split('\n'), c, fs=8.5)
    for i in range(len(states)-1):
        ax0, ax1 = states[i][0]+0.07, states[i+1][0]-0.07
        if i == 2:  # from streaming: two branches
            break
        arr(a, ax0, 0.80, ax1, 0.80, '', '#555555')
    arr(a, 0.35, 0.80, 0.39, 0.80, '', '#555555')
    arr(a, 0.53, 0.80, 0.57, 0.80, '', '#555555')

    # Redis Stream (центр)
    box(a, 0.50, 0.48, 0.36, 0.14,
        ['Redis Stream', 'chat:{thread_id}:stream', 'XADD (агент) → XREAD (WebSocket)'], C_REDIS, fs=8)

    # Агент → Redis
    box(a, 0.18, 0.48, 0.22, 0.14,
        ['Celery Worker', 'AgentExecutionService', 'XADD events'], C_ORCH)
    arr(a, 0.29, 0.48, 0.32, 0.48, 'XADD', C_ORCH)

    # Redis → WebSocket
    box(a, 0.82, 0.48, 0.22, 0.14,
        ['WebSocket Layer', 'XREAD · heartbeat', 'push → клиент'], C_ORCH)
    arr(a, 0.68, 0.48, 0.71, 0.48, 'XREAD', C_REDIS)

    # Типы событий
    event_types = [
        'stream_chunk', 'agent_reply', 'routing_event', 'tool_event', 'error'
    ]
    a.text(0.50, 0.30, 'Типы событий: ' + '  ·  '.join(event_types),
           ha='center', fontsize=8, color='#444444')

    # Оркестратор (отдельный канал)
    box(a, 0.18, 0.12, 0.22, 0.12,
        ['SwarmOrchestratorAgent', 'WebSocket :8000', '/ws/task/{id}'], C_MISS)
    arr(a, 0.29, 0.12, 0.32, 0.41, 'события\nоркестратора', C_MISS, rad=0.15)

    save(f, "fig_2_5_task_lifecycle.png")


# ══════════════════════════════════════════════════════════════════════════════
#  РИС. 3.1 — Isaac Sim + ROS 2: схема интеграции
# ══════════════════════════════════════════════════════════════════════════════
def fig_3_1():
    f, a = fig_ax(12, 5.5)
    a.set_title("Рис. 3.1. Схема интеграции Isaac Sim и ROS 2 с контуром управления",
                fontsize=10, pad=8)

    # Isaac Sim
    box(a, 0.15, 0.65, 0.22, 0.14,
        ['NVIDIA Isaac Sim', 'headless · Web Viewer :8211', 'Carter Warehouse сцена'], C_AGENT, bold=True)
    box(a, 0.15, 0.40, 0.22, 0.14,
        ['Action Graph', 'RGB / depth камеры', 'namespace: /carter_{N}'], C_AGENT)

    # ROS2
    box(a, 0.43, 0.65, 0.22, 0.14,
        ['ROS 2 Jazzy', 'DDS bridge', 'isaac_ros_common'], '#1890ff')
    box(a, 0.43, 0.40, 0.22, 0.14,
        ['isaac_ros_mission_client', 'VDA5050 клиент', '/vda5050/{robot}/order'], C_AGENT)
    box(a, 0.43, 0.15, 0.22, 0.14,
        ['rosbridge WebSocket', ':9090', 'REST-доступ к топикам'], '#1890ff')

    # Mission Control
    box(a, 0.72, 0.65, 0.22, 0.14,
        ['Mission Control', ':8050', 'Behavior Tree · cuOpt'], C_MISS)
    box(a, 0.72, 0.40, 0.22, 0.14,
        ['Occupancy Map\n+ Waypoint Graph', 'PNG → /map/update_robot', 'cuOpt маршруты'], C_MISS)

    # ros-msp (MCP)
    box(a, 0.72, 0.15, 0.22, 0.14,
        ['ros-msp (MCP)', ':8012', 'publish/read\nROS2 топики'], C_REDIS)

    # Стрелки
    arr(a, 0.15, 0.58, 0.15, 0.47, '', C_AGENT)
    arr(a, 0.26, 0.65, 0.32, 0.65, 'ROS 2\nnamespace', C_AGENT)
    arr(a, 0.26, 0.40, 0.32, 0.40, 'VDA5050', C_AGENT)
    arr(a, 0.26, 0.40, 0.32, 0.15, '', C_AGENT)
    arr(a, 0.54, 0.65, 0.61, 0.65, 'API', '#1890ff')
    arr(a, 0.54, 0.65, 0.61, 0.40, 'map', '#1890ff')
    darr(a, 0.54, 0.40, 0.61, 0.40, 'order/state', '#1890ff')
    arr(a, 0.54, 0.15, 0.61, 0.15, 'WS connect', '#1890ff')
    arr(a, 0.72, 0.58, 0.72, 0.47, '', C_MISS)

    save(f, "fig_3_1_isaac_ros.png")


# ══════════════════════════════════════════════════════════════════════════════
#  РИС. 3.3 — Динамический выбор транспорта MCP
# ══════════════════════════════════════════════════════════════════════════════
def fig_3_3():
    f, a = fig_ax(11, 5)
    a.set_title("Рис. 3.3. Динамический выбор транспорта MCP через MCP_TRANSPORT",
                fontsize=10, pad=8)

    # Переменная окружения
    box(a, 0.50, 0.82, 0.30, 0.10,
        ['MCP_TRANSPORT', '(переменная окружения)'], '#888888', bold=True)

    # Два варианта
    box(a, 0.25, 0.55, 0.28, 0.18,
        ['MCP_TRANSPORT=sse', 'HTTP Server (FastMCP)', 'Bind: 0.0.0.0:{port}',
         'Production / Docker'], C_MISS)
    box(a, 0.75, 0.55, 0.28, 0.18,
        ['MCP_TRANSPORT=stdio', 'Локальный процесс', 'stdin / stdout потоки',
         'Тестирование / debug'], C_AGENT)

    arr(a, 0.37, 0.82, 0.32, 0.64, 'sse', C_MISS)
    arr(a, 0.63, 0.82, 0.68, 0.64, 'stdio', C_AGENT)

    # Единый код сервера
    box(a, 0.50, 0.22, 0.50, 0.14,
        ['Единый код MCP-сервера (server.py)',
         'async def tool_name() — идентичен для обоих режимов',
         'async with SseServer() / stdio_server() — выбор в main()'], '#555555')

    arr(a, 0.25, 0.46, 0.35, 0.29, '', C_MISS)
    arr(a, 0.75, 0.46, 0.65, 0.29, '', C_AGENT)

    save(f, "fig_3_3_mcp_transport.png")


# ══════════════════════════════════════════════════════════════════════════════
#  РИС. 3.4 — vLLM Data Parallel: координатор + воркер
# ══════════════════════════════════════════════════════════════════════════════
def fig_3_4():
    f, a = fig_ax(11, 5.5)
    a.set_title("Рис. 3.4. Архитектура vLLM Service: Data Parallel на двух узлах",
                fontsize=10, pad=8)

    # Клиенты
    box(a, 0.50, 0.88, 0.30, 0.10,
        ['Orchestrator / Interface', 'HTTP OpenAI-compatible API'], C_ORCH)

    # Node 0
    box(a, 0.25, 0.58, 0.32, 0.20,
        ['Node 0 — Координатор (rank 0)', 'Tesla V100 · 32 ГБ VRAM',
         'vLLM :8000', 'PIPELINE_PARALLEL_SIZE=2', 'VLLM_GPU_MEMORY_UTILIZATION=0.90'], C_MISS, bold=False)

    # Node 1
    box(a, 0.75, 0.58, 0.32, 0.20,
        ['Node 1 — Воркер (rank 1)', 'Tesla V100 · 32 ГБ VRAM',
         'vLLM :8000', 'TENSOR_PARALLEL_SIZE=1', 'forward pass (replica)'], C_AGENT, bold=False)

    # RPC
    darr(a, 0.41, 0.58, 0.59, 0.58, 'gRPC · :13345\nтензоры активаций', '#555555')

    # HTTP запрос
    arr(a, 0.50, 0.83, 0.35, 0.68, 'POST /v1/chat/completions', C_ORCH)

    # Ответ
    arr(a, 0.30, 0.48, 0.40, 0.30, '', C_MISS)
    box(a, 0.50, 0.22, 0.36, 0.12,
        ['Агрегация logits → next token', 'Streaming SSE response'], C_ORCH)
    arr(a, 0.55, 0.48, 0.55, 0.28, '', C_MISS)
    arr(a, 0.55, 0.16, 0.55, 0.05, '', C_ORCH)
    box(a, 0.50, 0.02, 0.30, 0.06, ['Ответ клиенту (streaming)'], C_ORCH)

    # Параметры
    a.text(0.50, -0.04,
           'Модель: Qwen2.5-Instruct  ·  Формат: OpenAI-compatible  ·  api_key="EMPTY"',
           ha='center', fontsize=8, color='#555555', style='italic')
    save(f, "fig_3_4_vllm_dp.png")


# ══════════════════════════════════════════════════════════════════════════════
#  РИС. 3.5 — Структура FastAPI-приложения оркестратора
# ══════════════════════════════════════════════════════════════════════════════
def fig_3_5():
    f, a = fig_ax(12, 6)
    a.set_title("Рис. 3.5. Структура FastAPI-приложения оркестратора",
                fontsize=10, pad=8)

    # app.py / lifespan
    box(a, 0.50, 0.88, 0.28, 0.10, ['app.py · lifespan manager', 'FastAPI + Depends'], C_ORCH, bold=True)

    # Роутеры
    routers = [
        (0.12, '/health\n/agents'),
        (0.30, '/sessions\n/tasks'),
        (0.50, '/ws\ntask stream'),
        (0.70, 'Orchestrator\nRuntime'),
        (0.88, 'Guardrails\nвалидация'),
    ]
    for x, text in routers:
        box(a, x, 0.66, 0.14, 0.12, text.split('\n'), C_ORCH)
        arr(a, 0.50, 0.83, x, 0.72, '', C_ORCH)

    # Сервисы
    services = [
        (0.12, 0.43, 'TaskApplication\nService'),
        (0.30, 0.43, 'SessionManager\nRedis · TTL 24h'),
        (0.50, 0.43, 'StreamCollector\nseq-нумерация'),
        (0.70, 0.43, 'PlanRunner\nMissionPlanner'),
        (0.88, 0.43, 'MapAnalyst\nvision-LLM'),
    ]
    for x, y, text in services:
        box(a, x, y, 0.15, 0.12, text.split('\n'), '#1890ff')
        arr(a, x, 0.60, x, 0.49, '', C_ORCH)

    # MCP-клиенты
    box(a, 0.25, 0.20, 0.38, 0.12,
        ['MCP-клиенты', 'mission-control · mission-dispatch · ros-msp', 'AsyncClient · httpx'], C_REDIS)
    box(a, 0.75, 0.20, 0.28, 0.12,
        ['OpenAI Agents SDK', 'Runner.run_streamed()', 'handoff · guardrails'], C_VLLM)

    for x in [0.30, 0.50]:
        arr(a, x, 0.37, 0.30, 0.26, '', '#1890ff')
    for x in [0.70, 0.88]:
        arr(a, x, 0.37, 0.72, 0.26, '', '#1890ff')

    save(f, "fig_3_5_orchestrator_app.png")


# ══════════════════════════════════════════════════════════════════════════════
#  РИС. 3.6 — StreamCollector и WebSocket push
# ══════════════════════════════════════════════════════════════════════════════
def fig_3_6():
    f, a = fig_ax(12, 4.5)
    a.set_title("Рис. 3.6. StreamCollector: seq-нумерация событий и WebSocket push",
                fontsize=10, pad=8)

    nodes = [
        (0.08, 'Agents SDK\nRunner.run_streamed()', C_ORCH),
        (0.27, 'StreamCollector\nбуферизация\nseq = 1, 2, 3 …', C_ORCH),
        (0.50, 'Redis\ntask:{id}:stream\nXADD', C_REDIS),
        (0.73, 'WebSocket\n/ws/task/{id}\nXREAD (block=0)', C_ORCH),
        (0.92, 'Interface\nTracePanel\n(клиент)', C_USER),
    ]
    for x, text, c in nodes:
        box(a, x, 0.60, 0.15, 0.26, text.split('\n'), c)

    labels = ['события\n(async iter)', 'XADD\npayload+seq', 'XREAD\nstream', 'WS push\nevents']
    for i in range(len(nodes)-1):
        arr(a, nodes[i][0]+0.075, 0.60, nodes[i+1][0]-0.075, 0.60,
            labels[i], '#555555')

    # Типы событий снизу
    event_box = '\n'.join([
        'Типы событий:',
        'stream_chunk  ·  agent_reply  ·  routing_event  ·  tool_event  ·  error',
    ])
    a.text(0.50, 0.20, event_box, ha='center', fontsize=8.5, color='#333333',
           bbox=dict(boxstyle='round,pad=0.4', facecolor='#f0f0f0', edgecolor='#aaaaaa'))

    save(f, "fig_3_6_streamcollector.png")


# ══════════════════════════════════════════════════════════════════════════════
#  РИС. 3.7 — Архитектура Interface
# ══════════════════════════════════════════════════════════════════════════════
def fig_3_7():
    f, a = fig_ax(13, 7.5)
    a.set_title("Рис. 3.7. Архитектура компонента Interface",
                fontsize=10, pad=8)

    # User / Frontend
    box(a, 0.12, 0.88, 0.18, 0.10, ['Пользователь'], C_USER, bold=True)
    box(a, 0.12, 0.72, 0.20, 0.12,
        ['React Frontend', 'Chat · TracePanel', 'Files · Profile'], C_USER)

    # FastAPI
    box(a, 0.38, 0.80, 0.18, 0.12,
        ['FastAPI', '/api/chats/', '/ws (WebSocket)'], C_ORCH)

    # WebSocket Layer
    box(a, 0.38, 0.60, 0.18, 0.12,
        ['WebSocket Layer', 'auth → XREAD', 'heartbeat → push'], C_ORCH)

    # ChatService / JobOrchestrator
    box(a, 0.38, 0.40, 0.18, 0.12,
        ['ChatService', 'JobOrchestrator', 'apply_async'], C_ORCH)

    # RabbitMQ
    box(a, 0.38, 0.20, 0.14, 0.10,
        ['RabbitMQ', 'task broker'], C_EXT)

    # Celery Worker
    box(a, 0.60, 0.20, 0.18, 0.12,
        ['Celery Worker', 'process_agent_message', 'AgentExecutionService'], C_ORCH)

    # Agents
    box(a, 0.83, 0.36, 0.22, 0.36,
        ['7 агентов:', 'General · WebSearch',
         'DeepResearch · ImageGen',
         'PptxGen · AudioTranscribe',
         'SwarmOrchestrator'], C_AGENT)

    # Redis Stream
    box(a, 0.60, 0.60, 0.18, 0.12,
        ['Redis Stream', 'chat:{id}:stream', 'XADD / XREAD'], C_REDIS)

    # Storage
    box(a, 0.60, 0.80, 0.18, 0.12,
        ['PostgreSQL + MinIO', 'история чатов', 'артефакты файлов'], C_EXT)

    # Orchestrator (внешний)
    box(a, 0.83, 0.80, 0.18, 0.10, ['Orchestrator\n(внешний сервис)'], C_ORCH)

    # Стрелки
    arr(a, 0.12, 0.83, 0.12, 0.78, '', C_USER)
    arr(a, 0.22, 0.80, 0.29, 0.80, 'WS + REST', C_USER)
    arr(a, 0.38, 0.74, 0.38, 0.66, '', C_ORCH)
    arr(a, 0.38, 0.54, 0.38, 0.46, 'создать задачу', C_ORCH)
    arr(a, 0.38, 0.34, 0.38, 0.25, 'apply_async', C_ORCH)
    arr(a, 0.45, 0.20, 0.51, 0.20, '', C_EXT)
    arr(a, 0.60, 0.26, 0.60, 0.54, 'XADD', C_REDIS)
    arr(a, 0.68, 0.20, 0.72, 0.36, '', C_AGENT)
    darr(a, 0.71, 0.60, 0.47, 0.60, 'XREAD', C_REDIS)
    arr(a, 0.83, 0.54, 0.83, 0.68, 'POST /task\nWS stream', C_AGENT)
    arr(a, 0.68, 0.80, 0.74, 0.80, 'persist', C_EXT)

    save(f, "fig_3_7_interface_arch.png")


# ══════════════════════════════════════════════════════════════════════════════
#  РИС. 3.8 — Redis Stream: XADD → XREAD модель
# ══════════════════════════════════════════════════════════════════════════════
def fig_3_8():
    f, a = fig_ax(12, 4.0)
    a.set_title("Рис. 3.8. Модель Redis Stream: XADD (агент) → XREAD (WebSocket) → клиент",
                fontsize=10, pad=8)

    nodes = [
        (0.10, 'Celery Worker\nAgentExecutionService', C_ORCH),
        (0.32, 'Redis Stream\nchat:{thread_id}:stream', C_REDIS),
        (0.55, 'WebSocket Handler\n(XREAD block=0)\nheartbeat 15s', C_ORCH),
        (0.78, 'React Frontend\nChat + TracePanel', C_USER),
    ]
    for x, text, c in nodes:
        box(a, x, 0.58, 0.16, 0.30, text.split('\n'), c)

    lbls = ['XADD\npayload+seq', 'XREAD\n(blocking)', 'WS push\n(json event)']
    for i in range(3):
        arr(a, nodes[i][0]+0.08, 0.58, nodes[i+1][0]-0.08, 0.58, lbls[i], '#555555')

    # Event examples
    events = [
        '{"seq":1, "type":"routing_event", "agent":"Router", "category":"navigation"}',
        '{"seq":2, "type":"stream_chunk",  "agent":"Navigation", "delta":"Отправляю..."}',
        '{"seq":7, "type":"agent_reply",   "agent":"Navigation", "content":"Миссия создана"}',
    ]
    for i, ev in enumerate(events):
        a.text(0.50, 0.18 - i*0.10, ev, ha='center', fontsize=6.5,
               color='#333333', family='monospace',
               bbox=dict(boxstyle='round,pad=0.2', facecolor='#f5f5f5', edgecolor='#cccccc'))

    save(f, "fig_3_8_redis_stream.png")


# ══════════════════════════════════════════════════════════════════════════════
#  РИС. 4.1 — Пайплайн дистилляции SmolVLA
# ══════════════════════════════════════════════════════════════════════════════
def fig_4_1():
    f, a = fig_ax(13, 5.5)
    a.set_title("Рис. 4.1. Пайплайн оптимизации SmolVLA: KD → FP16 → Pruning → INT8-анализ",
                fontsize=10, pad=8)

    # Teacher
    box(a, 0.10, 0.65, 0.14, 0.18,
        ['Teacher', 'SmolVLA Base', '450M params', 'FP32 · 6 ГБ'], C_MISS, bold=True)

    # Stages
    stages = [
        (0.28, 'Stage 1\nKnowledge\nDistillation\nL=α·MSE+(1-α)·KL\n+λ·AT\n10 эпох T=3.0'),
        (0.46, 'Stage 2\nFP16\nMixed Precision\ntorch.cuda.amp\n×1.5–2 ускорение'),
        (0.64, 'Stage 3\nStructured\nPruning\n30% Linear\nL2-norm'),
        (0.82, 'Stage 4\nINT8\nQuantization\nAnalysis\ncritical layers'),
    ]
    colors = [C_ORCH, C_MISS, C_AGENT, '#888888']
    for (x, text), c in zip(stages, colors):
        box(a, x, 0.65, 0.15, 0.30, text.split('\n'), c)

    # Student
    box(a, 0.28, 0.22, 0.14, 0.16,
        ['Student', '~1M params', 'student_ratio', 'малый размер'], C_ORCH)

    arr(a, 0.10, 0.65, 0.20, 0.65, '', C_MISS)
    for i in range(len(stages)-1):
        arr(a, stages[i][0]+0.075, 0.65, stages[i+1][0]-0.075, 0.65, '', '#555555')
    arr(a, 0.10, 0.56, 0.21, 0.25, 'обучение\nStudent', C_MISS)

    # Результат
    res = ('Результат: 443× ↓ параметры  |  12× ↓ VRAM  |  25× ↑ скорость  '
           '|  MSE +9.1%  R² −1.8%')
    a.text(0.50, 0.06, res, ha='center', fontsize=9, color='#222222',
           bbox=dict(boxstyle='round,pad=0.4', facecolor='#eef6e8', edgecolor=C_AGENT, lw=1.5))
    save(f, "fig_4_1_smolvla_pipeline.png")


# ══════════════════════════════════════════════════════════════════════════════
#  Запуск всех генераторов
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print("Генерация диаграмм для диссертации AgentsSwarm...")
    fig_2_1()
    fig_2_2()
    fig_2_3()
    fig_2_4()
    fig_2_5()
    fig_3_1()
    fig_3_3()
    fig_3_4()
    fig_3_5()
    fig_3_6()
    fig_3_7()
    fig_3_8()
    fig_4_1()
    print(f"\nГотово! Все PNG сохранены в ./{OUT}/")
