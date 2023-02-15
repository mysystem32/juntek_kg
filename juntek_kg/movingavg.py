""" Simple moving average - Alberto 2022 """
class MovingAvg:
    def __init__(self):
        """Create MovingAvg """
        self._count = 0
        self._sum = 0
        self._avg = 0
        self._min = 0
        self._max = 0

    def start(self):
        """Reset MovingAvg"""
        self.__init__()

    def reset(self):
        """Reset MovingAvg - same as start"""
        self.__init__()

    def next(self, value):
        """add a value to MovingAvg"""
        # first time?
        if self._count == 0:
            self._min = self._max = value
        #else:
        if value > self._max:
            self._max = value
        if value < self._min:
            self._min = value
        self._sum += value
        self._count += 1
        self._avg = float(self._sum) / self._count
        return self._avg

    def avg(self):
        """Return the average"""
        return self._avg

    def sum(self):
        """Return the sum"""
        return self._sum

    def min(self):
        """Return the min"""
        return self._min

    def max(self):
        """Return the max"""
        return self._max

    def count(self):
        """Return the count"""
        return self._count


if __name__ == "__main__":
    print("Moving Average")
