import collections
import typing


class nfa:
    # () -> (list, index) -> (matched, index_delta)
    pred_builder_type = typing.Callable[
        [], typing.Callable[[typing.Sequence[typing.Any], int], typing.Tuple[bool, int]]]

    class nfa_edge:
        def __init__(self, pred_builder: 'nfa.pred_builder_type', dest: 'nfa.nfa_node'):
            self.pred_builder = pred_builder
            self.dest = dest

    eps_builder: pred_builder_type = lambda: lambda l, idx: (True, 0)

    class nfa_node:
        def __init__(self, edges: typing.AbstractSet['nfa.nfa_edge'] = None):
            self.edges: typing.MutableSet['nfa.nfa_edge'] = set(edges) if edges is not None else set()

        def add_edges(self, edges: typing.AbstractSet['nfa.nfa_edge']):
            self.edges |= edges

        def discard_edge(self, edge: 'nfa.nfa_edge'):
            self.edges.discard(edge)

    def __init__(self, nodes: typing.AbstractSet['nfa.nfa_node'], start_node: 'nfa.nfa_node',
                 end_nodes: typing.AbstractSet['nfa.nfa_node']):
        self.nodes = set(nodes)
        self.start_node = start_node
        self.end_nodes = set(end_nodes)

    def elimit_eps(self):
        edges_need_be_removed = set()
        for node in self.nodes:
            for edge in node.edges:
                if edge.pred_builder == self.eps_builder:
                    edges_need_be_removed.add((node, edge))
                    break

        for src_node, edge in edges_need_be_removed:
            src_node.add_edges(edge.dest.edges)
            src_node.discard_edge(edge)


def make_seq_nfa(pred_builder_list: typing.Sequence[typing.Union[nfa.pred_builder_type, nfa]]):
    ret_nodes: typing.Set[nfa.nfa_node] = set()
    ret_start = nfa.nfa_node()
    ret_end: nfa.nfa_node = ret_start
    for pred_builder in pred_builder_list:
        if isinstance(pred_builder, nfa):
            pred_nfa = pred_builder
            assert (len(pred_nfa.end_nodes) == 1)
            ret_nodes |= set(pred_builder.nodes)
            new_end = next(iter(pred_nfa.end_nodes))
            ret_end.add_edges({nfa.nfa_edge(nfa.eps_builder, pred_nfa.start_node)})
            ret_end = new_end
        else:
            new_end = nfa.nfa_node()
            ret_end.add_edges({nfa.nfa_edge(pred_builder, new_end)})
            ret_end = new_end

    ret = nfa(ret_nodes, ret_start, {ret_end})
    ret.elimit_eps()
    return ret




class builders:
    any_obj = object()

    @staticmethod
    def make_pred_builder(obj):
        if id(obj) == id(builders.any_obj):
            return lambda: lambda l, i: (True, 1)
        else:
            return lambda: lambda l, i: (True, 1) if l[i] == obj else (False, 0)


class matching_iter:
    def __init__(self, exp_nfa: nfa, node: nfa.nfa_node, target: typing.Sequence[typing.Any], idx: int):
        self.exp_nfa = exp_nfa
        self.node = node
        self.target = target
        self.idx = idx

    def update(self, idx_delta: int):
        self.idx += idx_delta

    def at_end(self):
        return len(self.target) == self.idx


def rex_match(exp_nfa: nfa, target: typing.Sequence[typing.Any]):
    iter_set = collections.deque({matching_iter(exp_nfa, exp_nfa.start_node, target, 0)})
    while not any(i.at_end() for i in iter_set):
        if len(iter_set) == 0:
            return False
        item = iter_set.pop()
        print('[debug] matching idx', item.idx)

        for edge in item.node.edges:
            res, delta = edge.pred_builder()(item.target, item.idx)
            if res:
                if edge.next in exp_nfa.end_nodes:
                    return True
                iter_set.append(matching_iter(exp_nfa, edge.next, item.target, item.idx + delta))


def nfa_test():
    target = [1, 2, 3, 4, 5]
    exp_nfa = make_seq_nfa([builders.make_pred_builder(i) for i in [1, 2, builders.any_obj, 4, 5]])
    res = rex_match(exp_nfa, target)
    print('matching result:', res)


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
