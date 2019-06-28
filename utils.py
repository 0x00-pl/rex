class FunctionWithName:
    def __init__(self, func, name):
        self.func = func
        self.name = name

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def __str__(self):
        return self.name

class MatchingIter:
    def __init__(self, l):
        self.l = list(l)
        self.idx = 0

    def move_delta(self, delta):
        self.idx += delta

    def get_delta(self, delta):
        return self.l[self.idx + delta]

    def get(self):
        return self.get_delta(0)

    def is_end(self):
        return self.idx == len(self.l)



class Transitions:
    any_obj = object()

    @staticmethod
    def eq(obj, exclude_types):
        for ty in exclude_types:
            if isinstance(obj, ty):
                return obj

        if obj is Transitions.any_obj:
            return FunctionWithName(lambda l: 1, '.')
        else:
            return FunctionWithName(lambda l: 1 if l.get() == obj else None,
                                    '<' + str(obj) + '>')


class RexArguments:
    def __init__(self):
        self.fetch_idx = 0
        self.value_list = []
        self.value_dict = {}

    def add(self, value, name=''):
        self.value_list.append(value)
        if name != '':
            self.value_dict[name] = value
        return self

    def add_list(self, value_list: list):
        for value in value_list:
            self.add(value)
        return self

    def add_dict(self, value_dict):
        for name, value in value_dict.items():
            self.add(value, name)
        return self

    def get(self, name=''):
        if name != '':
            return self.value_dict[name]
        idx = self.fetch_idx
        self.fetch_idx += 1
        return self.value_list[idx]
