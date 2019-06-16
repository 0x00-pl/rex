import collections
import typing
import utils


class NFA:
    # (list, index) -> (matched, index_delta)
    transition_builder_type = typing.Callable[[typing.Sequence[typing.Any], int], typing.Tuple[bool, int]]

    class Edge:
        def __init__(self, transition_builder: 'NFA.transition_builder_type', dst: 'NFA.Node', name=None):
            self.transition_builder = transition_builder
            self.dst = dst
            self.name = name

    eps_builder: transition_builder_type = utils.FunctionWithName(lambda l, idx: (True, 0), 'eps')

    class Node:
        def __init__(self, edges: typing.AbstractSet['NFA.Edge'] = None):
            self.edges: typing.MutableSet['NFA.Edge'] = set(edges) if edges is not None else set()

        def copy(self):
            return NFA.Node(self.edges)

        def add_edges(self, edges: typing.AbstractSet['NFA.Edge']):
            self.edges |= edges

        def add_eps_edge(self, node: 'NFA.Node'):
            self.edges.add(NFA.Edge(NFA.eps_builder, node, 'eps'))

        def discard_edge(self, edge: 'NFA.Edge'):
            self.edges.discard(edge)

        def __str__(self):
            ret = ''
            for edge in self.edges:
                ret += str(id(self)) + ' --> ' + str(id(edge.dst)) + (' : ' + edge.name if edge.name else '') + '\n'

            return ret

    def __init__(self, nodes: typing.AbstractSet['NFA.Node'], start_node: 'NFA.Node',
                 end_nodes: typing.AbstractSet['NFA.Node']):
        self.nodes = set(nodes)
        self.start_node = start_node
        self.end_nodes = set(end_nodes)

    def gc_nodes(self):
        keep_nodes = {self.start_node}
        edge_nodes = {self.start_node}
        while len(edge_nodes) > 0:
            item = edge_nodes.pop()
            for edge in item.edges:
                dest = edge.dst
                if dest not in keep_nodes:
                    keep_nodes.add(dest)
                    edge_nodes.add(dest)

        self.nodes = keep_nodes

    def eliminate_eps(self):
        edges_need_be_removed = set()
        for node in self.nodes:
            for edge in node.edges:
                if edge.transition_builder == self.eps_builder:
                    edges_need_be_removed.add((node, edge))
                    break

        for src_node, edge in edges_need_be_removed:
            src_node.add_edges(edge.dst.edges)
            src_node.discard_edge(edge)

        self.gc_nodes()

    def copy(self):
        mapping: typing.MutableMapping['NFA.Node', 'NFA.Node'] = {}
        for node in self.nodes:
            mapping[node] = node.copy()

        # relink
        for new_node in mapping.values():
            for edge in new_node.edges:
                edge.dst = mapping[edge.dst]

        return NFA(set(mapping.values()), mapping[self.start_node], set(mapping[i] for i in self.end_nodes))

    def __str__(self):
        ret = 'https://www.planttext.com/\n@startuml\n\n'
        ret += str(id(self.start_node)) + ' : start\n'
        for node in self.end_nodes:
            ret += str(id(node)) + ' : end\n'

        for node in self.nodes:
            ret += str(node)
        ret += '\n@enduml\n'
        return ret


def make_seq_nfa(transition_builder_list: typing.Sequence[typing.Union[NFA.transition_builder_type, NFA]]):
    ret_start = NFA.Node()
    ret_ends: typing.Set[NFA.Node] = {ret_start}
    ret_nodes: typing.Set[NFA.Node] = {ret_start}
    for transition_builder in transition_builder_list:
        if isinstance(transition_builder, NFA):
            transition_nfa = transition_builder.copy()
            ret_nodes |= transition_nfa.nodes
            for ret_end in ret_ends:
                ret_end.add_eps_edge(transition_nfa.start_node)

            ret_ends = transition_nfa.end_nodes
        else:
            new_end = NFA.Node()
            ret_nodes.add(new_end)
            for ret_end in ret_ends:
                ret_end.add_edges({NFA.Edge(transition_builder, new_end, str(transition_builder))})
            ret_ends = {new_end}

    ret = NFA(ret_nodes, ret_start, ret_ends)
    ret.eliminate_eps()
    return ret


