#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Time : 2019/12/29 16:08
# Author: Zheng Shaoxiang
# @Email : zhengsx95@163.com
# Description:  定义一个基础的一维bin packing的gurobi model
# 二维bin packing model 一维单机批调度single batch model 二维单机批调度model
# 以及二维单机批调度的对偶松弛模型 dual feasible single batch model
from gurobipy import *
from collections import namedtuple
from collections import defaultdict

from abc import ABC, abstractmethod
from enum import Enum

from copy import copy
import re
import math

Item = namedtuple("Item", "id width height processing_time")
EPS = 1e-6


class ModelStatus(Enum):
    LOADED = 1
    OPTIMAL = 2
    INFEASIBLE = 3
    INF_OR_UNBD = 4
    UNBOUNDED = 5
    CUTOFF = 6
    ITERATION_LIMIT = 7
    NODE_LIMIT = 8
    TIME_LIMIT = 9
    SOLUTION_LIMIT = 10
    INTERRUPTED = 11
    NUMERIC = 12
    SUBOPTIMAL = 13
    INPROGRESS = 14
    USER_OBJ_LIMIT = 15


class BasicModel(ABC):
    @abstractmethod  # 子类中必须重写的方法
    def __init__(self, items, W, H, *args):
        self.W, self.H = W, H  # width and height of the single machine
        self.items = items  # items = dict{item_id: Item(id=1, width=2, height=2, processing_time=5),...}
        self.output_flag = False
        self.time_limit = 3600  # 默认设置3600s
        self.print_variable_flag = False  # determine that whether print the value of variables or not
        self.init_sol_flag = True  # use the initial solutions or not
        self.J = tuple(j for j in items)  # job indices
        self.B = None  # batch indices
        self.u, self.v = None, None  # variables
        self.lower_bound = None  # lower bound of problem
        self.u_index = None  # variable indices

        self.w, self.h = None, None  # width and height of items
        self.m = None  # gurobi model
        self.runtime = 0
        self.obj_val = None  # objective value
        self.status = None  # the optimized status of the model

    def set_params(self):
        self.m.Params.Threads = 1
        self.m.Params.OutputFlag = self.output_flag
        self.m.Params.TimeLimit = self.time_limit

    # 获取问题下界
    @ abstractmethod
    def set_lower_bound(self, lower):
        self.lower_bound = lower

    def get_lower_bound(self):
        pass

    @ abstractmethod  # 获得初始解
    def get_init_sol(self):
        pass

    @ abstractmethod  # 打印变量
    def print_variables(self):
        pass

    @ abstractmethod  # 添加初始解进入模型
    def add_init_sol(self, m):
        pass

    def do_something(self):
        pass

    @abstractmethod  # 建立问题模型
    def build_model(self):
        pass

    # 求解模型
    def solve(self):
        lower_bound = self.lower_bound

        def callback(model, where):  # simple callback
            if where == GRB.Callback.MIPSOL:  # 找到新的目标值
                # 不同的问题可能需要调整，因为目前的问题中，目标函数值最多有一位小数，因此定义目标函数值和下界
                # 只差不超过
                # print(f"找到新的MIP目标函数值{model.cbGet(GRB.Callback.MIPSOL_OBJBST)}")
                if abs(model.cbGet(GRB.Callback.MIPSOL_OBJBST) - lower_bound) <= 1e-3:
                    # print("找到最优解")
                    model.terminate()

        if self.m is None:

            self.m = self.build_model()  # build the model

            self.m.update()

        if self.init_sol_flag:  # if the flag is True, generate initial solutions and use them.
            self.m = self.add_init_sol(self.m)
            self.m.update()

        self.set_params()

        if self.lower_bound is None:  # when the lower bound is generated, use it for callback
            self.m.optimize()
        else:
            self.m.optimize(callback)

        self.status = self.m.Status

        self.runtime = self.m.Runtime
        self.obj_val = self.m.objVal

        if self.print_variable_flag:

            # print(f"status={m.Status}")
            # print(f"the status is optimal? {self.status == GRB.OPTIMAL or self.status == GRB.INTERRUPTED}")
            # print(f"optimal value = {m.objVal}\truntime={m.Runtime}\nMIPGap={m.MIPGap == float('inf')}")
            self.print_variables()

        self.do_something()
        return self.m  # 返回求解后的模型


