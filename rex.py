import typing

import utils


class REXEnv:
    VALUE_UNBOUND = object()

    def __init__(self):
        self.env_stack: [dict] = [{}]
        self.matching_functions: [typing.Callable[[utils.MatchingIter, dict], bool]] = []

    def push_env(self):
        self.env_stack.append({})

    def pop_env(self):
        self.env_stack.pop(-1)

    def add_to_current_env(self, key, value):
        self.env_stack[-1][key] = value

    def get_value(self, key):
        for idx in reversed(range(len(self.env_stack))):
            ret = self.env_stack[idx].get(key, REXEnv.VALUE_UNBOUND)
            if ret != REXEnv.VALUE_UNBOUND:
                return ret

    def match_value(self, key, value):
        last_value = self.get_value(key)
        if last_value == REXEnv.VALUE_UNBOUND:
            self.add_to_current_env(key, value)
            return True
        else:
            return last_value == value

    def __enter__(self):
        self.push_env()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pop_env()


class REX:
    def __init__(self, func):
        self.func = func

    def match(self, l, env=None):
        env = env or {}
        if not isinstance(l, utils.MatchingIter):
            ll = utils.MatchingIter(l)
        else:
            ll = l
        return self.func(ll, env)


class REXFunc:
    def __init__(self):
        pass

    ty = typing.Callable[[utils.MatchingIter, REXEnv], typing.Optional[tuple[utils.MatchingIter, REXEnv]]]

    @staticmethod
    def end():
        def is_end(it: utils.MatchingIter, env):
            if it.is_end():
                return it, env

        return is_end

    @staticmethod
    def with_env(name: str, func):
        def with_env(it: utils.MatchingIter, env: REXEnv):
            env.push_env()
            rit, renv = func(it, env)
            clip = it.clip(rit.idx)
            env.match_value()
            env.pop_env()


def test():
    protocol = REXFunc.with_env("protocol", REXFunc.or_(REXFunc.match_nfa("{}{}{}{}[(){}]", "h", "t", "t", "p", "s")))
    digits = utils.FunctionWithName(is_digits_0_to_255, "ip_digits")
    digits_4x = REXFunc.seq(
        REXFunc.with_env("digits0", digits), REXFunc.eq('.'),
        REXFunc.with_env("digits1", digits), REXFunc.eq('.'),
        REXFunc.with_env("digits2", digits), REXFunc.eq('.'),
        REXFunc.with_env("digits3", digits))
    rex = REXFunc.seq(protocol, REXFunc.eq_list('://'), digits_4x, REXFunc.end())
    result_env = rex.match("https://114.114.114.114", env={})
    print(result_env)
