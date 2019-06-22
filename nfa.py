import typing

import utils


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


class NFA:
    trans_func_type = typing.Callable[[MatchingIter], typing.Optional[int]]

    class Edge:
        def __init__(self, transition: 'NFA.trans_func_type', dst: 'NFA.Node', name=None):
            self.transition = transition
            self.dst = dst
            self.name = name

    eps_builder: trans_func_type = utils.FunctionWithName(lambda it: 0, 'eps')

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
            return str(id(self))

        def edges_to_string(self):
            ret = ''
            for edge in self.edges:
                ret += str(self) + ' --> ' + str(edge.dst) + (' : ' + edge.name if edge.name else '') + '\n'

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
                if edge.transition == self.eps_builder:
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
        for node in self.nodes:
            ret += node.edges_to_string()
        ret += str(self.start_node) + ' : start\n'
        for node in self.end_nodes:
            ret += str(node) + ' : end\n'

        ret += '\n@enduml\n'
        return ret


def make_seq_nfa(transition_list: typing.Sequence[typing.Union[NFA.trans_func_type, NFA]]):
    ret_start = NFA.Node()
    ret_ends: typing.Set[NFA.Node] = {ret_start}
    ret_nodes: typing.Set[NFA.Node] = {ret_start}
    for transition in transition_list:
        if isinstance(transition, NFA):
            transition_nfa = transition.copy()
            ret_nodes |= transition_nfa.nodes
            for ret_end in ret_ends:
                ret_end.add_eps_edge(transition_nfa.start_node)

            ret_ends = transition_nfa.end_nodes
        else:
            new_end = NFA.Node()
            ret_nodes.add(new_end)
            for ret_end in ret_ends:
                ret_end.add_edges({NFA.Edge(transition, new_end, str(transition))})
            ret_ends = {new_end}

    ret = NFA(ret_nodes, ret_start, ret_ends)
    ret.eliminate_eps()
    return ret


def make_or_nfa(transition_list: typing.Sequence[typing.Union[NFA.trans_func_type, NFA]]):
    ret_start = NFA.Node()
    ret_ends: typing.Set[NFA.Node] = set()
    ret_nodes: typing.Set[NFA.Node] = {ret_start}
    for transition in transition_list:
        if isinstance(transition, NFA):
            tmp = transition.copy()
            ret_nodes |= tmp.nodes
            ret_start.add_eps_edge(tmp.start_node)
            ret_ends |= tmp.end_nodes
        else:
            new_end = NFA.Node()
            ret_start.add_edges({NFA.Edge(transition, new_end, str(transition))})
            ret_nodes.add(new_end)
            ret_ends |= {new_end}

    ret = NFA(ret_nodes, ret_start, ret_ends)
    ret.eliminate_eps()
    return ret


class StatePool:
    def __init__(self):
        self.states = {0: set()}

    def tick(self):
        assert (len(self.states[0]) == 0)
        new_states = dict()
        for k, v in self.states.items():
            if len(v) != 0:
                new_states[k - 1] = v

        self.states = new_states

    def add_state(self, node: NFA.Node, delta: int):
        p = self.states.get(delta, set())
        p.add(node)
        self.states[delta] = p

    def pop_state(self) -> typing.Iterable[NFA.Node]:
        p = self.states.get(0, set())
        while len(p) != 0:
            yield p.pop()

    def __len__(self):
        return sum(len(v) for k, v in self.states.items())

    def __str__(self):
        ret = 'states:\n'
        for k, v in self.states.items():
            ret += '[' + str(k) + ']:' + ' '.join([str(it) for it in v]) + '\n'
        return ret


def nfa_match(nfa: NFA, target: MatchingIter):
    states = StatePool()
    states.add_state(nfa.start_node, 0)

    while len(states) > 0 and target.idx <= len(target.l):
        for state in states.pop_state():
            if state in nfa.end_nodes:
                return True

            if target.idx == len(target.l):
                return False

            for edge in state.edges:
                next_state = edge.dst
                trans_func = edge.transition
                delta = trans_func(target)
                if delta is not None:
                    states.add_state(next_state, delta)
        states.tick()
        target.move_delta(1)

    return False


class NFABuilder:
    def __init__(self, s: str, args: utils.RexArguments):
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


def test():
    nfa = NFABuilder('{}{}{}{}{}', utils.RexArguments().add_list(
        [utils.Transitions.eq(it, ()) for it in [1, 2, 3, utils.Transitions.any_obj, 5]])).nfa_build()
    print(nfa)
    match_iter = MatchingIter([1, 2, 3, 4, 5])
    match_result = nfa_match(nfa, match_iter)
    print(match_result, match_iter.is_end())

if __name__ == '__main__':
    test()