class Orthogonal(BasicModel):
    """
    determine that whether a set of rectangular items can be packed into a bin or not
    """
    def __init__(self, items, W, H, *args):
        super().__init__(items, W, H, *args)
        self.W = W
        self.H = H
        self.items = items
        self.packed_items = None
        self.a = None
        self.o = None
        self.x = None
        self.y = None
        self.l = None
        self.b = None

    def set_lower_bound(self, lower):
        self.lower_bound = min(lower, -len(self.items))

    def get_init_sol(self):
        pass

    @ staticmethod
    def do_something(self):
        self.packed_items = [j for j in self.J if abs(self.m.getVarByName(f"a[{j}]").x - 1) <= EPS]

    def build_model(self):
        m = Model("Orthogonal")
        self.w = {key: item.width for key, item in self.items.items()}
        self.h = {key: item.height for key, item in self.items.items()}

        # 索引定义
        bid_index = tuplelist([(i, j) for i in self.J for j in self.J if i != j])

        # 变量定义
        self.o = m.addVars(self.J, vtype=GRB.BINARY, name="o")  # o[j] = 1 if item j is oriented, 0 otherwise
        self.a = m.addVars(self.J, vtype=GRB.BINARY, name="a")  # a[j] = 1 if item j is assigned to the bin, 0 otherwise
        # x[j] indicates the bottom-left x-coordinate of item j
        self.x = m.addVars(self.J, vtype=GRB.CONTINUOUS, name="x")
        # y[j] indicates the bottom-left y-coordinate of item j
        self.y = m.addVars(self.J, vtype=GRB.CONTINUOUS, name="y")
        # l[i, j] = 1 if item i is to the left of item j in the same bin, 0 otherwise
        self.l = m.addVars(bid_index, vtype=GRB.BINARY, name="l")
        # b[i, j] = 1 if item i is to the bottom of item j in the same bin, 0 otherwise
        self.b = m.addVars(bid_index, vtype=GRB.BINARY, name="b")

        m.addConstrs((self.x[j] + self.w[j] * self.o[j] + (1 - self.o[j]) * self.h[j] <= self.W for j in self.J),
                     name="x_not_exceed")
        m.addConstrs((self.y[j] + self.h[j] * self.o[j] + (1 - self.o[j]) * self.w[j] <= self.H for j in self.J),
                     name="y_not_exceed")
        m.addConstrs((self.x[i] + self.w[i] * self.o[i] + (1 - self.o[i]) * self.h[i] <=
                      self.x[j] + self.W * (1 - self.l[i, j]) for i, j in bid_index), name="x_not_overlap")
        m.addConstrs((self.y[i] + self.h[i] * self.o[i] + (1 - self.o[i]) * self.w[i] <=
                      self.y[j] + self.H * (1 - self.b[i, j]) for i, j in bid_index), name="y_not_overlap")
        m.addConstrs((self.l[i, j] + self.l[j, i] + self.b[i, j] + self.b[j, i] >= self.a[i] + self.a[j] - 1
                      for i, j in bid_index if i < j), name="relative_position")

        m.setObjective(-self.a.sum(), GRB.MINIMIZE)

        self.m = m
        return m

    def add_init_sol(self, m):
        return m

    def print_variables(self):
        print(f"the packed items are:")
        print([j for j in self.J if abs(self.m.getVarByName(f"a[{j}]").x - 1) <= EPS])
        print(f"and objective value = {self.m.objVal}")
        print(f"runtime = {self.m.Runtime}")
        pass


