#Source: Bang Ye Wu, Kun-Mao Chao "Steiner Minimal Tress"

import sys

class Graph:
    def __init__(self, graph = None):
        if graph is None:
            self._graph = {}
            self._reset_copy_of_graph = {}
        else:
            self._graph = graph
            self._reset_copy_of_graph = self.copy_of_graph(self._graph)

    def get_graph(self):
        return self._graph

    #debug print of graph
    def print_graph(self):
        #print "Original graph:"
        for (keys, value) in self._graph.items():
            print "\t", keys, value
        #print "Reset graph:"
        #for (keys, value) in self._reset_copy_of_graph.items():
        #    print keys, value

    def to_string(self):
        for (keys, value) in self._graph.items():
            str += str(keys) + " " + str(value)
        return str

    def get_adjacent_vertices(self, vert):
        return self._graph[vert]

    def get_weight_of_edge(self,vert_1,vert_2):
        return self._graph[vert_1][vert_2]

    def update_throughputs(self, path, sla):
        for i in xrange(len(path)-1):
            self._graph[path[i]][path[i+1]]-=sla
            self._graph[path[i+1]][path[i]]-=sla
    
    def do_reset_copy_of_graph(self):
        self._reset_copy_of_graph = self.copy_of_graph(self._graph)
            
    def reset_throughputs(self):
        self._graph = self.copy_of_graph(self._reset_copy_of_graph)

    def copy_of_graph(self,graph):
        gr = {}
        for k in graph.keys():
            gr.setdefault(k,{})
            for t in graph[k].keys():
                gr[k][t] = graph[k][t]
        return gr

    #get graph from *.txt file
    def get_physical_from_file(self, filename):
        graph_file = open(filename)
        dws = []
        count = 0    
        for line in graph_file:
            self._graph.setdefault(int(count),{})
            dws = []
            dwl = line.split(" ")
            #print line
            for t in dwl:
                i_1 = t.index("(")
                i_2 = t.index(")")
                b = t[i_1+1:i_2]
                b = b.split(",")
                self._graph.setdefault(int(b[0]),{})
                self._graph[count][int(b[0])] = int(b[1])
                self._graph[int(b[0])][count] = int(b[1])
            count+=1
        self._reset_copy_of_graph = self.copy_of_graph(self._graph)


    def get_virtual_from_file(self, filename):
        listOfTerminalVertices = []
        graph_file = open(filename)
        dws = []
        count = 0    
        for line in graph_file:
            flag = False
            dws = []
            dwl = line.split(" ")
            self._graph.setdefault(int(count),{})
            for t in dwl:
                sqb_1 = -1
                sqb_2 = -2
                if "{" in t:
                    sqb_1 = t.index("{")
                    sqb_2 = t.index("}")
                    tv = t[sqb_1+1:sqb_2]
                    tv_2= tv.split(",")
                    terminalVertices = []
                    flag = False    
                    for t in tv_2:
                        terminalVertices.append(int(t))
                    listOfTerminalVertices.append(terminalVertices)
                else:
                    i_1 = t.index("(")
                    i_2 = t.index(")")
                    b = t[i_1+1:i_2]
                    b = b.split(",")
                    flag = True 
                    self._graph.setdefault(int(b[0]),{})
                    self._graph[count][int(b[0])] = int(b[1])
                    self._graph[int(b[0])][count] = int(b[1])
            if flag == True:
                count+=1
        return listOfTerminalVertices

    #Dijkstra algorithm implementation for vertex_1 (find shortest pathes from vertex_1 to other vertices)
    def Dijkstra_algorithm(self, vertex_1, mode):
        dist = dict.fromkeys(self._graph,float('inf'))
        path = {}
        init_flag = True
        #dist to initial vertex is NULL
        dist[vertex_1]=0
        hops = dict.fromkeys(self._graph,0)
        #Set of original graph vertices
        vertex_array = set(self._graph)
        #cycle through all the vertices
        vertex_3 = vertex_1
        while vertex_array:
            for vertex,d in self._graph[vertex_3].items():
                if mode == "hops":
                    if dist[vertex] > dist[vertex_3] + 1:
                        path[vertex] = vertex_3
                        dist[vertex] = dist[vertex_3] + 1
                        hops[vertex] = hops[vertex_3] + 1
                elif mode == "throughput":
                    if(self._graph[vertex_3][vertex]!=0):
                        if dist[vertex] > dist[vertex_3] + 1/float(self._graph[vertex_3][vertex]):
                            path[vertex] = vertex_3
                            dist[vertex] = dist[vertex_3] + 1/float(self._graph[vertex_3][vertex])
                            hops[vertex] = hops[vertex_3] + 1 
                    else:
                        if dist[vertex] > dist[vertex_3] + 1/0.0000000000000000000000001:
                            path[vertex] = vertex_3
                            dist[vertex] = dist[vertex_3] + 1/0.000000000000000000001
                            hops[vertex] = hops[vertex_3] + 1 
            vertex_3 = min( vertex_array, key = dist.get )
            vertex_array.remove( vertex_3 )
        return (path, dist, hops)
                
    
    #get path as vertex sequence adter Dijkstra search
    def get_path(self, last_vertex, hops, path, dist):
        result_path = []
        result_path.append(last_vertex)
        tmp = hops[last_vertex]
        result_dist = 0
        current = last_vertex
        result_dist+=dist[last_vertex]
        for i in xrange(int(tmp)):                
            vertex = path[current]
            result_path.append(vertex)
            current = path[current]
        result_path.reverse()
        return (result_path,result_dist)
    
    #construct the metric closure for original graph on terminal vertices
    def _construct_metric_closure(self, terminalVertices):
        
        metricClosureOfGraph = {}
        #creation of metric closure as full graph on terminal vertices 
        #(weight of every edge equals total weight of shortest path between appropriate vertices"  
        for i in frozenset(terminalVertices):
            (path, dist, hops) = self.Dijkstra_algorithm(i,"hops")
            metricClosureOfGraph.setdefault(i,{})
            for j in frozenset(terminalVertices):
                metricClosureOfGraph.setdefault(j,{})
                if (i!=j):
                    result_path,result_dist = self.get_path(j,hops, path, dist)
                    
                    #saving the homeomorphic path for edge in MST and it's total weight
                    metricClosureOfGraph[int(i)][int(j)] = (result_path, dist[j])
                    metricClosureOfGraph[int(j)][int(i)] = (result_path, dist[j])
        print "Metric closure for original graph:"            
        for (keys, value) in metricClosureOfGraph.items():
            print "\t", keys, value
        return metricClosureOfGraph
    
    #three main steps in 2 appoximately algorithm for Steiner tree
    def build_Steiner_tree_2_approxim(self, terminalVertices):
        mc = self._construct_metric_closure(terminalVertices)
        #MST = self._build_minimal_spanning_tree(mc,terminalVertices)
        MST = self._build_minimal_spanning_tree_2(mc,terminalVertices)
        Steiner_vertices = self._construct_Steiner_tree(MST)
        return Steiner_vertices
        
    #function for build MST of metric closure of original graph    
    def _build_minimal_spanning_tree(self, mc, terminalVertices):
        #searching of minimal node (with minimal edges weight for adjacent vertices in MST_set)
        def search_minimal_node(mc, MST_set):
            flag = False
            for i in set(mc):
                for j in set(mc[i]):
                    if flag == False:
                        (tmp, max) = mc[i][j]
                        flag = True
                    if (mc[i][j][1]>max):
                        max = mc[i][j][1]
            min = max
            for i in MST_set:
                for j in mc[i]:
                    if mc[i][j][1] <= min and j not in MST_set:
                        min = mc[i][j][1]
                        idx_1 = j
                        idx_2 = i
                        path = mc[i][j][0]
            return (min,idx_1,idx_2,path)

        #use Prim's algorithm for MST building
        toVisit = []
        firstNode = mc.keys()[0]
        for i in set(mc):
            if i!=firstNode:
                toVisit.append(i)
        MST_set = set()
        result_MST = {}
        weights = []
        MST_set.add(firstNode)
        for node in toVisit:
            w,j,i,p = search_minimal_node(mc,frozenset(MST_set))
            result_MST.setdefault(i,{})
            result_MST.setdefault(j,{})
            result_MST[i][j] = (p,w)
            result_MST[j][i] = (p,w)
            MST_set.add(j)
            weights.append(w)
        print "Prim's MST for metric closure:"
        for k in result_MST:
            print "\t", k, result_MST[k]
        return result_MST


