#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Time : 2020/9/25 21:16
# Author: Zheng Shaoxiang
# @Email : zhengsx95@163.com
# Description:
from gurobipy import *
import itertools
import random
from pricing import Pricing as Pr
from graph import Graph


class Enumeration:
    def __init__(self, lst):
        self.lst = lst

    def gen_indices(self):
        return []

    def sr_inequality(self):
        return self.gen_indices()


class CompleteEnumerate(Enumeration):
    def __init__(self, lst):
        super().__init__(lst)

    def gen_indices(self):
        return tuple(itertools.combinations(self.lst, 3))


class RandomEnumerate(Enumeration):
    def __init__(self, lst, n):
        super().__init__(lst)
        self.n = n

    def gen_indices(self):
        combination = list(itertools.combinations(self.lst, 3))
        random.shuffle(combination)
        return tuple(combination[:self.n])


class SeparateEnumerate(Enumeration):
    def __init__(self, lst):
        super().__init__(lst)

    def gen_indices(self):
        ans = []
        for i, item in enumerate(self.lst):
            ans.append(item)
            if i % 3 == 2:
                yield tuple(ans)
                ans = []


class MasterModel:
    def __init__(self, data, add_cuts=False):
        self.model = Model("1D-BPP")  # restricted master problem
        self.data = data
        self.add_cuts = add_cuts  # add inequalities or not
        self.pricing = None  # Pricing class
        self.x = None  # x variables
        self.var_num = self.data.n  # number of variables
        self.constraints, self.sr = None, None  # constraints
        self.s = None  # sr inequality index ((1, 2, 3), (4, 5, 6),...)
        self.graph = Graph()  # 初始化无向图定义不相容的边
        self.item_id = [item.id for item in self.data.items]  # item_id
        if add_cuts:
            self.initialize_param()
        self.initialize_model()

        self.pricing = self.get_pricing_instance()

    def initialize_param(self, enu_class=SeparateEnumerate):
        enu = enu_class(self.item_id)
        self.s = tuple(enu.sr_inequality())

    def setObjective(self, expr, sense):
        self.model.setObjective(expr, sense)

    def add_col(self, coe):
        col = Column(coe, self.model.getConstrs())
        self.var_num += 1
        self.model.addVar(vtype=GRB.CONTINUOUS, obj=1, column=col, name=f"x[{self.var_num}]")

    def initialize_model(self):
        self.x = self.model.addVars(tuple(range(1, self.data.n + 1)),
                                    vtype=GRB.CONTINUOUS, name="x")
        self.constraints = self.model.addConstrs(
            (self.x[i] == 1 for i in range(1, self.data.n + 1)), name="exact")

        self.setObjective(self.x.sum(), GRB.MINIMIZE)
        if self.add_cuts:

            self.sr = self.model.addConstrs((0 <= 1 for _ in self.s), name="sr")

            for c in self.sr.values():
                c.setAttr("RHS", 1)
        self.model.update()
        self.set_parameters()

    def set_parameters(self):
        self.model.Params.OutputFlag = False

    def optimize(self):
        self.model.optimize()

    def get_reduced_cost(self):
        return self.pricing.get_reduced_cost()

    def get_status(self):
        return self.model.status

    def get_objVal(self):
        return self.model.objVal

    def getVars(self):
        return self.model.getVars()

    def optimize_pricing(self, ex_dual, sr_dual):
        self.pricing.solve(ex_dual, sr_dual, self.data, self.graph)

    def get_pricing_instance(self):
        return Pr(self.s)

    def get_dual(self):
        exact, sr = [], []
        for c in self.constraints.values():
            exact.append(c.getAttr(GRB.Attr.Pi))

        if self.sr is not None:
            for c in self.sr.values():
                sr.append(c.getAttr(GRB.Attr.Pi))
        return exact, sr

    def get_pricing_coe(self):
        return self.pricing.get_coe()

    def removeConstrById(self, constraint_id):
        self.model.remove(self.constraints[constraint_id])

    def removeVarById(self, var_id):
        self.model.remove(self.x[var_id])


if __name__ == '__main__':
    pass
