#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Time : 2020/9/25 21:10
# Author: Zheng Shaoxiang
# @Email : zhengsx95@163.com
# Description:
from myQueue import MyQueue
from bpNode import Node
from masterModel import MasterModel
from solution import Solution
from columnGeneration import ColumnGeneration as CG
from uti import is_integer
from instance import Item
from copy import deepcopy


class Brancher:
    def __init__(self):
        pass

    def generate_branches(self, node):
        return []

    def branching(self, node):
        return self.generate_branches(node)


class BinaryBranch(Brancher):
    @ staticmethod
    def find_items(node):
        """
        :param node: list[Gurobi.var,...]
        :return:
        """
        x, y = None, None
        items = node.rmp.data.items
        sols = {v.varName: v for v in node.get_solution()}
        min_value = float("inf")
        for ind, item in enumerate(items):
            for _ind, _item in enumerate(items):
                if ind >= _ind:
                    continue

                if node.p.get((item.id, _item.id), None) is None:
                    continue

                miu = sum(sols.get(f"x[{p}]", 0) for p in node.p[item.id, _item.id])

                if not is_integer(miu):
                    if is_integer(miu - 0.5):  # miu == 0.5
                        return item, _item
                    if abs(miu - 0.5) < min_value:
                        min_value = abs(miu - 0.5)
                        x, y = item, _item

        return x, y

    def generate_branches(self, node):
        item1, item2 = self.find_items(node)  # 找到两个item
        return [BranchDecisions(item1, item2, 1), BranchDecisions(item1, item2, 0)]


class BranchDecisions:
    def __init__(self, item1, item2, value):
        """
        :param item1: Item(id width)
        :param item2:
        :param value: binary parameter 1 indicate item1 and item2 must be packed in a bin
        """
        self.item1 = item1
        self.item2 = item2
        self.value = value

    def apply(self, node):
        # fixme: 简单使用了深拷贝
        new_node = deepcopy(node)
        if self.value == 1:  # item1和item2必须在同一pattern中
            changed_index, changed_item = -1, None
            items = node.rmp.data.items
            # 1.在items集合中合并item1和item2
            for i, item in enumerate(items):  # 默认合并到最靠前的item
                if item == self.item1:
                    changed_item = Item(id=item.id, width=item.width + self.item2.width)
                    changed_index = i
                if item == self.item2:
                    new_node.rmp.data.n -= 1
                    new_node.rmp.data.items = \
                        items[:changed_index] + [changed_item] + items[changed_index + 1:i] + items[i + 1:]
                    break
            # 2.在冲突集合中删除包含item2的元组,并将所有连接到item2的边转移到item1中
            graph = new_node.rmp.graph
            for connect_node in graph.neighbors(self.item2.id):  # 所有与item2连接的点
                graph.has_edge(connect_node, self.item1.id)  # 转移边
            graph.remove_node(self.item2.id)  # 删除节点item2以及连接的所有边
            assert new_node.rmp.graph is graph

            # 3.在rmp中删除item2对应的行以及所有只包含item1和item2其中一个的列,并更新node.q
            new_node.removeConstrById(self.item2.id)
            for q in node.q[self.item1.id, self.item2.id]:
                # fixme:未更新q 考虑捕捉该函数异常
                new_node.rmp.removeVarById(q)

        elif self.value == 0:
            # 1.添加冲突集合中的item1和item2
            new_node.rmp.graph.add_edge(self.item1.id, self.item2.id)
            # 2.删除rmp中同时包含item1和item2的列
            for p in new_node.p[self.item1.id, self.item2.id]:
                # fixme:未更新p 考虑捕捉该函数异常
                new_node.rmp.removeVarById(p)
        else:
            raise ValueError("")
        new_node.level += 1
        return new_node

    def __repr__(self):
        s = 'must' if self.value == 1 else 'cannot'
        return f'{self.item1} and {self.item2}' + s + ' be packed in a bin'


class SearchTree:
    def __init__(self, instance):
        self.instance = instance
        self.queue = MyQueue()  # 初始化列表，默认深度优先（depth-first）
        self.incumbent = Solution()  # 初始化最优解

    def solve(self):
        m = MasterModel(self.instance)  # 初始化限制主问题(restrict master problem, RMP)
        node = Node(m)  # 初始化根节点
        self.queue.push(node)  # 节点入队列

        while not self.queue.empty():
            node = self.queue.pop()  # 弹出节点

            # 列生成求解该节点对应的RMP
            cg = CG(node)
            node.solution = cg.solve()  # 返回列生成求解的结果

            print(f"{node.solution=}")
            if node.should_be_pruned(self.incumbent):  # 如果该结点不应该继续分支，结束当前循环，且更新incumbent, if any
                continue

            branches = BinaryBranch().branching(node)
            for branch in branches:  # 结点分支定添加进入队列
                self.queue.push(branch.apply(node))


if __name__ == '__main__':
    pass
