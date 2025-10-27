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
    "time_series": deque(maxlen=60),
    "waiting_trucks": deque(maxlen=60),
    "loading_trucks": deque(maxlen=60),
    "loaded_cumulative": deque(maxlen=60)
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
        self.setBrush(QBrush(QColor(color)))
        self.setZValue(1)
        self.target_x = 100
        self.target_y = 80

        # Текст с ID
        self.text = QGraphicsSimpleTextItem(f"T{tid}", self)
        self.text.setPos(w/4, -15)

        # Индикатор прогресса
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
        self.resize(1300, 700)
        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)

    def init_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # -------------------------- Вкладка описание --------------------------
        self.tab_desc = QWidget()
        layout_desc = QVBoxLayout()
        text = QTextBrowser()
        text.setHtml("""
        <h1 style="color:#2c3e50; text-align:center;">Управление погрузкой грузовых автомобилей</h1>

        <p style="font-size:14px;">
        Данная система предназначена для моделирования работы доков погрузки грузовых автомобилей на складе или предприятии. 
        Грузовики приезжают к докам, ожидают своей очереди, проходят процесс загрузки и уезжают после завершения. 
        Цель системы — оптимизация работы доков и контроль очереди грузовиков.
        </p>

        <h3 style="color:#27ae60;">Цвет дока:</h3>
        <ul style="font-size:13px;">
        <li><span style="color:green;">Зелёный</span> — док работает и готов принимать грузовики</li>
        <li><span style="color:red;">Красный</span> — док сломан и не принимает грузовики</li>
        <li><span style="color:orange;">Жёлтый</span> — идёт процесс загрузки</li>
        </ul>

        <h3 style="color:#2980b9;">Типы грузовиков:</h3>
        <ul style="font-size:13px;">
        <li>Small — малый грузовик, быстрая загрузка</li>
        <li>Medium — средний грузовик, среднее время загрузки</li>
        <li>Large — большой грузовик, длительная загрузка</li>
        </ul>

        <h3 style="color:#c0392b;">Работа системы:</h3>
        <ul style="font-size:13px;">
        <li>Грузовики формируют глобальную очередь перед доками.</li>
        <li>Если док свободен и исправен, грузовик подъезжает к нему и начинается загрузка.</li>
        <li>Если док сломан, грузовик ожидает свободного исправного дока.</li>
        <li>Система позволяет аварийно останавливать доки или восстанавливать их работу.</li>
        <li>Пользователь может регулировать вероятность появления новых грузовиков с помощью ползунка.</li>
        </ul>

        <h3 style="color:#8e44ad;">Разработчик:</h3>
        <p style="font-size:13px;">Мухтаров Руслан ст. гр. ПИ-430Б</p>

        <h3 style="color:#16a085;">Инструкция для пользователя:</h3>
        <ul style="font-size:13px;">
        <li>Запустите симуляцию кнопкой <b>▶️ Запустить</b>.</li>
        <li>Для остановки используйте кнопку <b>⏹ Остановить</b>.</li>
        <li>Можно аварийно вывести доки из строя или починить их по одному или все сразу.</li>
        <li>Следите за графиками очереди, загрузки и общего числа погруженных грузовиков.</li>
        </ul>
        """)
        text.setReadOnly(True)
        layout_desc.addWidget(text)
        self.tab_desc.setLayout(layout_desc)
        self.tabs.addTab(self.tab_desc, "🧭 Описание")

        # -------------------------- Вкладка анимации --------------------------
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
        self.btn_emergency_single = QPushButton("💥 Сломать")
        self.btn_repair_single = QPushButton("🧰 Починить")
        self.slider_arrival = QSlider(Qt.Orientation.Horizontal)
        self.slider_arrival.setRange(1, 50)
        self.slider_arrival.setValue(int(TRUCK_ARRIVAL_PROB*1000))
        v_controls.addWidget(self.btn_start)
        v_controls.addWidget(self.btn_stop)
        v_controls.addWidget(self.btn_emergency_all)
        v_controls.addWidget(self.btn_repair_all)
        v_controls.addWidget(QLabel("Выбор дока:"))
        v_controls.addWidget(self.dock_combo)
        v_controls.addWidget(self.btn_emergency_single)
        v_controls.addWidget(self.btn_repair_single)
        v_controls.addWidget(QLabel("Скорость появления грузовиков"))
        v_controls.addWidget(self.slider_arrival)
        h_layout.addLayout(v_controls)

        self.tab_anim.setLayout(h_layout)
        self.tabs.addTab(self.tab_anim, "🚛 Анимация")

        # -------------------------- Вкладка графиков --------------------------
        self.tab_graphs = QWidget()
        v_graph = QVBoxLayout()
        self.pg_plot = pg.PlotWidget(title="Очередь, загрузка и погружено")
        self.pg_plot_avg = pg.PlotWidget(title="Среднее ожидание")
        v_graph.addWidget(self.pg_plot)
        v_graph.addWidget(self.pg_plot_avg)
        self.tab_graphs.setLayout(v_graph)
        self.tabs.addTab(self.tab_graphs, "📊 Графики")

        # -------------------------- Сигналы --------------------------
        self.btn_start.clicked.connect(self.start)
        self.btn_stop.clicked.connect(self.stop)
        self.btn_emergency_all.clicked.connect(self.emergency_all)
        self.btn_repair_all.clicked.connect(self.repair_all)
        self.btn_emergency_single.clicked.connect(self.emergency_one)
        self.btn_repair_single.clicked.connect(self.repair_one)
        self.slider_arrival.valueChanged.connect(self.set_arrival_prob)

        # -------------------------- Нарисуем доки --------------------------
        self.dock_items = []
        for i in range(MAX_BAYS):
            rect = self.scene.addRect(DOCK_X, 100+i*DOCK_Y_GAP, 150, 50, brush=QBrush(QColor("green")))
            self.dock_items.append(rect)

        # Красивый стиль
        self.setStyleSheet("""
            QPushButton { font-size: 14px; padding: 5px; }
            QSlider::handle { background: #3498db; width: 15px; }
            QSlider::groove { background: #bdc3c7; height: 6px; }
            QTabWidget::pane { border: 1px solid #3498db; }
        """)

    # -------------------------- Методы управления --------------------------
    def start(self):
        state["truck_id"] = 0
        self.timer.start(UPDATE_INTERVAL)

    def stop(self):
        self.timer.stop()

    def set_arrival_prob(self, val):
        global TRUCK_ARRIVAL_PROB
        TRUCK_ARRIVAL_PROB = val/1000

    def emergency_all(self):
        for i in range(MAX_BAYS):
            state["active_bays"][i] = False
        self.update_dock_colors()

    def repair_all(self):
        state["active_bays"] = [True]*MAX_BAYS
        self.update_dock_colors()
        self.move_global_queue_to_docks()

    def emergency_one(self):
        idx = self.dock_combo.currentIndex()
        state["active_bays"][idx] = False
        self.update_dock_colors()

    def repair_one(self):
        idx = self.dock_combo.currentIndex()
        state["active_bays"][idx] = True
        self.update_dock_colors()
        self.move_global_queue_to_docks()

    def update_dock_colors(self):
        for i, rect in enumerate(self.dock_items):
            if state["dock_queues"][i] and state["dock_queues"][i][0].loading:
                color = "yellow"
            else:
                color = "green" if state["active_bays"][i] else "red"
            rect.setBrush(QBrush(QColor(color)))

    # -------------------------- Основная симуляция --------------------------
    def update_simulation(self):
        if random.random() < TRUCK_ARRIVAL_PROB:
            self.add_new_truck()

        for truck in list(state["moving_trucks"]):
            truck.move_toward_target()
            if truck.x() > 1200:
                self.scene.removeItem(truck)
                if truck in state["moving_trucks"]:
                    state["moving_trucks"].remove(truck)

        for i, queue in enumerate(state["dock_queues"]):
            if queue:
                truck = queue[0]
                if not truck.loading and state["active_bays"][i]:
                    if abs(truck.x() - truck.target_x) < 1 and abs(truck.y() - truck.target_y) < 1:
                        truck.loading = True
                        truck.start_time = time.time()
                if truck.loading and not state["active_bays"][i]:
                    truck.loading = False
                    truck.progress.setRect(0, truck.rect().height()+2, 0, 5)
                    truck.setBrush(QBrush(QColor(truck.color)))
                elif truck.loading and state["active_bays"][i] and (time.time() - truck.start_time >= truck.load_time):
                    self.finish_truck(truck, i)

        self.move_global_queue_to_docks()
        self.update_truck_table()
        self.update_graphs()

    # -------------------------- Логика грузовиков --------------------------
    def add_new_truck(self):
        state["truck_id"] += 1
        truck_type = random.choice(list(TRUCK_TYPES.keys()))
        truck = Truck(state["truck_id"], truck_type)
        truck.setPos(50 + len(state["global_queue"])*55, 50)
        self.scene.addItem(truck)
        state["global_queue"].append(truck)
        state["moving_trucks"].append(truck)

    def assign_truck_to_dock(self):
        free_docks = [i for i, active in enumerate(state["active_bays"]) if active and len(state["dock_queues"][i])==0]
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
                wait_time = int(time.time() - truck.arrive_time) if not truck.loading else int(truck.start_time - truck.arrive_time)
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
        state["time_series"].append(len(state["time_series"]))
        queue_len = len(state["global_queue"]) + sum(len(q) for q in state["dock_queues"])
        loading = sum(1 for q in state["dock_queues"] if q and q[0].loading)
        state["waiting_trucks"].append(queue_len)
        state["loading_trucks"].append(loading)
        state["loaded_cumulative"].append(state["total_loaded"])

        self.pg_plot.clear()
        self.pg_plot.plot(list(state["waiting_trucks"]), pen=pg.mkPen('r', width=2), name="Очередь")
        self.pg_plot.plot(list(state["loading_trucks"]), pen=pg.mkPen('b', width=2), name="Погрузка")
        self.pg_plot.plot(list(state["loaded_cumulative"]), pen=pg.mkPen('g', width=2), name="Погружено")

        self.pg_plot_avg.clear()
        if state["wait_times"]:
            avg = [sum(state["wait_times"][:i+1])/len(state["wait_times"][:i+1]) for i in range(len(state["wait_times"]))]
            self.pg_plot_avg.plot(avg, pen=pg.mkPen('m', width=2), name="Среднее ожидание")

# -------------------------- Запуск --------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
