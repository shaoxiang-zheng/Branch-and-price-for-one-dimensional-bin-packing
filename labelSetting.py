#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Time: 2020/9/28 11:15
# Author: Zheng Shaoxiang
# @Email: zhengsx95@163.com
# Description:
from uti import ComparisonEpsilon
import heapq
from gurobipy import *


class Label:
    def __init__(self, data, s, miu, lamb, o=None, j=-1, w=0, c=1.0, v=None,  r=None, z=None):
        self.data = data
        self.n = len(self.data.items)
        self.s = s  # ((1, 2, 3),...)
        self.j = j  # 部分解中最后一个被考虑的物品的索引
        self.w = w  # 部分解的物品总尺寸
        self.c = c  # 部分解的reduced cost
        self.miu, self.lamb = miu, lamb  # miu: list[int] lamb: {(1, 2, 3): float}
        self.v = v if v is not None else []  # 部分解中包含的item索引
        self.o = o if o is not None else list(range(self.n))  # 剩下{j+1, j+2,...,n - 1}中尺寸可以放得下的item索引
        self.r = r if r is not None else {i: 0 for i in s}  # binary source {(1, 2, 3): 0}
        self.z = z if z is not None else [0] * len(lamb)  # sr inequality的系数

    def __repr__(self):
        return f"Label(j={self.j}, w={self.w}, c={self.c}, V={self.v}, " \
               f"O={self.o}, R={self.r}), z={self.z}"

    def __eq__(self, other):
        return abs(self.c - other.c) <= ComparisonEpsilon

    def __le__(self, other):
        return self.c <= other.c + ComparisonEpsilon

    def __gt__(self, other):
        return not self.__le__(other)

    def __ge__(self, other):
        return self.c + ComparisonEpsilon >= other.c

    def __lt__(self, other):
        return not self.__ge__(other)

    def dominate(self, other):
        assert isinstance(other, Label)
        if self.w > other.w:
            return False
        if self.j != other.j:
            return False
        if self.c - sum(self.lamb[s] for s in self.r if self.r[s] == 1 and other.r[s] == 0) > \
                other.c - sum(self.miu[i] for i in other.o if i not in self.o):
            return False
        return True

    def should_be_fathomed(self):
        if self.c + ComparisonEpsilon >= 0 and not self.o:
            return True

        lower = Model("lower")
        z = lower.addVars(self.o, vtype=GRB.BINARY, name="z")
        lower.addConstr(quicksum(z[i] * self.data.items[i].width for i in self.o),
                        GRB.LESS_EQUAL, self.data.capacity - self.w, name='c')
        lower.setObjective(quicksum(-self.miu[i] * z[i] for i in self.o), GRB.MINIMIZE)
        lower.Params.OutputFlag = 0
        lower.optimize()

        if lower.objVal + self.c + ComparisonEpsilon >= 0:
            return True
        return False

    def extend(self, i, graph, v=1):
        """
        :param i: the index to be considered
        :param graph: Graph()
        :param v: 1 indicates that item i should be packed, 0 otherwise
        :return:
        """
        if v == 0:
            return Label(self.data, self.s, self.miu, self.lamb,
                         j=i, w=self.w, c=self.c, v=self.v, o=self.o[1:], r=self.r, z=self.z)
        else:
            items, capacity = self.data.items, self.data.capacity
            z = self.z[:]
            c = self.c - self.miu[i]
            r = {}
            sum_lamb = 0
            k = -1
            for s, b in self.r.items():
                k += 1
                if items[i].id not in s:
                    r[s] = b
                else:
                    r[s] = (b + 1) % 2
                    if b == 1:
                        sum_lamb += self.lamb[s]
                        z[k] = 1
            c -= sum_lamb
            o = [h for h in self.o[1:] if self.w + items[i].width + items[h].width <= capacity and
                 items[h].id not in graph.neighbors(items[i].id)]

            return Label(self.data, self.s, self.miu, self.lamb, j=i,
                         w=self.w + items[i].width, c=c, v=self.v + [i], o=o, r=r, z=z)


class LabelSetting:
    def __init__(self, data, s, miu, lamb, graph, verbose=False):
        """
        :param data:
        :param s: # [(1, 2, 3),...]
        :param miu: list[]
        :param lamb: list[]
        :param graph: Graph()
        """
        self.data = data
        self.s = s if s is not None else []  # se inequalities index
        self.miu = miu  # dual value of exact constraints
        self.lamb = {key: value for key, value in zip(s, lamb)} if s is not None else {}  # sr dual value
        self.graph = graph
        self.labels = []  # all completed labels
        self.verbose = verbose

    @ staticmethod
    def update(labels):
        n_dominated = [0] * len(labels)  # 记录每个label dominated的次数
        for ind, label in enumerate(labels):
            for _ind, _label in enumerate(labels):
                if ind < _ind:
                    dominate = dominated = False
                    # 如果两个label支配则不删除
                    if label.dominate(_label):
                        dominate = True
                    if _label.dominate(label):
                        dominated = True
                    if dominate and dominated:
                        pass  # 相互支配
                    elif dominate:
                        n_dominated[_ind] += 1
                    elif dominated:
                        n_dominated[ind] += 1
        return [label for i, label in enumerate(labels) if n_dominated[i] == 0]

    def filter(self, delta=5):

        self.labels = heapq.nsmallest(delta, self.labels)

    def solve(self):
        n = len(self.data.items)
        label = Label(self.data, self.s, self.miu, self.lamb)   # 初始化label

        labels = {i: [] for i in range(-1, n)}  # {i: [Label()]} all labels with last considered item being index i
        labels[-1] = [label]
        for j in range(-1, n):
            if self.verbose:
                print(f"\n{j=}")
                print(f"before dominated there are {len(labels[j])} labels")
            labels[j] = self.update(labels[j])  # filter the set by dominance rule
            if self.verbose:
                print(f"after dominated there are {len(labels[j])} labels")
            for label in labels[j]:
                if not label.o:  # 不存在待考虑item
                    if self.verbose:
                        print(f"The label is completed: {label}")
                    heapq.heappush(self.labels, label)
                else:
                    i = label.o[0]  # 下一个待考虑item index
                    if self.verbose:
                        print(f"item index = {i} item id = {self.data.items[i].id} is considered")

                    for v in [1, 0]:
                        if self.verbose:
                            print(f"item id = {self.data.items[i].id} is " + ('packed' if v == 1 else 'discarded'))
                        new_label = label.extend(i, self.graph, v=v)
                        if self.verbose:
                            print(f"The new label is {new_label}")
                        if not new_label.should_be_fathomed():
                            labels[i].append(new_label)
                        elif self.verbose:
                            print("The label if fathomed")

        self.filter()
        return self.labels


if __name__ == '__main__':
    pass
