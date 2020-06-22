import time


class Holder(object):
    def __init__(self, min_time=0.0, freq=2.0, add=0.1, sub=0.05):
        self.min_time = min_time
        self.freq = freq
        self.add = add
        self.sub = sub
        self.first_evoke_time = 0
        self.evoke_counter = 0
        self.hold_time = 0

    def evoke(self):
        time.sleep(self.min_time)
        time.sleep(self.hold_time)
        if 1/(time.time()-self.first_evoke_time + 0.00000001) > self.freq:
            self.hold_time = self.hold_time + self.add
        else:
            self.hold_time = self.hold_time - self.sub*((time.time()-self.first_evoke_time + 0.00000001)/(1/self.freq))
            if self.hold_time < 0:
                self.hold_time = 0
            self.reset()

    def reset(self):
        self.first_evoke_time = time.time()
        self.evoke_counter = 0


if __name__ == '__main__':
    h = Holder(freq=0.1)
    counter = 0
    while True:
        print(counter)
        h.evoke()
        counter = counter + 1