#============= Kruskal's ====================

    #function for build MST of metric closure of original graph    
    def _build_minimal_spanning_tree_2(self, mc, terminalVertices):
        result_MST = {};
        forest = []
        for i in terminalVertices:
            forest.append([i])
        while (len(forest) != 1):
            flag = True
            for i in set(mc):
                for j in set(mc[i]):
                    if flag:
                        path = mc[i][j][0]
                        min = mc[i][j][1]
                        x = i
                        y = j
                        flag = False
                    else:
                        if (mc[i][j][1] < min):
                            path = mc[i][j][0]
                            min = mc[i][j][1]
                            x = i
                            y = j
            
            for i in forest:
                if (x in i) and not (y in i):
                    for j in forest:
                        if (y in j):
                            for k in j:
                                i.append(k)
                            forest.remove(j)
                            break
                    if (result_MST.get(x) == None):
                        result_MST[x] = {y : (path, min)}
                    else:
                        result_MST[x].update({y : (path, min)})
                    if (result_MST.get(y) == None):
                        result_MST[y] = {x : (path, min)}
                    else:
                        result_MST[y].update({x :(path, min)})
            # removing used edges from metric closure
            mc[x].pop(y, None)
            if (mc[x] == {}):
                mc.pop(x, None)
            mc[y].pop(x, None)
            if (mc[y] == {}):
                mc.pop(y, None)

        print "Kruskal's MST for metric closure:"
        for k in result_MST:
            print "\t", k, result_MST[k]
        return result_MST

