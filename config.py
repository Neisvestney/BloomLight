from __future__ import annotations

import logging
import pickle
import time
from threading import Thread
from typing import TypeVar, Type, Generic, List


class ConfigManager:
    def __init__(self, external: type):
        self.save_thread: StoppingTimer = None
        self.external = external
        self.fields: List[tuple[str, Field]] = [(f, external.__getattribute__(f)) for f in dir(external) if type(external.__getattribute__(f)) == Field]
        [f[1].update_handler.connect(lambda: self.save_in_time()) for f in self.fields if f[1].update_handler]
        if not self.load():
            self.set()

    def set(self):
        for f in self.fields:
            self.external.__setattr__(f[0], f[1].value_fn())

    def get_save(self):
        save = Save()
        [save.__setattr__(f[0], f[1].value_fn()) for f in self.fields]
        return save

    def save(self):
        self.set()
        file = open('config.save', 'wb')
        pickle.dump(self.get_save(), file)
        file.close()
        logging.info("Save complete")

    def save_in_time(self, delay=2):
        self.set()

        if self.save_thread:
            self.save_thread.stopped = True
        self.save_thread = StoppingTimer(delay, self.save)
        self.save_thread.start()

    def load(self):
        try:
            file = open('config.save', 'rb')
        except FileNotFoundError:
            return False

        save = pickle.load(file)
        file.close()
        for v in dir(save):
            for x in self.fields:
                if v == x[0]:
                    x[1].set_fn(save.__getattribute__(v))

        self.set()
        logging.info("Load complete")
        return True


class Save:
    pass


T = TypeVar('T')


class Field(Generic[T]):
    def __init__(self, value_fn, set_fn, update_handler=None, data_type: Type[T] = object) -> T:
        self.value_fn = value_fn
        self.set_fn = set_fn
        self.update_handler = update_handler
        self.data_type = data_type


class StoppingTimer(Thread):
    def __init__(self, time_to_run, fn):
        Thread.__init__(self)
        self.time_to_run = time_to_run
        self.fn = fn
        self.stopped = False

    def run(self):
        time.sleep(self.time_to_run)
        if not self.stopped:
            self.fn()
