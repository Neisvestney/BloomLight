from __future__ import annotations

import logging
import pickle
from typing import TypeVar, Type, Generic


class ConfigManager:
    def __init__(self, external: type):
        self.external = external
        self.fields = [(f, external.__getattribute__(f)) for f in dir(external) if type(external.__getattribute__(f)) == Field]
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
    def __init__(self, value_fn, set_fn, data_type: Type[T]) -> T:
        self.value_fn = value_fn
        self.set_fn = set_fn
        self.data_type = data_type
