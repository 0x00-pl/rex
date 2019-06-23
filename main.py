import nfa


class env_stack:
    no_value = object()

    def __init__(self):
        self.stack = [{}]

    def top(self):
        return self.stack[-1]

    def push(self):
        self.stack.append({})
        return self

    def pop(self):
        return self.stack.pop(-1)

    def add(self, name, value):
        self.top()[name] = value
        return self

    def get(self, name):
        for i in range(-1, -1 - len(self.stack), -1):
            if name in self.stack[i]:
                return self.stack[i].get(name)
        return env_stack.no_value

    def try_add(self, name, value):
        if self.get(name) == env_stack.no_value:
            self.add(name, value)
            return True
        elif self.get(name) == value:
            return True
        else:
            return False


def rex_make_match_item_pred(env_s: env_stack, name):
    return lambda: lambda l, idx: (True, 1) if env_s.try_add(name, l[idx]) else (False, 0)


#
#
# class rex_value:
#     def __init__(self, name):
#         self.name = name or 'no-name'
#         self.value = None
#         self.has_value = False
#
#     def try_set_value(self, value):
#         if not self.has_value:
#             self.value = value
#             self.has_value = True
#             return True
#         else:
#             return False
#
#
# class rex:
#     def test(self, obj_list):
#         pass
#
#
# class rex_constant(rex):
#     def __init__(self, pred):
#
#
# def test(reg, obj_list):
#     reg.test(obj_list)

def test():
    nfa.test()

if __name__ == '__main__':
    test()
