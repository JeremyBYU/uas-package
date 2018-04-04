import simpy
def producer(env, store):
    for i in range(100):
        yield env.timeout(.5)
        yield store.put({'spam':  i})
        print('Produced spam at', env.now)

def consumer(name, env, store):
    while True:
        yield env.timeout(2)
        print(name, 'requesting spam at', env.now)
        item = yield store.get()
        print(name, 'got', item, 'at', env.now)

env = simpy.Environment()
store = simpy.Store(env, capacity=1)

prod = env.process(producer(env, store))
consumers = [env.process(consumer(i, env, store)) for i in range(2)]

env.run(until=5)