class BinPacking(BasicModel):
    """
    one-dimensional bin packing
    """

    def __init__(self, items, W, H=1, *args):
        super().__init__(items, W, H)

        self.num_bins = 0
        self.W = W * H

    def get_num_of_bins(self):

        return len(self.items)

    def get_init_sol(self):
        _items = copy(self.items)  # 拷贝所有结果
        _results = defaultdict(list)
        bin_id = 1
        while _items:
            scheduled_item_id = set()
            c_width = 0
            for _item in sorted(_items.values(), key=lambda x: x.width * (1 if not hasattr(x, "height") else x.height),
                                reverse=True):
                if c_width + _item.width * (1 if not hasattr(_item, "height") else _item.height) <= self.W:
                    _results[bin_id].append(_item)
                    scheduled_item_id.add(_item.id)
                    c_width += _item.width * (1 if not hasattr(_item, "height") else _item.height)
            bin_id += 1
            _items = {item.id: item for item in _items.values() if item.id not in scheduled_item_id}
        return _results  # dict{bin_id:[Item,...]}

    def set_lower_bound(self, lower):
        self.lower_bound = math.ceil(sum(item.width * item.height for item in self.items.values()) / self.W)
        self.lower_bound = max(self.lower_bound, lower)

    def build_model(self):

        self.num_bins = self.get_num_of_bins()

        self.w = {key: item.width * (item.height if hasattr(item, "height") else 1) for key, item in self.items.items()}

        m = Model("BinPacking")

        # 索引定义
        self.B = tuple(k for k in range(1, self.num_bins + 1))
        self.u_index = tuplelist([(j, k) for j in self.J for k in self.B])

        # 变量定义
        # u[j, k] = 1 if item j is assigned to bin k, 0 otherwise
        self.u = m.addVars(self.u_index, vtype=GRB.BINARY, name="u")
        self.v = m.addVars(self.B, vtype=GRB.BINARY, name="v")  # v[k] = 1 if bin k is used, 0 otherwise

        # 约束定义
        m.addConstrs((self.u.sum(j, '*') == 1 for j in self.J), name="exact_one")
        m.addConstrs((quicksum(self.u[j, k] * self.w[j] for j in self.J) <= self.W * self.v[k] for k in self.B),
                     name="length_not_exceed")

        m.setObjective(self.v.sum(), GRB.MINIMIZE)

        return m

    def print_variables(self):
        jobs_of_bin = defaultdict(list)
        for ind, u in self.u.items():
            if abs(u.x - 1) <= EPS:
                job_s, bin_s = re.findall(r"\d+", u.varName)
                job_id, bin_id = int(job_s), int(bin_s)
                jobs_of_bin[bin_id].append(job_id)
        for bin_id, jobs in jobs_of_bin.items():
            print(f"the bin {bin_id} is used and the items packed in are\n"
                  f"{jobs_of_bin[bin_id]}")
        print()

    def add_init_sol(self, m):
        init_results = self.get_init_sol()
        for bin_id, packed_items in init_results.items():
            m.getVarByName(f"v[{bin_id}]").start = 1.0
            for _item in packed_items:
                m.getVarByName(f"u[{_item.id},{bin_id}]").start = 1.0
        return m


class DualFeasibleFunction:
    def __init__(self):
        pass

    @ staticmethod
    def u1(x):
        assert 0 <= x <= 1, "超出边界"
        if abs(x-0.5) <= EPS:
            return 0.5
        elif x < 0.5:
            return 0
        elif x > 0.5:
            return 1

    @staticmethod
    def U(rho, x):
        assert 0 <= x <= 1, "超出边界"
        assert 0 < rho <= 0.5, "超出边界"
        if x > 1 - rho:
            return 1
        elif x < rho:
            return 0
        else:
            return x

    @staticmethod
    def phi(rho, x):
        assert 0 <= x <= 1, "超出边界"
        assert 0 < rho <= 0.5, "超出边界"
        if x > 1 - rho:
            return 1 - math.floor((1 - x) / rho) / math.floor(1 / rho)
        elif x < rho:
            return 0
        else:
            return 1 / math.floor(1 / rho)

    def omega(self, index, p, w, h, q=None):
        assert index in (1, 2, 3, 4, 5, 6, 7), "超出边界"
        assert 0 < p <= 0.5, "p应在(0, 0.5]"
        assert 0 < w <= 1, "w应在(0, 1]"
        assert 0 < h <= 1, "h应在(0, 1]"

        if index == 1:
            return self.u1(w) * self.U(p, h)
        elif index == 2:
            return self.U(p, w) * self.u1(h)
        elif index == 3:
            return self.u1(w) * self.phi(p, h)
        elif index == 4:
            return self.phi(p, w) * self.u1(h)
        elif index == 5:
            return w * self.U(p, h)
        elif index == 6:
            return self.U(p, w) * h
        elif index == 7:
            assert q is not None, "q尚未赋值"
            assert 0 < q <= 0.5, "q应在(0, 0.5]"
            return self.phi(p, w) * self.phi(q, h)


