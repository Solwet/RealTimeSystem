import sys
import random
import time
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTabWidget, QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsSimpleTextItem,
    QTableWidget, QTableWidgetItem, QLabel, QSlider, QComboBox, QTextBrowser
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor, QBrush
import pyqtgraph as pg
from collections import deque

# -------------------------- Параметры --------------------------
MAX_BAYS = 4
DOCK_X = 400
DOCK_Y_GAP = 120
TRUCK_SPEED = 5
UPDATE_INTERVAL = 50  # мс
TRUCK_ARRIVAL_PROB = 0.02
FIRE_DURATION = 10  # секунд
FIRE_COST = 300

TRUCK_TYPES = {
    "Small": (40, 25, 3, 6, "lightblue"),
    "Medium": (50, 30, 4, 8, "orange"),
    "Large": (60, 35, 6, 10, "purple")
}

# -------------------------- Состояние --------------------------
state = {
    "truck_id": 0,
    "active_bays": [True]*MAX_BAYS,
    "dock_queues": [[] for _ in range(MAX_BAYS)],
    "moving_trucks": [],
    "global_queue": deque(),
    "wait_times": [],
    "total_loaded": 0,
    "step_count": 0,
    "waiting_trucks": [],
    "loading_trucks": [],
    "loaded_cumulative": [],
    "dock_status": [None]*MAX_BAYS,
    "money": 0,
    "money_history": [],  # ✅ Новая история финансов
    "repair_cost": 100,
    "truck_profit": {"Small": 30, "Medium": 50, "Large": 80},
    "transactions": [],
    "fire_timers": [None]*MAX_BAYS
}

# -------------------------- Класс грузовика --------------------------
class Truck(QGraphicsRectItem):
    def __init__(self, tid, truck_type="Medium"):
        w, h, min_load, max_load, color = TRUCK_TYPES[truck_type]
        super().__init__(0, 0, w, h)
        self.id = tid
        self.type = truck_type
        self.color = color
        self.dock = None
        self.arrive_time = time.time()
        self.start_time = None
        self.load_time = random.uniform(min_load, max_load)
        self.loading = False
        self.returning_to_queue = False
        self.setBrush(QBrush(QColor(color)))
        self.setZValue(1)
        self.target_x = 100
        self.target_y = 80

        self.text = QGraphicsSimpleTextItem(f"T{tid}", self)
        self.text.setPos(w/4, -15)

        self.progress = QGraphicsRectItem(0, h+2, w, 5, self)
        self.progress.setBrush(QBrush(QColor("green")))
        self.progress.setRect(0, h+2, 0, 5)

    def move_toward_target(self):
        if self.loading:
            elapsed = time.time() - self.start_time
            ratio = min(1.0, elapsed / self.load_time)
            self.progress.setRect(0, self.rect().height()+2, self.rect().width()*ratio, 5)
            return True
        dx = self.target_x - self.x()
        dy = self.target_y - self.y()
        dist = (dx**2 + dy**2)**0.5
        if dist < TRUCK_SPEED:
            self.setPos(self.target_x, self.target_y)
            return True
        else:
            self.setPos(self.x() + TRUCK_SPEED*dx/dist, self.y() + TRUCK_SPEED*dy/dist)
            return False