#============================================

    
    def _construct_Steiner_tree(self,MST):
        
        vertices = dict.fromkeys(MST,(0,0))
        coun = [0]
        #addition edges to Steiner tree (if 0 or 1 vertices of path contains 
        #in Steiner tree then every edge of path adds to Steiner tree 
        #else if 2 or more vertices contains in path then beginning of path and ending of one 
        #adds to Steiner tree
        def add_edges_to_Steiner_tree(rst,path):
            rst_sets = set(rst)
            first_pos = -1
            second_pos = -1
            for i in path:
                if i in rst_sets:
                    if first_pos ==-1:
                        first_pos = i
                    elif first_pos>-1:
                        second_pos = i
            if (first_pos) == -1 and (second_pos) == -1 or first_pos!=-1 and second_pos == -1:
                for i in path:
                    rst.setdefault(i,{})
                for j in xrange(len(path)):
                    if j == 0:
                        rst[path[j]][path[j+1]] = self._graph[path[j]][path[j+1]] 
                    elif j!= len(path)-1:
                        rst[path[j]][path[j+1]] = self._graph[path[j]][path[j+1]] 
                        rst[path[j]][path[j-1]] = self._graph[path[j]][path[j-1]] 
                    elif j == len(path)-1:
                        rst[path[j]][path[j-1]] = self._graph[path[j]][path[j-1]] 
            else:
                wasFirst = False
                wasSecond =False
                for i in path:
                    if wasFirst == False and wasSecond == False:
                        if (i!=first_pos):
                            rst.setdefault(i,{})
                        else: 
                            wasFirst = True
                    elif wasFirst == True and wasSecond == False:
                        if (i!=second_pos):
                            continue
                        elif i==second_pos:
                            wasSecond = True
                    elif wasFirst == True and wasSecond == True:
                        rst.setdefault(i,{})
                for j in xrange(len(path)):
                    if wasFirst == False and wasSecond == False:
                        if (j!=fisrt_pos):
                            if j == 0:
                                rst[path[j]][path[j+1]] = self._graph[path[j]][path[j+1]] 
                            elif j!= len(path)-1:
                                rst[path[j]][path[j+1]] = self._graph[path[j]][path[j+1]] 
                                rst[path[j]][path[j-1]] = self._graph[path[j]][path[j-1]] 
                            elif j == len(path)-1:
                                rst[path[j]][path[j-1]] = self._graph[path[j]][path[j-1]] 
                        else: wasFirst = True
                    elif wasFirst == True and wasSecond == False:
                        if (j!=second_pos):
                            continue
                        elif j== second_pos:
                            wasSecond = True
                    elif wasFirst == True and wasSecond == True:
                        if j == 0:
                            rst[path[j]][path[j+1]] = self._graph[path[j]][path[j+1]] 
                        elif j!= len(path)-1:
                            rst[path[j]][path[j+1]] = self._graph[path[j]][path[j+1]] 
                            rst[path[j]][path[j-1]] = self._graph[path[j]][path[j-1]] 
                        elif j == len(path)-1:
                            rst[path[j]][path[j-1]] = self._graph[path[j]][path[j-1]] 
                
        #implementation DFS for vertices ordering (0 and 1 used as visit label)    
        def _Depth_first_search(MST,v,vertices,coun):
            vertices[v] = (1,coun[0])
            for vert in MST[v].keys():
                if vertices[vert][0] == 0:
                    coun[0]+=1
                    _Depth_first_search(MST,vert,vertices,coun)
        for v in vertices.keys():
            if(vertices[v][0] == 0):
                _Depth_first_search(MST,v,vertices,coun)
        dfsVertices = [0]*len(vertices)
        for v in vertices:
            dfsVertices[vertices[v][1]]=v
        print "DFS order of vertices:"
        print "\t", dfsVertices
        result_Steiner_tree = {}
        for i in xrange(len(dfsVertices)):
            t = dfsVertices[i]
            for j in MST[t].keys():
                add_edges_to_Steiner_tree(result_Steiner_tree, MST[t][j][0])
        return result_Steiner_tree

def main(terminalVertices):
    graph = Graph()
    graph.get_from_file("tg.txt")
    graph.print_graph()
    graph.build_Steiner_tree_2_approxim(terminalVertices)
    

if __name__=="__main__":
    args = []
    count = 0 
    for arg in sys.argv:
        if count:
            args.append(int(arg))
        count+=1
    main(args)            