class BinPacking2(BinPacking, Orthogonal):
    """
    two-dimensional bin packing
    """
    def __init__(self, items, W, H, *args):
        super(BinPacking2, self).__init__(items, W, H, *args)
        self.W = W
        self.H = H

    def get_init_sol(self):
        pass

    def build_model(self):
        bm = super(BinPacking2, self).build_model()  # 调用父类方法一维bin packing模型
        om = super(BinPacking, self).build_model()  # 调用父类方法二维orthogonal packing模型

        bm.update()
        om.update()

        self.num_bins = self.get_num_of_bins()

        # 索引定义
        bid_index = tuplelist([(i, j) for i in self.J for j in self.J if i != j])

        # 变量定义
        self.u = om.addVars(self.u_index, vtype=GRB.BINARY, name="u")
        self.v = om.addVars(self.B, vtype=GRB.BINARY, name="v")
        # 约束定义
        om.addConstrs((self.u.sum(j, '*') == 1 for j in self.J), name="exact_one")
        om.addConstrs((self.u[j, k] <= self.v[k] for j, k in self.u_index), name="bin_formed")

        for i, j in bid_index:
            if i < j:
                om.remove(om.getConstrByName(f"relative_position[{i},{j}]"))

        om.addConstrs((self.l[i, j] + self.l[j, i] + self.b[i, j] + self.b[j, i] >= self.u[i, k] + self.u[j, k] - 1
                      for i, j in bid_index if i < j for k in self.B), name="relative_position")

        om.setObjective(self.v.sum(), GRB.MINIMIZE)
        om.modelName = "BinPacking2"
        return om

    def set_lower_bound(self, lower):
        self.lower_bound = math.ceil(sum(item.width * item.height for item in self.items.values()) / self.W * self.H)
        self.lower_bound = max(self.lower_bound, lower)

    def add_init_sol(self, m):
        # init_sol = {bin_id: [Corner(id=12, width=11, height=10, x=0, y=0),...],...}
        init_sol = self.get_init_sol()
        if init_sol is None:
            return m
        for bin_id, packed_items in init_sol.items():
            self.v[bin_id].start = 1.0
            for _item in packed_items:
                self.u[_item.id, bin_id].start = 1.0
                self.x[_item.id].start = _item.x
                self.y[_item.id].start = _item.y
                self.o[_item.id].start = 1.0 if (self.w[_item.id], self.h[_item.id]) == \
                                                (_item.width, _item.height) else 0
        return m

    def print_variables(self):
        print(f"objective value = {self.m.objVal}")
        print(f"runtime = {self.m.Runtime}")
        jobs_of_bin = defaultdict(list)
        for ind, u in self.u.items():
            if abs(u.x - 1) <= EPS:
                job_s, bin_s = re.findall(r"\d+", u.varName)
                job_id, bin_id = int(job_s), int(bin_s)
                jobs_of_bin[bin_id].append(job_id)
        for bin_id, jobs in jobs_of_bin.items():
            print(f"the bin {bin_id} is used and the items packed in are\n"
                  f"{jobs_of_bin[bin_id]}")
        print()