# -------------------------- Главный класс --------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Управление погрузкой грузовых автомобилей")
        self.resize(1500, 800)  # чуть выше для 3 графиков
        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)

        self.fire_colors = [False] * MAX_BAYS
        self.fire_blink_timer = QTimer()
        self.fire_blink_timer.timeout.connect(self.blink_fire_colors)
        self.fire_blink_timer.start(500)

    def init_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Вкладка описание
               # -------------------------- Вкладка описание --------------------------
        self.tab_desc = QWidget()
        layout_desc = QVBoxLayout()
        text = QTextBrowser()

        description_html = """
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
            <h1 style="text-align: center; color: #2c3e50; margin-bottom: 10px;">
                🚛 Управление погрузкой грузовых автомобилей
            </h1>
            <p style="text-align: center; color: #7f8c8d; font-size: 16px; margin-bottom: 30px;">
                Продвинутая симуляция складской логистики с финансовым учётом и чрезвычайными ситуациями
            </p>

            <div style="background: #f8f9fa; border-left: 8px solid #3498db; padding: 16px; margin: 20px 0; border-radius: 0 12px 12px 0;">
                <h2 style="color: #2980b9; margin-top: 0;">Основные возможности</h2>
                <ul style="font-size: 14px; line-height: 1.6; color: #34495e;">
                    <li><b>Реалистичная очередь</b> — грузовики прибывают с заданной вероятностью и ждут своей очереди.</li>
                    <li><b>Три типа грузовиков</b> — Small, Medium, Large с разной прибылью и временем погрузки.</li>
                    <li><b>Аварийные ситуации</b> — пожары и поломки останавливают работу доков.</li>
                    <li><b>Финансовая система</b> — прибыль от погрузки, расходы на ремонт и тушение.</li>
                    <li><b>Плавная анимация</b> — грузовики плавно перемещаются, включая возврат в очередь при ЧС.</li>
                    <li><b>Динамическая аналитика</b> — графики очереди, загрузки, ожидания и финансов в реальном времени.</li>
                </ul>
            </div>

            <div style="background: #f8f9fa; border-left: 8px solid #f39c12; padding: 16px; margin: 20px 0; border-radius: 0 12px 12px 0;">
                <h2 style="color: #e67e22; margin-top: 0;"> Цветовая индикация доков</h2>
                <ul style="font-size: 14px; line-height: 1.6; color: #34494e;">
                    <li><span style="display: inline-block; width: 16px; height: 16px; background: green; border: 1px solid #333; margin-right: 6px;"></span> <b>Зелёный</b> — док свободен и готов к работе.</li>
                    <li><span style="display: inline-block; width: 16px; height: 16px; background: yellow; border: 1px solid #333; margin-right: 6px;"></span> <b>Жёлтый</b> — в доке идёт погрузка грузовика.</li>
                    <li><span style="display: inline-block; width: 16px; height: 16px; background: red; border: 1px solid #333; margin-right: 6px;"></span> 
                        <span style="display: inline-block; width: 16px; height: 16px; background: orange; border: 1px solid #333; margin-right: 6px;"></span> 
                        <b>Красный - оранжевый</b> — в доке <b>пожар</b> (мигает для привлечения внимания).</li>
                    <li><span style="display: inline-block; width: 16px; height: 16px; background: darkred; border: 1px solid #333; margin-right: 6px;"></span> <b>Тёмно-красный</b> — док <b>сломан</b> (авария, требует ремонта).</li>
                </ul>
            </div>

            <div style="background: #f8f9fa; border-left: 8px solid #2ecc71; padding: 15px; margin: 20px 0; border-radius: 0 12px 12px 0;">
                <h2 style="color: #27ae60; margin-top: 0;">💰 Финансовая модель</h2>
                <h3 style="color: #27ae60; margin: 12px 0 8px 0;">Доходы (при успешной погрузке):</h3>
                <ul style="font-size: 14px; line-height: 1.6; color: #2c3e50;">
                    <li>🚛 <b>Small</b>: <span style="color: green; font-weight: bold;">+30</span></li>
                    <li>🚛 <b>Medium</b>: <span style="color: green; font-weight: bold;">+50</span></li>
                    <li>🚛 <b>Large</b>: <span style="color: green; font-weight: bold;">+80</span></li>
                </ul>
                <h3 style="color: #f8f9fa; margin: 16px 0 8px 0;">Расходы:</h3>
                <ul style="font-size: 14px; line-height: 1.6; color: #2c3e50;">
                    <li>🔧 <b>Ремонт дока</b>: <span style="color: red; font-weight: bold;">–100</span></li>
                    <li>🚒 <b>Тушение пожара</b>: <span style="color: red; font-weight: bold;">–300</span></li>
                </ul>
                <p style="font-size: 13px; color: #7f8c8d; margin-top: 10px;">
                    Все транзакции отображаются в реальном времени в журнале и влияют на общий баланс.
                </p>
            </div>

            <div style="text-align: center; margin-top: 30px; color: #95a5a6; font-size: 13px;">
                <p><b>Разработчик:</b> Мухтаров Руслан ПИ-430Б</p>
            </div>
        </div>
        """

        text.setHtml(description_html)
        text.setReadOnly(True)
        text.setStyleSheet("border: none; background: transparent;")
        layout_desc.addWidget(text)
        self.tab_desc.setLayout(layout_desc)
        self.tabs.addTab(self.tab_desc, "🧭 Описание")

        # Вкладка анимации
        self.tab_anim = QWidget()
        h_layout = QHBoxLayout()
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        h_layout.addWidget(self.view)

        self.truck_table = QTableWidget(0, 5)
        self.truck_table.setHorizontalHeaderLabels(["ID", "Тип", "Док", "Статус", "Время ожидания"])
        self.truck_table.setMaximumWidth(300)
        h_layout.addWidget(self.truck_table)

        v_controls = QVBoxLayout()
        self.btn_start = QPushButton("▶️ Запустить")
        self.btn_stop = QPushButton("⏹ Остановить")
        self.btn_emergency_all = QPushButton("⚠️ Авария все")
        self.btn_repair_all = QPushButton("🔧 Починить все")
        self.dock_combo = QComboBox()
        self.dock_combo.addItems([f"Док {i+1}" for i in range(MAX_BAYS)])
        self.btn_emergency_single = QPushButton("💥 Поломка дока")
        self.btn_fire_single = QPushButton("🔥 Пожар в доке")
        self.btn_repair_single = QPushButton("🧰 Починить док")
        self.slider_arrival = QSlider(Qt.Orientation.Horizontal)
        self.slider_arrival.setRange(1, 50)
        self.slider_arrival.setValue(int(TRUCK_ARRIVAL_PROB*1000))
        self.label_money = QLabel(f"💰 Деньги: {state['money']}")
        self.tx_browser = QTextBrowser()

        v_controls.addWidget(self.btn_start)
        v_controls.addWidget(self.btn_stop)
        v_controls.addWidget(self.btn_emergency_all)
        v_controls.addWidget(self.btn_repair_all)
        v_controls.addWidget(QLabel("Выбор дока:"))
        v_controls.addWidget(self.dock_combo)
        v_controls.addWidget(self.btn_emergency_single)
        v_controls.addWidget(self.btn_fire_single)
        v_controls.addWidget(self.btn_repair_single)
        v_controls.addWidget(QLabel("Вероятность прибытия (‰):"))
        v_controls.addWidget(self.slider_arrival)
        v_controls.addWidget(self.label_money)
        v_controls.addWidget(QLabel("📜 История транзакций:"))
        v_controls.addWidget(self.tx_browser)

        h_layout.addLayout(v_controls)
        self.tab_anim.setLayout(h_layout)
        self.tabs.addTab(self.tab_anim, "🚛 Анимация")

        # Вкладка графиков — ✅ ДОБАВЛЕН ТРЕТИЙ ГРАФИК
        self.tab_graphs = QWidget()
        v_graph = QVBoxLayout()
        self.pg_plot = pg.PlotWidget(title="Очередь, загрузка и погружено")
        self.pg_plot.addLegend()
        self.pg_plot.setLabel('left', 'Количество грузовиков')
        self.pg_plot.setLabel('bottom', 'Шаг симуляции')

        self.pg_plot_avg = pg.PlotWidget(title="Среднее ожидание")
        self.pg_plot_avg.addLegend()
        self.pg_plot_avg.setLabel('left', 'Среднее время ожидания (сек)')
        self.pg_plot_avg.setLabel('bottom', 'Количество обработанных грузовиков')

        self.pg_plot_money = pg.PlotWidget(title="Финансы (Деньги)")
        self.pg_plot_money.addLegend()
        self.pg_plot_money.setLabel('left', 'Деньги')
        self.pg_plot_money.setLabel('bottom', 'Шаг симуляции')
        self.pg_plot_money.setLabel('left', 'Деньги', color='green')  # опционально

        v_graph.addWidget(self.pg_plot)
        v_graph.addWidget(self.pg_plot_avg)
        v_graph.addWidget(self.pg_plot_money)  # ✅ Добавлен
        self.tab_graphs.setLayout(v_graph)
        self.tabs.addTab(self.tab_graphs, "📊 Графики")

        # Сигналы
        self.btn_start.clicked.connect(self.start)
        self.btn_stop.clicked.connect(self.stop)
        self.btn_emergency_all.clicked.connect(self.emergency_all)
        self.btn_repair_all.clicked.connect(self.repair_all)
        self.btn_emergency_single.clicked.connect(self.break_dock)
        self.btn_fire_single.clicked.connect(self.fire_dock)
        self.btn_repair_single.clicked.connect(self.repair_one)
        self.slider_arrival.valueChanged.connect(self.set_arrival_prob)

        # Доки
        self.dock_items = []
        for i in range(MAX_BAYS):
            rect = self.scene.addRect(DOCK_X, 100+i*DOCK_Y_GAP, 150, 50, brush=QBrush(QColor("green")))
            self.dock_items.append(rect)

        self.setStyleSheet("""
            QPushButton { font-size: 14px; padding: 5px; }
            QSlider::handle { background: #3498db; width: 15px; }
            QSlider::groove { background: #bdc3c7; height: 6px; }
            QTabWidget::pane { border: 1px solid #3498db; }
        """)

    # -------------------------- Управление --------------------------
    def start(self):
        state["truck_id"] = 0
        state["step_count"] = 0
        state["waiting_trucks"].clear()
        state["loading_trucks"].clear()
        state["loaded_cumulative"].clear()
        state["wait_times"].clear()
        state["total_loaded"] = 0
        state["money"] = 0
        state["money_history"].clear()  # ✅ Сброс истории финансов
        state["transactions"].clear()
        state["fire_timers"] = [None]*MAX_BAYS
        self.tx_browser.clear()
        self.timer.start(UPDATE_INTERVAL)

    def stop(self):
        self.timer.stop()

    def set_arrival_prob(self, val):
        global TRUCK_ARRIVAL_PROB
        TRUCK_ARRIVAL_PROB = val/1000

    def emergency_all(self):
        for i in range(MAX_BAYS):
            state["dock_status"][i] = "broken"
            state["active_bays"][i] = False
        self.update_dock_colors()

    def repair_all(self):
        for i in range(MAX_BAYS):
            if state["dock_status"][i] == "broken":
                state["money"] -= state["repair_cost"]
                state["transactions"].append(f"-{state['repair_cost']} починка дока {i+1}")
            elif state["dock_status"][i] == "fire":
                self.extinguish_fire(i)
            state["dock_status"][i] = None
            state["active_bays"][i] = True
        self.update_dock_colors()
        self.move_global_queue_to_docks()

    def break_dock(self):
        idx = self.dock_combo.currentIndex()
        state["dock_status"][idx] = "broken"
        state["active_bays"][idx] = False
        self.update_dock_colors()

    def fire_dock(self):
        idx = self.dock_combo.currentIndex()
        if state["dock_status"][idx] in ["broken", "fire"]:
            return

        for truck in list(state["dock_queues"][idx]):
            truck.loading = False
            truck.progress.setRect(0, truck.rect().height() + 2, 0, 5)
            truck.setBrush(QBrush(QColor(truck.color)))
            truck.dock = None
            truck.returning_to_queue = True
            target_index = len(state["global_queue"])
            truck.target_x = 50 + target_index * 55
            truck.target_y = 50
            if truck not in state["moving_trucks"]:
                state["moving_trucks"].append(truck)

        state["dock_queues"][idx].clear()
        state["dock_status"][idx] = "fire"
        state["active_bays"][idx] = False
        state["fire_timers"][idx] = time.time() + FIRE_DURATION
        state["money"] -= FIRE_COST
        state["transactions"].append(f"-{FIRE_COST} тушение пожара в доке {idx+1}")
        self.update_dock_colors()

    def extinguish_fire(self, idx):
        state["fire_timers"][idx] = None
        state["dock_status"][idx] = None
        state["active_bays"][idx] = True
        self.update_dock_colors()
        self.move_global_queue_to_docks()

    def repair_one(self):
        idx = self.dock_combo.currentIndex()
        if state["dock_status"][idx] == "broken":
            state["money"] -= state["repair_cost"]
            state["transactions"].append(f"-{state['repair_cost']} починка дока {idx+1}")
            state["dock_status"][idx] = None
            state["active_bays"][idx] = True
        elif state["dock_status"][idx] == "fire":
            self.extinguish_fire(idx)
        self.update_dock_colors()
        self.move_global_queue_to_docks()

    def update_dock_colors(self):
        for i, rect in enumerate(self.dock_items):
            if state["dock_status"][i] == "broken":
                color = "darkred"
            elif state["dock_status"][i] == "fire":
                color = "red" if self.fire_colors[i] else "orange"
            else:
                color = "yellow" if state["dock_queues"][i] and state["dock_queues"][i][0].loading else "green"
            rect.setBrush(QBrush(QColor(color)))

    def blink_fire_colors(self):
        for i in range(MAX_BAYS):
            if state["dock_status"][i] == "fire":
                self.fire_colors[i] = not self.fire_colors[i]
                self.update_dock_colors()

    # -------------------------- Симуляция --------------------------
    def update_simulation(self):
        for i in range(MAX_BAYS):
            if state["dock_status"][i] == "fire" and state["fire_timers"][i] is not None:
                if time.time() >= state["fire_timers"][i]:
                    self.extinguish_fire(i)

        if random.random() < TRUCK_ARRIVAL_PROB:
            self.add_new_truck()

        for truck in list(state["moving_trucks"]):
            arrived = truck.move_toward_target()

            if truck.returning_to_queue and arrived:
                state["global_queue"].append(truck)
                truck.returning_to_queue = False
                state["moving_trucks"].remove(truck)
            elif not truck.returning_to_queue and truck.x() > 1200:
                self.scene.removeItem(truck)
                state["moving_trucks"].remove(truck)

        for i, queue in enumerate(state["dock_queues"]):
            if queue:
                truck = queue[0]
                if not truck.loading and state["active_bays"][i] and state["dock_status"][i] != "fire":
                    if abs(truck.x() - truck.target_x) < 1 and abs(truck.y() - truck.target_y) < 1:
                        truck.loading = True
                        truck.start_time = time.time()
                elif truck.loading and (not state["active_bays"][i] or state["dock_status"][i] == "fire"):
                    truck.loading = False
                    truck.progress.setRect(0, truck.rect().height() + 2, 0, 5)
                    truck.setBrush(QBrush(QColor(truck.color)))
                    truck.dock = None
                    truck.returning_to_queue = True
                    target_index = len(state["global_queue"])
                    truck.target_x = 50 + target_index * 55
                    truck.target_y = 50
                    if truck not in state["moving_trucks"]:
                        state["moving_trucks"].append(truck)
                    state["dock_queues"][i].clear()
                elif truck.loading and state["active_bays"][i] and state["dock_status"][i] != "fire" and (time.time() - truck.start_time >= truck.load_time):
                    self.finish_truck(truck, i)

        self.move_global_queue_to_docks()
        self.update_truck_table()
        self.update_graphs()
        self.label_money.setText(f"💰 Деньги: {state['money']}")
        self.tx_browser.setPlainText("\n".join(state["transactions"][-20:]))

    # -------------------------- Грузовики --------------------------
    def add_new_truck(self):
        state["truck_id"] += 1
        truck_type = random.choice(list(TRUCK_TYPES.keys()))
        truck = Truck(state["truck_id"], truck_type)
        truck.setPos(50 + len(state["global_queue"])*55, 50)
        self.scene.addItem(truck)
        state["global_queue"].append(truck)
        state["moving_trucks"].append(truck)

    def assign_truck_to_dock(self):
        free_docks = [i for i, active in enumerate(state["active_bays"])
                      if active and len(state["dock_queues"][i]) == 0 and state["dock_status"][i] not in ["broken", "fire"]]
        return free_docks[0] if free_docks else None

    def move_global_queue_to_docks(self):
        for _ in range(len(state["global_queue"])):
            truck = state["global_queue"][0]
            dock_idx = self.assign_truck_to_dock()
            if dock_idx is not None:
                state["global_queue"].popleft()
                truck.dock = dock_idx
                truck.target_x = DOCK_X + 10
                truck.target_y = 110 + dock_idx*DOCK_Y_GAP
                state["dock_queues"][dock_idx].append(truck)
                if truck not in state["moving_trucks"]:
                    state["moving_trucks"].append(truck)
            else:
                break

    def finish_truck(self, truck, dock_idx):
        if truck in state["dock_queues"][dock_idx]:
            state["dock_queues"][dock_idx].remove(truck)
        state["total_loaded"] += 1
        wait_time = truck.start_time - truck.arrive_time
        state["wait_times"].append(wait_time)

        profit = state["truck_profit"].get(truck.type, 50)
        state["money"] += profit
        state["transactions"].append(f"+{profit} от T{truck.id} ({truck.type})")

        truck.loading = False
        truck.setBrush(QBrush(QColor(truck.color)))
        truck.target_x = 1200
        truck.target_y = truck.y()
        if truck not in state["moving_trucks"]:
            state["moving_trucks"].append(truck)

    def update_truck_table(self):
        self.truck_table.setRowCount(0)
        for i, queue in enumerate(state["dock_queues"]):
            for truck in queue:
                row = self.truck_table.rowCount()
                self.truck_table.insertRow(row)
                self.truck_table.setItem(row, 0, QTableWidgetItem(str(truck.id)))
                self.truck_table.setItem(row, 1, QTableWidgetItem(truck.type))
                self.truck_table.setItem(row, 2, QTableWidgetItem(f"Док {i+1}"))
                status = "Погрузка" if truck.loading else "Ожидание"
                self.truck_table.setItem(row, 3, QTableWidgetItem(status))
                wait_time = int(truck.start_time - truck.arrive_time) if truck.loading else int(time.time() - truck.arrive_time)
                self.truck_table.setItem(row, 4, QTableWidgetItem(str(wait_time)))
        for truck in state["global_queue"]:
            row = self.truck_table.rowCount()
            self.truck_table.insertRow(row)
            self.truck_table.setItem(row, 0, QTableWidgetItem(str(truck.id)))
            self.truck_table.setItem(row, 1, QTableWidgetItem(truck.type))
            self.truck_table.setItem(row, 2, QTableWidgetItem("—"))
            self.truck_table.setItem(row, 3, QTableWidgetItem("В очереди"))
            wait_time = int(time.time() - truck.arrive_time)
            self.truck_table.setItem(row, 4, QTableWidgetItem(str(wait_time)))

    def update_graphs(self):
        state["step_count"] += 1
        current_step = state["step_count"]
        queue_len = len(state["global_queue"]) + sum(len(q) for q in state["dock_queues"])
        loading = sum(1 for q in state["dock_queues"] if q and q[0].loading)

        state["waiting_trucks"].append(queue_len)
        state["loading_trucks"].append(loading)
        state["loaded_cumulative"].append(state["total_loaded"])
        state["money_history"].append(state["money"])  # ✅ Сохраняем текущие деньги

        steps = list(range(1, current_step + 1))

        # График очереди и загрузки
        self.pg_plot.clear()
        self.pg_plot.plot(steps, state["waiting_trucks"], pen=pg.mkPen('r', width=2), name="Очередь")
        self.pg_plot.plot(steps, state["loading_trucks"], pen=pg.mkPen('b', width=2), name="Погрузка")
        self.pg_plot.plot(steps, state["loaded_cumulative"], pen=pg.mkPen('g', width=2), name="Погружено")

        # График среднего ожидания
        self.pg_plot_avg.clear()
        if state["wait_times"]:
            avg = [sum(state["wait_times"][:i+1]) / (i+1) for i in range(len(state["wait_times"]))]
            truck_indices = list(range(1, len(avg) + 1))
            self.pg_plot_avg.plot(truck_indices, avg, pen=pg.mkPen('m', width=2), name="Среднее ожидание")

        # ✅ График финансов
        self.pg_plot_money.clear()
        self.pg_plot_money.plot(steps, state["money_history"], pen=pg.mkPen('green', width=2), name="Деньги")
        # Опционально: горизонтальная линия на нуле
        if state["money_history"]:
            self.pg_plot_money.addItem(pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen('gray', style=Qt.PenStyle.DashLine)))


# -------------------------- Запуск --------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())