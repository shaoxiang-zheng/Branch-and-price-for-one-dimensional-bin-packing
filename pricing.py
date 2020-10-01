#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Time : 2020/9/25 21:51
# Author: Zheng Shaoxiang
# @Email : zhengsx95@163.com
# Description:
from gurobimodel import *
from labelSetting import LabelSetting


class Pricing:
    def __init__(self, s, use_model=False):
        self.data = None
        self.s = s  # ((1, 2, 3), (4, 5, 6),...)
        self.n = None
        self.graph = None
        self.pricing = None  # Model()
        self.y, self.z = None, None
        self.use_model = use_model  # 使用模型求解
        self.lab = None  # LabelSetting类

    def build_model(self, data, graph):
        self.pricing = Model("pricing")

        item_id = [item.id for item in data.items]
        w = {item.id: item.width for item in data.items}
        self.y = self.pricing.addVars(item_id, vtype=GRB.BINARY, name="y")

        self.pricing.addConstr(quicksum(self.y[i] * w[i] for i in item_id),
                               GRB.LESS_EQUAL, data.capacity, name="capacity")

        if self.s is not None:
            # print(f"{self.s=}")
            self.z = self.pricing.addVars(self.s, vtype=GRB.BINARY, name="z")

            # self.s中item id可能已经被删除，因此添加条件i in item_id and j in item_id
            self.pricing.addConstrs((self.z[s] >= self.y[i] + self.y[j] - 1
                                     for s in self.s for i in s for j in s if i < j and i in item_id and j in item_id),
                                    name="sr_constr1")
            self.pricing.addConstrs((self.z[s] <= self.y[i] + self.y[j]
                                     for s in self.s for i in s for j in s if i < j and i in item_id and j in item_id),
                                    name="sr_constr2")
        if graph.has_node():  # 图不为空
            self.pricing.addConstrs((self.y[i] + self.y[j] <= 1
                                     for i, j in graph.get_all_edges()), name="incompatibility")
        self.pricing.ModelSense = GRB.MAXIMIZE
        self.set_parameters()

    def set_parameters(self):
        self.pricing.Params.OutputFlag = False

    def update_objective(self, exact, sr):
        self.pricing.update()
        for x, v in zip(self.y.values(), exact):
            x.obj = v
        if self.z is not None:
            for x, v in zip(self.z.values(), sr):
                x.obj = v

    def optimize(self):
        self.pricing.update()
        self.pricing.optimize()

    def get_reduced_cost(self):
        if self.use_model:
            return 1 - self.pricing.objVal
        else:
            if self.lab.labels:
                return self.lab.labels[0].c
            return 0

    def getConstrs(self):
        return self.pricing.getConstrs()

    def get_coe(self):
        sr_coe = []
        if self.use_model:
            # round() 为避免数值误差
            exact_coe = [round(v.x) for v in self.y.values()]
            if self.s is not None:
                sr_coe = [round(v.x) for v in self.z.values()]
        else:
            exact_coe = [1 if i in self.lab.labels[0].v else 0 for i in range(self.n)]
            sr_coe = self.lab.labels[0].z
        return exact_coe + sr_coe

    def solve(self, ex_dual, sr_dual, data, graph):
        """
        :param ex_dual: list[]
        :param sr_dual:   list[]
        :param data:
        :param graph:
        :return:
        """
        if self.use_model:
            self.build_model(data, graph)
            self.update_objective(ex_dual, sr_dual)
            self.optimize()
        else:
            self.n = data.n
            self.lab = LabelSetting(data, self.s, ex_dual, sr_dual, graph)
            self.lab.solve()


if __name__ == '__main__':
    pass