class SingleBatch(BinPacking):
    """
    one-dimensional single batch scheduling model
    :arg
    """
    def __init__(self, items, W, H=1, *args):
        super().__init__(items, W, H, *args)
        self.p = None  # parameters indicate the processing time of each item
        self.q = None  # variables indicate the processing time of each bin

    def build_model(self):
        m = super(SingleBatch, self).build_model()  # one-dimensional bin packing model

        m.update()

        self.p = {key: item.processing_time for key, item in self.items.items()}
        self.q = m.addVars(self.B, vtype=GRB.CONTINUOUS, name="q")
        m.addConstrs((self.q[k] >= self.p[j] * self.u[j, k] for j in self.J for k in self.B),
                     name="bin_processing_time")
        m.setObjective(self.q.sum(), GRB.MINIMIZE)
        m.modelName = "SingleBatch"
        return m

    def set_lower_bound(self, lower):
        self.lower_bound = max(math.ceil(sum(item.width * item.height * item.processing_time
                                             for item in self.items.values()) / (self.W * self.H)), lower)

    def add_init_sol(self, m):
        return m

    def get_init_sol(self):
        pass

    # def print_variables(self):
    #     print(f"todo")


class SingleBatch2(SingleBatch, BinPacking2):
    """
    two-dimensional single batch scheduling
    :arg
    """
    def __init__(self, items, W, H, *args):
        super(SingleBatch2, self).__init__(items, W, H, *args)

    def build_model(self):
        bm = super(SingleBatch, self).build_model()  # two-dimensional bin packing model

        bm.update()

        for j, k in self.u_index:
            bm.remove(bm.getConstrByName(f"bin_formed[{j},{k}]"))

        for j in self.J:
            bm.remove(bm.getVarByName(f"a[{j}]"))

        self.p = {key: item.processing_time for key, item in self.items.items()}
        q = bm.addVars(self.B, vtype=GRB.CONTINUOUS, name="q")
        bm.addConstrs((q[k] >= self.p[j] * self.u[j, k] for j in self.J for k in self.B), name="bin_processing_time")
        bm.setObjective(q.sum())
        bm.modelName = "SingleBatch2"

        return bm

    def set_lower_bound(self, lower):
        self.lower_bound = lower

    def add_init_sol(self, m):
        return m

    def get_init_sol(self):
        pass

    def print_variables(self):
        print(f"todo")


