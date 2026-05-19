"""
Mock-скриншоты интерфейса AgentsSwarm Interface для ВКР.
Рис. 3.9 — Chat, Рис. 3.10 — TracePanel.
Рис. 3.11 удалён из текста ВКР и этим скриптом больше не создаётся.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np
import os

OUT = os.path.join(os.path.dirname(__file__), 'img')
os.makedirs(OUT, exist_ok=True)

# ── цвета Chakra UI / тёмная тема ──────────────────────────────────────────
BG      = '#1a202c'   # gray.800
SIDEBAR = '#2d3748'   # gray.700
PANEL   = '#2d3748'
MSG_U   = '#3182ce'   # blue.500
MSG_A   = '#2d3748'   # gray.700
BORDER  = '#4a5568'   # gray.600
TEXT    = '#e2e8f0'   # gray.200
MUTED   = '#a0aec0'   # gray.500
GREEN   = '#38a169'   # green.600
ORANGE  = '#dd6b20'   # orange.600
BLUE    = '#3182ce'
PURPLE  = '#805ad5'


def rounded_rect(ax, x, y, w, h, color, alpha=1.0, radius=0.005, lw=0):
    r = FancyBboxPatch((x, y), w, h,
                       boxstyle=f"round,pad={radius}",
                       facecolor=color, edgecolor='none',
                       linewidth=lw, alpha=alpha,
                       transform=ax.transAxes, clip_on=True)
    ax.add_patch(r)


def text(ax, x, y, s, color=TEXT, fs=8, ha='left', va='center', bold=False, mono=False):
    w = 'bold' if bold else 'normal'
    f = 'monospace' if mono else 'sans-serif'
    ax.text(x, y, s, color=color, fontsize=fs, ha=ha, va=va,
            fontweight=w, fontfamily=f, transform=ax.transAxes)


# ── Рис. 3.9 — Chat ────────────────────────────────────────────────────────
def fig_chat():
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.axis('off')
    fig.patch.set_facecolor(BG)

    # Sidebar
    rounded_rect(ax, 0, 0, 0.22, 1, SIDEBAR)
    text(ax, 0.03, 0.96, 'AgentsSwarm', TEXT, fs=10, bold=True)
    text(ax, 0.03, 0.91, '💬  Chat', BLUE, fs=9, bold=True)
    text(ax, 0.03, 0.86, '📋  TracePanel', MUTED, fs=8)
    text(ax, 0.03, 0.82, '📁  Files', MUTED, fs=8)
    text(ax, 0.03, 0.78, '👤  Profile', MUTED, fs=8)

    text(ax, 0.03, 0.70, 'Диалоги', MUTED, fs=7, bold=True)
    for i, (title, ts) in enumerate([
        ('Навигация Carter', '14:32'),
        ('Патруль склада',   '13:15'),
        ('Зарядка роботов',  '11:40'),
    ]):
        y = 0.64 - i * 0.08
        rounded_rect(ax, 0.02, y - 0.025, 0.18, 0.05,
                     PANEL if i == 0 else 'none', alpha=0.6)
        text(ax, 0.04, y, title, TEXT if i == 0 else MUTED, fs=7.5)
        text(ax, 0.18, y, ts, MUTED, fs=6.5, ha='right')

    # Main area
    rounded_rect(ax, 0.23, 0, 0.77, 1, BG)

    # Header
    rounded_rect(ax, 0.23, 0.92, 0.77, 0.08, SIDEBAR)
    text(ax, 0.26, 0.96, 'Навигация Carter', TEXT, fs=9.5, bold=True)
    rounded_rect(ax, 0.78, 0.94, 0.18, 0.035, BLUE, radius=0.003)
    text(ax, 0.87, 0.958, 'SwarmOrchestrator ▾', TEXT, fs=7.5, ha='center')

    # Messages
    msgs = [
        ('user',  0.84, 'Направь робота Carter в зону B-12 для инспекции.'),
        ('agent', 0.70, 'Выполняю маршрутизацию запроса через Router Agent →\nMissionPlanner. Строю маршрут до зоны B-12...'),
        ('agent', 0.57, '[routing_event] Router → MissionPlanner\n[tool_event]  get_waypoints(zone="B-12")\n[tool_event]  create_mission(robot="carter_1", target="B-12")'),
        ('agent', 0.44, 'Миссия создана (ID: mission_047). Робот Carter_1\nдвижется по маршруту: Hub → Corridor-C → Zone B-12.\nОжидаемое время прибытия: ~4 мин.'),
        ('user',  0.33, 'Покажи статус миссии.'),
        ('agent', 0.22, '[tool_event]  get_mission_status(id="mission_047")\n\nМиссия 047: статус RUNNING, прогресс 60%.\nКартер на участке Corridor-C.'),
    ]
    for role, y, msg in msgs:
        is_user = (role == 'user')
        col = MSG_U if is_user else MSG_A
        x0 = 0.60 if is_user else 0.25
        w = 0.36
        lines = msg.count('\n') + 1
        h = 0.045 + (lines - 1) * 0.028
        rounded_rect(ax, x0, y - h/2 - 0.005, w, h + 0.01, col,
                     radius=0.004)
        is_mono = '[tool_event]' in msg or '[routing_event]' in msg
        for li, line in enumerate(msg.split('\n')):
            ly = y + (lines - 1 - li) * 0.027 - (lines - 1) * 0.013
            text(ax, x0 + 0.012, ly, line, TEXT, fs=7.2,
                 mono=is_mono)

    # Input
    rounded_rect(ax, 0.24, 0.03, 0.68, 0.07, PANEL, radius=0.005)
    text(ax, 0.27, 0.065, 'Введите сообщение...', MUTED, fs=8)
    rounded_rect(ax, 0.93, 0.038, 0.06, 0.054, BLUE, radius=0.004)
    text(ax, 0.96, 0.065, '▶', TEXT, fs=10, ha='center')

    plt.tight_layout(pad=0)
    fig.savefig(os.path.join(OUT, 'fig_3_9_chat.png'), dpi=300,
                bbox_inches='tight', facecolor=BG)
    plt.close()
    print('  saved: fig_3_9_chat.png')


# ── Рис. 3.10 — TracePanel ──────────────────────────────────────────────────
def fig_trace():
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.axis('off')
    fig.patch.set_facecolor(BG)

    rounded_rect(ax, 0, 0, 0.22, 1, SIDEBAR)
    text(ax, 0.03, 0.96, 'AgentsSwarm', TEXT, fs=10, bold=True)
    text(ax, 0.03, 0.91, '💬  Chat', MUTED, fs=8)
    text(ax, 0.03, 0.86, '📋  TracePanel', BLUE, fs=9, bold=True)
    text(ax, 0.03, 0.82, '📁  Files', MUTED, fs=8)
    text(ax, 0.03, 0.78, '👤  Profile', MUTED, fs=8)

    rounded_rect(ax, 0.23, 0, 0.77, 1, BG)
    rounded_rect(ax, 0.23, 0.92, 0.77, 0.08, SIDEBAR)
    text(ax, 0.26, 0.96, 'Трассировка агентного маршрута', TEXT, fs=9.5, bold=True)
    text(ax, 0.80, 0.96, 'mission_047  |  carter_1', MUTED, fs=8)

    # Column headers
    hs = [0.26, 0.40, 0.56, 0.72, 0.88]
    for h, label in zip(hs, ['Время', 'Тип события', 'Агент', 'Инструмент / данные', 'Статус']):
        text(ax, h, 0.88, label, MUTED, fs=7.5, bold=True)
    rounded_rect(ax, 0.24, 0.855, 0.74, 0.002, BORDER)

    events = [
        ('14:32:01', 'routing_event',  'Router',          '→ MissionPlanner',              GREEN,  '✓'),
        ('14:32:02', 'tool_event',     'MissionPlanner',  'get_waypoints(zone="B-12")',     BLUE,   '✓'),
        ('14:32:03', 'tool_event',     'MissionPlanner',  'create_mission(robot="c1")',     BLUE,   '✓'),
        ('14:32:03', 'stream_chunk',   'MissionPlanner',  'Миссия создана ID=047',         MUTED,  '✓'),
        ('14:32:15', 'tool_event',     'MissionPlanner',  'get_mission_status(id=047)',     BLUE,   '✓'),
        ('14:32:15', 'stream_chunk',   'MissionPlanner',  'RUNNING 60% Corridor-C',        MUTED,  '✓'),
        ('14:32:16', 'agent_reply',    'MissionPlanner',  '—',                             GREEN,  '✓'),
    ]

    for i, (ts, etype, agent, data, col, st) in enumerate(events):
        y = 0.82 - i * 0.085
        if i % 2 == 0:
            rounded_rect(ax, 0.24, y - 0.032, 0.74, 0.065, SIDEBAR, alpha=0.4)
        text(ax, 0.26, y, ts, MUTED, fs=7.5, mono=True)
        rounded_rect(ax, 0.385, y - 0.018, 0.13, 0.036, col, alpha=0.2, radius=0.003)
        text(ax, 0.39, y, etype, col, fs=7, mono=True)
        text(ax, 0.565, y, agent, TEXT, fs=7.5)
        text(ax, 0.715, y, data, TEXT, fs=7, mono=True)
        text(ax, 0.88, y, st, GREEN, fs=9, ha='center')

    plt.tight_layout(pad=0)
    fig.savefig(os.path.join(OUT, 'fig_3_10_trace.png'), dpi=300,
                bbox_inches='tight', facecolor=BG)
    plt.close()
    print('  saved: fig_3_10_trace.png')


# ── Рис. 3.11 — Files ──────────────────────────────────────────────────────
def fig_files():
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.axis('off')
    fig.patch.set_facecolor(BG)

    rounded_rect(ax, 0, 0, 0.22, 1, SIDEBAR)
    text(ax, 0.03, 0.96, 'AgentsSwarm', TEXT, fs=10, bold=True)
    text(ax, 0.03, 0.91, '💬  Chat', MUTED, fs=8)
    text(ax, 0.03, 0.86, '📋  TracePanel', MUTED, fs=8)
    text(ax, 0.03, 0.82, '📁  Files', BLUE, fs=9, bold=True)
    text(ax, 0.03, 0.78, '👤  Profile', MUTED, fs=8)

    rounded_rect(ax, 0.23, 0, 0.77, 1, BG)
    rounded_rect(ax, 0.23, 0.92, 0.77, 0.08, SIDEBAR)
    text(ax, 0.26, 0.96, 'Сгенерированные артефакты', TEXT, fs=9.5, bold=True)

    # Filter tabs
    for xi, (label, active) in enumerate([
        ('Все', True), ('Изображения', False), ('PPTX', False), ('Аудио', False)
    ]):
        x = 0.26 + xi * 0.13
        col = BLUE if active else PANEL
        rounded_rect(ax, x, 0.85, 0.11, 0.04, col, radius=0.003)
        text(ax, x + 0.055, 0.87, label, TEXT if active else MUTED,
             fs=8, ha='center')

    # File cards — 2 rows × 4 cols
    files = [
        ('🖼', 'warehouse_map.png',   'ImageGen',       '2.4 МБ', PURPLE),
        ('📊', 'report_may.pptx',     'PptxGen',        '1.8 МБ', ORANGE),
        ('🖼', 'robot_path.png',      'ImageGen',       '1.1 МБ', PURPLE),
        ('🎙', 'briefing.mp3',        'AudioTranscribe','4.2 МБ', GREEN),
        ('🖼', 'zone_b12.png',        'ImageGen',       '980 КБ', PURPLE),
        ('📊', 'fleet_status.pptx',   'PptxGen',        '2.1 МБ', ORANGE),
        ('🖼', 'occupancy_vis.png',   'ImageGen',       '1.3 МБ', PURPLE),
        ('🎙', 'mission_log.mp3',     'AudioTranscribe','6.7 МБ', GREEN),
    ]

    cols, rows = 4, 2
    cw, ch = 0.17, 0.28
    x0, y0 = 0.25, 0.76

    for idx, (icon, name, agent, size, acol) in enumerate(files):
        col_i = idx % cols
        row_i = idx // cols
        x = x0 + col_i * (cw + 0.025)
        y = y0 - row_i * (ch + 0.03)

        rounded_rect(ax, x, y - ch, cw, ch, SIDEBAR, radius=0.006)

        # Preview area
        rounded_rect(ax, x + 0.01, y - ch + 0.11, cw - 0.02, ch - 0.13,
                     '#3a4a5c', radius=0.004)
        text(ax, x + cw/2, y - ch + 0.17, icon, TEXT, fs=18, ha='center')

        # Badge
        rounded_rect(ax, x + 0.01, y - ch + 0.075, 0.09, 0.028, acol,
                     alpha=0.3, radius=0.002)
        text(ax, x + 0.055, y - ch + 0.089, agent, acol, fs=6, ha='center')

        text(ax, x + 0.01, y - ch + 0.05, name, TEXT, fs=6.5)
        text(ax, x + 0.01, y - ch + 0.025, size, MUTED, fs=6)

        # MinIO link
        rounded_rect(ax, x + 0.01, y - ch + 0.002, cw - 0.02, 0.022,
                     BLUE, alpha=0.15, radius=0.002)
        text(ax, x + cw/2, y - ch + 0.013, '⬇ Скачать',
             BLUE, fs=6.5, ha='center')

    plt.tight_layout(pad=0)
    fig.savefig(os.path.join(OUT, 'fig_3_11_files.png'), dpi=300,
                bbox_inches='tight', facecolor=BG)
    plt.close()
    print('  saved: fig_3_11_files.png')


print('Генерация mock-скриншотов...')
fig_chat()
fig_trace()
print('Готово!')
