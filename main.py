import threading
import time
import random
from queue import PriorityQueue, Empty
import logging

# === ВИЗУАЛИЗАЦИЯ: импортируем matplotlib с фиксом для Windows ===
import matplotlib
matplotlib.use('TkAgg')  # ← Критически важно для отображения окна
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)

# Глобальные параметры
NUM_DOCKS = 2
SIMULATION_TIME = 30  # секунд
TRUCK_ARRIVAL_RATE = 2  # среднее время между прибытиями (сек)
LOADING_TIME_MIN = 3
LOADING_TIME_MAX = 6
DEADLINE_OFFSET = 8  # дедлайн = время прибытия

# События для завершения симуляции
stop_simulation = threading.Event()

# === СТАТИСТИКА ===
stats_lock = threading.Lock()
stats = {
    "completed": 0,
    "missed_deadlines": 0,
    "total_trucks": 0
}

class Truck:
    def __init__(self, truck_id, arrival_time):
        self.id = truck_id
        self.arrival_time = arrival_time
        self.deadline = arrival_time + DEADLINE_OFFSET
        self.loading_time = random.uniform(LOADING_TIME_MIN, LOADING_TIME_MAX)
        self.priority = self.deadline

    def __lt__(self, other):
        return self.priority < other.priority

    def __repr__(self):
        return f"Truck-{self.id}(arr={self.arrival_time:.1f}, dl={self.deadline:.1f}, load={self.loading_time:.1f})"

class LoadingDock:
    def __init__(self, dock_id):
        self.id = dock_id
        self.busy = False
        self.lock = threading.Lock()

    def load_truck(self, truck):
        with self.lock:
            self.busy = True

        logging.info(f"Док {self.id}: начало погрузки {truck}")
        time.sleep(truck.loading_time)  # имитация погрузки
        current_time = time.time() - sim_start_time

        # === Учёт статистики ===
        with stats_lock:
            if current_time > truck.deadline:
                stats["missed_deadlines"] += 1
                logging.warning(f"Док {self.id}: ПРОПУЩЕН ДЕДЛАЙН для {truck} (текущее время: {current_time:.1f})")
            else:
                stats["completed"] += 1
                logging.info(f"Док {self.id}: успешно завершена погрузка {truck}")

        with self.lock:
            self.busy = False

# Глобальные объекты
docks = [LoadingDock(i) for i in range(NUM_DOCKS)]
truck_queue = PriorityQueue()
truck_counter = 0
sim_start_time = None

def truck_generator():
    global truck_counter
    while not stop_simulation.is_set():
        time.sleep(random.expovariate(1.0 / TRUCK_ARRIVAL_RATE))
        if stop_simulation.is_set():
            break
        with stats_lock:
            truck_counter += 1
            stats["total_trucks"] = truck_counter
        arrival_time = time.time() - sim_start_time
        truck = Truck(truck_counter, arrival_time)
        truck_queue.put(truck)
        logging.info(f"Прибыл {truck}")

def scheduler():
    while not stop_simulation.is_set():
        try:
            truck = truck_queue.get(timeout=1)
        except Empty:
            continue

        dock_assigned = False
        while not dock_assigned and not stop_simulation.is_set():
            for dock in docks:
                if not dock.busy:
                    threading.Thread(target=dock.load_truck, args=(truck,), daemon=True).start()
                    dock_assigned = True
                    break
            if not dock_assigned:
                time.sleep(0.1)

# === ФУНКЦИЯ АНИМАЦИИ ГРАФИКА ===
def start_visualization():
    """Запускает окно визуализации в основном потоке"""
    xs, ys_queue, ys_docks = [], [], []

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))
    fig.suptitle('Система погрузки грузовиков — Визуализация', fontsize=12)

    line_queue, = ax1.plot([], [], 'b-', label='Очередь')
    line_docks, = ax2.plot([], [], 'r-', label='Занятые доки')

    ax1.set_ylabel('Длина очереди')
    ax1.legend()
    ax1.grid(True)

    ax2.set_xlabel('Время (сек)')
    ax2.set_ylabel('Занятые доки')
    ax2.set_ylim(-0.1, NUM_DOCKS + 0.5)
    ax2.legend()
    ax2.grid(True)

    def animate(frame):
        current_time = time.time() - sim_start_time
        if current_time < 0:
            return

        queue_len = truck_queue.qsize()
        busy_count = sum(1 for d in docks if d.busy)

        xs.append(current_time)
        ys_queue.append(queue_len)
        ys_docks.append(busy_count)

        # Ограничиваем историю
        if len(xs) > 200:
            xs.pop(0)
            ys_queue.pop(0)
            ys_docks.pop(0)

        line_queue.set_data(xs, ys_queue)
        line_docks.set_data(xs, ys_docks)

        ax1.relim()
        ax1.autoscale_view()
        ax2.relim()
        ax2.autoscale_view()

    ani = FuncAnimation(fig, animate, interval=500, cache_frame_data=False)
    plt.tight_layout()
    plt.show(block=True)  # ← Блокирует до закрытия окна

# === ЗАПУСК СИСТЕМЫ ===
if __name__ == "__main__":
    sim_start_time = time.time()

    # Запуск фоновых потоков
    gen_thread = threading.Thread(target=truck_generator, daemon=True)
    sched_thread = threading.Thread(target=scheduler, daemon=True)

    gen_thread.start()
    sched_thread.start()

    logging.info("Симуляция запущена. Открывается окно визуализации...")
    
    # Запуск визуализации в основном потоке (это важно!)
    start_visualization()

    # После закрытия окна — завершаем симуляцию
    stop_simulation.set()

    # Итоговая статистика
    with stats_lock:
        print("\n" + "="*50)
        print("📊 ИТОГОВАЯ СТАТИСТИКА")
        print("="*50)
        print(f"Всего грузовиков:       {stats['total_trucks']}")
        print(f"Успешно загружено:      {stats['completed']}")
        print(f"Пропущено дедлайнов:    {stats['missed_deadlines']}")
        print(f"Осталось в очереди:     {truck_queue.qsize()}")
        print("="*50)

    logging.info("Симуляция завершена.")