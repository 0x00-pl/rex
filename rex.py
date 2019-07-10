import typing

import utils


class REXEnv:
    VALUE_UNBOUND = object()

    def __init__(self, prev_env=None):
        self.data = {}
        self.prev_env = prev_env

    def fork(self):
        return REXEnv(prev_env=self)

    def get_value(self, key, default=None):
        cur = self.data.get(key, REXEnv.VALUE_UNBOUND)
        if cur != REXEnv.VALUE_UNBOUND:
            return cur
        elif self.prev_env:
            return self.prev_env.get_value(key, default)
        else:
            return default

    def match_value(self, key, value):
        val = self.get_value(key, REXEnv.VALUE_UNBOUND)
        if val == REXEnv.VALUE_UNBOUND:
            self.data[key] = value
            return True
        else:
            return val == value


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
            else:
                return None

        return is_end

    @staticmethod
    def with_env(name: str, func):
        def with_env(it: utils.MatchingIter, env: REXEnv):
            fr = func(it, env)
            if fr is None:
                return None
            clip = it.clip(fr[0].idx)
            if env.match_value(name, clip):
                return fr
            else:
                return None

        return with_env

    @staticmethod
    def or_(*args):
        def or_(it: utils.MatchingIter, env: REXEnv):
            for func in args:
                new_env = env.fork()
                fr = func(it, new_env)
                if fr is None:
                    continue
                else:
                    return fr
            else:
                return None

        return or_

    @staticmethod
    def seq(*args):
        def seq(it: utils.MatchingIter, env: REXEnv):
            env = env.fork()
            for func in args:
                fr = func(it, env)
                if fr is None:
                    return None
                else:
                    it, env = fr
            return it, env

        return seq

    @staticmethod
    def eq(val):
        def eq(it: utils.MatchingIter, env: REXEnv):
            if it.get() == val:
                new_it = it.clone()
                new_it.move_delta(1)
                return new_it, env
            else:
                return None

        return eq

    @staticmethod
    def eq_list(val_list):
        val_list_len = len(val_list)

        def eq_list(it: utils.MatchingIter, env: REXEnv):
            if it.clip(it.idx + val_list_len) == val_list:
                new_it = it.clone()
                new_it.move_delta(val_list_len)
                return new_it, env
            else:
                return None

        return eq_list


def test():
    protocol = REXFunc.with_env("protocol", REXFunc.or_(REXFunc.match_nfa("{}{}{}{}[(){}]", "h", "t", "t", "p", "s")))
    digits = utils.FunctionWithName(is_digits_0_to_255, "ip_digits")
    digits_4x = REXFunc.seq(
        REXFunc.with_env("digits0", digits), REXFunc.eq('.'),
        REXFunc.with_env("digits1", digits), REXFunc.eq('.'),
        REXFunc.with_env("digits2", digits), REXFunc.eq('.'),
        REXFunc.with_env("digits3", digits))
    rex = REX(REXFunc.seq(protocol, REXFunc.eq_list('://'), digits_4x, REXFunc.end()))
    result_env = rex.match("https://114.114.114.114", env={})
    print(result_env)
