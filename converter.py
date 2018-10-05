import sys
import networkx as nx

#Converter from  .gml format to dictionary of dictionaries format
def convert_from_gml(name, val):
    graph = {}
    G = nx.read_gml(name)
    print G.edges
    nds = []
    for k in G.nodes:
        nds.append(k)
    for i in G.node:
        graph.setdefault(nds.index(i),{})
    for k in G.edges:
        graph[nds.index(k[0])][nds.index(k[1])] = val
        graph[nds.index(k[1])][nds.index(k[0])] = val
    print graph
    for k in graph.keys():
        print "#", k, graph[k]
    return graph

#Get the number of vertices in graph
def get_node_number(name):
    G = nx.read_gml(name)
    return len(G.node)

if __name__ == "__main__":
    i = 0
    name = []
    for param in sys.argv: 
        if i == 1:
            name = param
            break
        i+=1
    #name = str(name.split(".")[0])
    #name+=".txt"
    #print name
    #f = open(".txt","w")"""
    graph = convert_from_gml(name,20)