class DualFeasibleSingleBatch(SingleBatch2, DualFeasibleFunction):
    """
    two-dimensional dual feasible single batch problem
    :arg
    """

    def __init__(self, items, W, H, *args):
        super().__init__(items, W, H, *args)
        self.f_o = None
        self.f_r = None
        self.num_feasibility_constraints = 0

    def get_tau(self):
        """
        获得新的实例tau
        :return
        """
        n = len(self.items)
        N = [i for i in self.items]
        _N = N + [i + n for i in self.items]  # index of oriented and non-oriented version

        P, Q = [0.15, 0.3, 0.45], [0.15, 0.3, 0.45]
        m = len(P) * 6 + len(P) * len(Q)  # 约束数量
        func = DualFeasibleFunction()
        # func = super(SingleBatch2, self)

        # tau[c, i] = s  表示在第c个约束下第i个item的面积
        tau_r = tupledict([((c, i), 0) for c in range(1, m + 1) for i in self.items])
        tau_o = tupledict([((c, i), 0) for c in range(1, m + 1) for i in self.items])

        c = 1  # 约束编号

        for p in P:
            for index in range(1, 7):
                for job_id, item in self.items.items():
                    w, h = item.width / self.W, item.height / self.H
                    r = func.omega(index=index, p=p, w=w, h=h)
                    tau_o[c, job_id] = r

                    w, h = item.height / self.W, item.width / self.H
                    r = func.omega(index=index, p=p, w=w, h=h)
                    tau_r[c, job_id] = r
                if sum(max(tau_o[c, job_id], tau_r[c, job_id]) for job_id in self.items) <= 1:
                    # 若某个约束面积之和小于1，则该约束不起作用，删除
                    for job_id in self.items:
                        del tau_o[c, job_id]
                        del tau_r[c, job_id]
                else:
                    c += 1

        index = 7
        for p in P:
            for q in Q:
                for job_id, item in self.items.items():
                    w, h = item.width / self.W, item.height / self.H
                    r = func.omega(index=index, p=p, q=q, w=w, h=h)
                    tau_o[c, job_id] = r

                    w, h = item.height / self.W, item.width / self.H
                    r = func.omega(index=index, p=p, q=q, w=w, h=h)
                    tau_r[c, job_id] = r
                if sum(max(tau_o[c, job_id], tau_r[c, job_id]) for job_id in self.items) <= 1:
                    # 若某个约束面积之和小于1，则该约束不起作用，删除
                    for job_id in self.items:
                        del tau_o[c, job_id]
                        del tau_r[c, job_id]
                else:
                    c += 1

        _tau_o = {}
        _tau_r = {}
        nc = defaultdict(lambda: 0)
        for _c1 in range(1, c):
            for _c2 in range(1, c):
                if _c1 == _c2:
                    continue
                for job_id in self.items:
                    if tau_o[_c1, job_id] <= tau_o[_c2, job_id] and tau_r[_c1, job_id] <= tau_r[_c2, job_id]:
                        pass
                    else:
                        break
                else:  # _c1 被 _c2支配
                    nc[_c1] += 1  # 约束c被支配的数目
        num = 0  # 约束的数量
        for _c in range(1, c):
            if nc[_c] == 0:  # 约束c不被任一约束支配
                num += 1
                for job_id in self.items:
                    _tau_o[num, job_id] = tau_o[_c, job_id]
                    _tau_r[num, job_id] = tau_r[_c, job_id]

        return tau_o, tau_r, num

    def delete_two_dimensional_constraints(self, m):
        for i in self.J:
            m.remove(m.getConstrByName(f"x_not_exceed[{i}]"))
            m.remove(m.getConstrByName(f"y_not_exceed[{i}]"))
            for j in self.J:
                if i != j:
                    m.remove(m.getVarByName(f"l[{i},{j}]"))
                    m.remove(m.getVarByName(f"b[{i},{j}]"))
                    m.remove(m.getConstrByName(f"x_not_overlap[{i},{j}]"))
                    m.remove(m.getConstrByName(f"y_not_overlap[{i},{j}]"))
                    if i < j:
                        for k in self.B:
                            m.remove(m.getConstrByName(f"relative_position[{i},{j},{k}]"))
        return m

    def delete_partial_constraints(self, m):
        for j in self.J:
            m.remove(m.getConstrByName(f"exact_one[{j}]"))
            for k in self.B:
                m.remove(m.getConstrByName(f"bin_processing_time[{j},{k}]"))
        return m

    def build_model(self):
        m = super(DualFeasibleSingleBatch, self).build_model()  # two-dimensional single batch problem
        m.update()
        # 删除two-dimensional single batch problem中的二维约束
        m = self.delete_two_dimensional_constraints(m)
        m.update()

        # 删除约束
        m = self.delete_partial_constraints(m)
        m.update()

        # 增加一维dual feasible constraints
        self.f_o = m.addVars(self.u_index, vtype=GRB.BINARY, name="f_o")
        self.f_r = m.addVars(self.u_index, vtype=GRB.BINARY, name="f_r")
        tau_o, tau_r, num_constraints = self.get_tau()
        self.num_feasibility_constraints = num_constraints
        m.addConstrs((self.f_o.sum(j, '*') + self.f_r.sum(j, '*') == 1 for j in self.J), name="oriented_exact_one")
        m.addConstrs((quicksum(tau_o[c, j] * self.f_o[j, k] + tau_r[c, j] * self.f_r[j, k] for j in self.J) <= 1
                      for k in self.B for c in range(1, num_constraints + 1)), name="dual_bin")
        m.addConstrs((m.getVarByName(f"q[{k}]") >= (self.f_o[j, k] + self.f_r[j, k]) * self.p[j] for j in self.J for k
                      in self.B), "bin_processing_time")
        m.modelName = "DualFeasibleSingleBatch"
        return m

    def add_init_sol(self, m):
        return m

    def get_init_sol(self):
        pass

    def print_variables(self):
        pass


if __name__ == '__main__':
    import random
    random.seed(1)
    width, height = 20, 20
    items = {i: Item(id=i, width=random.randint(1, 11), height=random.randint(1, 11),
                     processing_time=random.randint(1, 11)) for i in range(1, 21)}
    bp = SingleBatch(width, height, items)
    bp.time_limit = 1

    # lb = DualFeasibleSingleBatch(width, height, items).solve()
    # bp.set_lower_bound(lb)
    #
    # bp.print_variable_flag = True

    bp.solve()
