#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Time : 2020/9/27 15:29
# Author: Zheng Shaoxiang
# @Email : zhengsx95@163.com
# Description:

class Graph:
    """
    定义一个无向图 undirected graph
    """
    def __init__(self):
        self.nodes = set()  # 存储节点编号
        self.edges = {}  # {node_number: set(1, 2)}

    def add_node(self, node):
        self.nodes.add(node)

    def add_nodes_from(self, nodes):
        for node in nodes:
            self.add_node(node)

    def add_edge(self, u, v):
        if u == v:  # 禁止添加连接同个节点的边
            return
        if u in self.edges:
            if v not in self.edges[u]:  # 防止添加重复边
                self.edges[u].add(v)
        else:
            self.edges[u] = {v}

        if v in self.edges:
            if u not in self.edges[v]:  # 防止添加重复边
                self.edges[v].add(u)
        else:
            self.edges[v] = {u}

    def add_edges_from(self, edges):
        for edge in edges:
            self.add_edge(*edge)

    def has_node(self):
        if self.nodes:
            return True
        return False

    def has_edge(self, u, v):
        if u not in self.edges or v not in self.edges:
            return False
        if v in self.edges[u]:
            return True
        return False

    def neighbors(self, node):
        if node not in self.edges:
            return []
        return self.edges[node]

    def remove_node(self, node):
        for nei in self.neighbors(node):
            self.edges[nei].remove(node)
        if node in self.edges:
            self.edges.pop(node)

    def get_all_edges(self):
        # 返回所有无重复的边
        for origin, to_edges in self.edges.items():
            for to_edge in to_edges:
                if origin < to_edge:
                    yield origin, to_edge


if __name__ == '__main__':
    pass
