import simpy
import random

# ===============================
# Параметры симуляции
# ===============================
NUM_TRUCKS = 10       # Количество грузовиков
NUM_DOCKS = 2         # Количество погрузочных доков
ARRIVAL_MEAN = 3      # Среднее время между прибытием грузовиков
LOADING_MIN = 5       # Мин. время погрузки
LOADING_MAX = 10      # Макс. время погрузки

# ===============================
# Сбор статистики
# ===============================
truck_wait_times = []
truck_loading_times = []

# ===============================
# Функция для грузовика
# ===============================
def truck(env, name, dock):
    arrival_time = env.now
    print(f'{env.now:.1f}: {name} подъехал')
    
    with dock.request() as request:
        yield request
        wait_time = env.now - arrival_time
        truck_wait_times.append(wait_time)
        print(f'{env.now:.1f}: {name} заехал на док, ожидал {wait_time:.1f} ед. времени')
        
        loading_time = random.randint(LOADING_MIN, LOADING_MAX)
        truck_loading_times.append(loading_time)
        yield env.timeout(loading_time)
        print(f'{env.now:.1f}: {name} загружен за {loading_time} ед. времени и выехал')

# ===============================
# Генератор грузовиков
# ===============================
def truck_generator(env, dock):
    for i in range(NUM_TRUCKS):
        env.process(truck(env, f'Грузовик {i+1}', dock))
        yield env.timeout(random.expovariate(1.0 / ARRIVAL_MEAN))

# ===============================
# Основная симуляция
# ===============================
env = simpy.Environment()
dock = simpy.Resource(env, capacity=NUM_DOCKS)

env.process(truck_generator(env, dock))
env.run()

# ===============================
# Статистика
# ===============================
print("\n=== Статистика ===")
if truck_wait_times:
    print(f"Среднее время ожидания: {sum(truck_wait_times)/len(truck_wait_times):.2f}")
if truck_loading_times:
    print(f"Среднее время погрузки: {sum(truck_loading_times)/len(truck_loading_times):.2f}")
