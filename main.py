import threading
import time
import random
from queue import PriorityQueue, Empty
import logging

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
DEADLINE_OFFSET = 8  # дедлайн = время прибытия + offset

# События для завершения симуляции
stop_simulation = threading.Event()

class Truck:
    def __init__(self, truck_id, arrival_time):
        self.id = truck_id
        self.arrival_time = arrival_time
        self.deadline = arrival_time + DEADLINE_OFFSET
        self.loading_time = random.uniform(LOADING_TIME_MIN, LOADING_TIME_MAX)
        self.priority = self.deadline  # чем раньше дедлайн — тем выше приоритет

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
            if self.busy:
                return False
            self.busy = True

        logging.info(f"Док {self.id}: начало погрузки {truck}")
        time.sleep(truck.loading_time)  # имитация погрузки
        current_time = time.time() - sim_start_time

        if current_time > truck.deadline:
            logging.warning(f"Док {self.id}: ПРОПУЩЕН ДЕДЛАЙН для {truck} (текущее время: {current_time:.1f})")
        else:
            logging.info(f"Док {self.id}: успешно завершена погрузка {truck}")

        with self.lock:
            self.busy = False
        return True

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
        truck_counter += 1
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

        # Найти свободный док
        dock_assigned = False
        while not dock_assigned and not stop_simulation.is_set():
            for dock in docks:
                if not dock.busy:
                    # Запускаем погрузку в отдельном потоке
                    threading.Thread(target=dock.load_truck, args=(truck,), daemon=True).start()
                    dock_assigned = True
                    break
            if not dock_assigned:
                time.sleep(0.1)  # ждём освобождения дока


sim_start_time = time.time()

# Запуск генератора грузовиков и планировщика
gen_thread = threading.Thread(target=truck_generator, daemon=True)
sched_thread = threading.Thread(target=scheduler, daemon=True)

gen_thread.start()
sched_thread.start()

logging.info("Симуляция запущена. Ожидание...")
time.sleep(SIMULATION_TIME)

stop_simulation.set()
logging.info("Симуляция завершена.")

