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
import copy


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
    def __init__(self, data, add_cuts=True, **kwargs):
        self.model = kwargs.get('model', None)  # restricted master problem
        self.data = data
        self.add_cuts = add_cuts  # add inequalities or not
        self.pricing = kwargs.get('pricing', None)  # Pricing class
        self.x = kwargs.get('x', None)  # x variables
        self.var_num = kwargs.get("var_num", None)  # number of variables
        self.constraints, self.sr = \
            kwargs.get('constraints', None), kwargs.get('sr', None)  # constraints
        self.s = kwargs.get('s', None)  # sr inequality index ((1, 2, 3), (4, 5, 6),...)
        self.graph = kwargs.get('graph', Graph())  # 初始化无向图定义不相容的边
        self.init_columns = kwargs.get("init_columns", None)
        self.item_id = [item.id for item in self.data.items]  # item_id
        if add_cuts and self.s is None:
            self.initialize_param()
        if self.model is None:
            self.model = Model("1D-BPP")
            self.initialize_model()
        if self.pricing is None:
            self.pricing = self.get_pricing_instance()

    def __copy__(self):
        """
        when copy.copy is invoked
        :return:
        """
        data = copy.deepcopy(self.data)
        assert data.items is not self.data.items

        self.model.update()
        model = self.model.copy()

        pricing = self.pricing

        x = copy.copy(self.x)
        constraints, sr = copy.copy(self.constraints), copy.copy(self.sr)
        s = self.s
        graph = copy.deepcopy(self.graph)

        return MasterModel(data=data, add_cuts=self.add_cuts, model=model, pricing=pricing, x=x,
                           constraints=constraints, sr=sr, s=s, graph=graph, var_num=self.var_num)

    def initialize_param(self, enu_class=SeparateEnumerate):
        enu = enu_class(self.item_id)
        self.s = tuple(enu.sr_inequality())

    def setObjective(self, expr, sense):
        self.model.setObjective(expr, sense)

    def add_col(self, coe):
        """

        :param coe: [[], []]
        :return:
        """
        for c in coe:
            col = Column(c, self.model.getConstrs())
            self.var_num += 1
            self.model.addVar(vtype=GRB.CONTINUOUS, obj=1, column=col, name=f"x[{self.var_num}]")

    def initialize_model(self):
        if self.init_columns is None:
            x_index = tuple(range(1, self.data.n + 1))
            self.x = self.model.addVars(x_index, vtype=GRB.CONTINUOUS, name="x")
            self.constraints = self.model.addConstrs(
                (self.x[i] == 1 for i in x_index), name="exact")

            self.setObjective(self.x.sum(), GRB.MINIMIZE)
            if self.add_cuts:
                self.sr = self.model.addConstrs((0 <= 1 for _ in self.s), name="sr")
                for c in self.sr.values():
                    c.setAttr("RHS", 1)
        else:
            x_index = tuple(range(1, len(self.init_columns) + 1))
            self.x = self.model.addVars(x_index, vtype=GRB.CONTINUOUS, name="x")
            self.constraints = self.model.addConstrs((
                quicksum(self.x[i] * self.init_columns[i - 1][j - 1] for i in x_index) == 1
                for j in range(1, self.data.n + 1)
            ), name="exact")
            self.setObjective(self.x.sum(), GRB.MINIMIZE)

            if self.add_cuts:
                self.sr = self.model.addConstrs((quicksum(
                    self.x[i] * int(self.init_columns[i - 1][p - 1] +
                                    self.init_columns[i - 1][q - 1] +
                                    self.init_columns[i - 1][r - 1] >= 2)
                    for i in x_index) <= 1 for p, q, r in self.s), name="sr")
        self.var_num = len(x_index)
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
        constr_name = self.constraints[constraint_id].constrName
        self.model.remove(self.model.getConstrByName(constr_name))
        self.constraints.pop(constraint_id)

    def removeVarById(self, var_id):
        var_name = f"x[{var_id}]"
        if self.model.getVarByName(var_name) is not None:
            self.model.remove(self.model.getVarByName(var_name))


if __name__ == '__main__':
    pass