def make_or_nfa(transition_builder_list: typing.Sequence[typing.Union[NFA.transition_builder_type, NFA]]):
    ret_start = NFA.Node()
    ret_ends: typing.Set[NFA.Node] = set()
    ret_nodes: typing.Set[NFA.Node] = {ret_start}
    for transition_builder in transition_builder_list:
        if isinstance(transition_builder, NFA):
            tmp = transition_builder.copy()
            ret_nodes |= tmp.nodes
            ret_start.add_eps_edge(tmp.start_node)
            ret_ends |= tmp.end_nodes
        else:
            new_end = NFA.Node()
            ret_start.add_edges({NFA.Edge(transition_builder, new_end, str(transition_builder))})
            ret_nodes.add(new_end)
            ret_ends |= {new_end}

    ret = NFA(ret_nodes, ret_start, ret_ends)
    ret.eliminate_eps()
    return ret


class builders:
    any_obj = object()

    @staticmethod
    def make_transition_builder(obj):
        if isinstance(obj, NFA):
            return obj
        elif id(obj) == id(builders.any_obj):
            return utils.FunctionWithName(lambda l, i: (True, 1), '.')
        else:
            return utils.FunctionWithName(lambda l, i: (True, 1) if l[i] == obj else (False, 0),
                                          '<' + str(obj) + '>')


class matching_iter:
    def __init__(self, exp_nfa: NFA, node: NFA.Node, target: typing.Sequence[typing.Any], idx: int):
        self.exp_nfa = exp_nfa
        self.node = node
        self.target = target
        self.idx = idx

    def update(self, idx_delta: int):
        self.idx += idx_delta

    def at_end(self):
        return len(self.target) == self.idx

    def __str__(self):
        ret = str(id(self.node))
        ret += ' target[' + str(self.idx) + ']'
        return ret


def nfa_match(exp_nfa: NFA, target: typing.Sequence[typing.Any]):
    iter_set = collections.deque({matching_iter(exp_nfa, exp_nfa.start_node, target, 0)})
    while not len(iter_set) == 0:
        item = iter_set.pop()
        print('[debug] matching idx', item.idx)

        for edge in item.node.edges:
            try:
                res, delta = edge.transition_builder(item.target, item.idx)
            except IndexError:
                res, delta = False, 0

            if res:
                if edge.dst in exp_nfa.end_nodes:
                    return True
                iter_set.append(matching_iter(exp_nfa, edge.dst, item.target, item.idx + delta))

    return False


class nfa_arguments:
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


class nfa_builder:
    def __init__(self, s: str, args: nfa_arguments):
        self.args = args
        self.s = s
        self.s_idx = 0

    def get_ch(self, offset=0):
        if self.s_idx >= len(self.s):
            return None
        ret = self.s[self.s_idx]
        self.s_idx += offset
        return ret

    def nfa_read_name(self):
        name = ''
        self.get_ch(1)  # for '{'
        while self.get_ch() != '}':
            name += self.get_ch(1)

        self.get_ch(1)  # for '}'
        return name

    def nfa_build_list(self):
        ret = []
        while self.get_ch() not in (']', ')', None):
            if self.get_ch() == '{':
                name = self.nfa_read_name()
                ret.append(self.args.get(name))
            elif self.get_ch() == '[':
                ret.append(self.nfa_build_or_list())
            elif self.get_ch() == '(':
                ret.append(self.nfa_build_seq_list())
        return ret

    def nfa_build_or_list(self):
        self.get_ch(1)  # for '['
        ret = self.nfa_build_list()
        self.get_ch(1)  # for ']'
        return make_or_nfa(ret)

    def nfa_build_seq_list(self):
        self.get_ch(1)  # for '('
        ret = self.nfa_build_list()
        self.get_ch(1)  # for ')'
        return make_seq_nfa(ret)

    def nfa_build(self):
        return make_seq_nfa(self.nfa_build_list())


def nfa_test():
    target = [1, 2, 3, 4]
    # exp_nfa_inner = make_or_nfa([builders.make_transition_builder(i) for i in [4, 5]])
    # print('exp_nfa_inner: ', str(exp_nfa_inner))
    # exp_nfa = make_seq_nfa([builders.make_transition_builder(i) for i in [1, 2, builders.any_obj, exp_nfa_inner]])
    # print('exp_nfa: ', str(exp_nfa))

    # args = nfa_arguments().add_list([builders.make_transition_builder(i) for i in [1, 2, 3, 4, 5]])
    args = nfa_arguments().add_dict({str(i): builders.make_transition_builder(i) for i in [1, 2, 3, 4, 5]})
    builder_nfa = nfa_builder('{1}[{2}][({3}{4}){5}]', args).nfa_build()
    print('builder_nfa_nfa: ', str(builder_nfa))
    res = nfa_match(builder_nfa, target)
    print('matching result:', res)


class env_stack:
    no_value = {}

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
nfa_test()
