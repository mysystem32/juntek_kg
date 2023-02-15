""" Alberto - Nov 2022 """
import time

class Elapsed:
    """ class to calculate if timer has expired """

    def __init__(self, period: int):
        self.previous_time=time.time()
        self.start_time=time.time()
        self.period=period

    def set_period(self, period:int):
        """ set the period """
        self.period=period

    def check(self):
        """ check if timer has expired
            if true: set previous_time = now
        """
        now = time.time()
        delta = now - self.previous_time
        if delta < 1:
            return False

        modulus = int(self.period - (now - self.start_time) % self.period)
        if modulus == 0 or delta >= self.period:
            self.previous_time = now
            return True

        return False
