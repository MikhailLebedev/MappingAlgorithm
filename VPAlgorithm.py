from __future__ import generators
import sys
import SMT

import itertools
from SMT import Graph 
from Tester import VPATester
from Logger import VPALogger
from itertools import permutations
import copy 

#Main algorithm is responsable for "virtual-to-physical" mapping
class VPAlgorithm:

    def __init__(self,logger, iter_param):
        self._physical_graph = Graph()
        self._virtual_graph = Graph()
        self._free_nodes = Graph()
        self._free_nodes_for_build = Graph()
        self.resultVerticesMapping = {}
        self.resultBigSwitchRouteMapping = {}
        self.resultVirtualLinksMapping = {}
        self.remainingVirVertices = set()
        self.remainingPhyVertices = set()
        self.listOfTerminalVertices = []
        self.listOfTerminalVertices_backup = []
        self.SteinerTrees = {}
        self.log = logger
        self.iter_param = iter_param

    #Setters
    def set_physical_graph(self, p_graph):
        self._physical_graph = p_graph

    def set_virtual_graph(self, v_graph):
        self._virtual_graph = v_graph

    #First step: 1.VBS mapping (build 2-approx Steiner Minimal Tree for every group of terminal vertices)
    #         2.Virtual links betwwen VBS mapping
    def  _first_step_construct_Big_switches_mapping(self, physical_network, virtual_network, listOfTerminalVertices):
        #Get graphs
        if physical_network == None and virtual_network == None and listOfTerminalVertices == None:    
            self._physical_graph.get_physical_from_file("physical.txt")
            self.listOfTerminalVertices = self._virtual_graph.get_virtual_from_file("virtual.txt")
        else:
            self._physical_graph = Graph(physical_network)
            self._virtual_graph = Graph(virtual_network)
            self.listOfTerminalVertices = listOfTerminalVertices
        print "Physical graph"
        self._physical_graph.print_graph()
        print "Virtual graph"
        self._virtual_graph.print_graph()
        print "TERMINAL VERTICES:"
        print "\t", self.listOfTerminalVertices
        verticesForBS = set()
        count = 0 
        listForCommonNodeFinding = []

        self.resultVerticesMapping = {}
        self.listOfTerminalVertices_backup = copy.deepcopy(self.listOfTerminalVertices)

        #=============== MODIFICATION BLOCK START ======================
        self._free_nodes = copy.deepcopy(self._physical_graph)
        # List of all terminal vertices which cant be used on current step of MST building
        tver  = []
        for x in xrange(len(self.listOfTerminalVertices)):
            for y in self.listOfTerminalVertices[x]:
                tver.append(y);
        #=============== MODIFICATION BLOCK END ======================

        #Build 2-approx SMT for every group of terminal vertices
        #Set mapping Virtual Border Switch to ({physical switch},{physial link})
        for i in xrange(len(self.listOfTerminalVertices)):
            terminalVertices = self.listOfTerminalVertices[i]
            #resultSteinerTree = self._physical_graph.build_Steiner_tree_2_approxim(terminalVertices)

        #=============== MODIFICATION BLOCK START ======================
            for x in terminalVertices:
                tver.remove(x)
            self._free_nodes_for_build = copy.deepcopy(self._free_nodes)

            for tv in tver:
                for x in set(self._free_nodes_for_build._graph):
                    for y in set(self._free_nodes_for_build._graph[x]):
                        if (y == tv):
                            self._free_nodes_for_build._graph[x].pop(y, None)
                    if (x == tv or self._free_nodes_for_build._graph[x] == {}):
                        self._free_nodes_for_build._graph.pop(x, None)
                        if (x in terminalVertices):
                            print "Stop. Status: Mapping couldn't be built."
                            self.log.writelog("STOP. NOT CONNECTED GRAPH\n")
                            self.log.writelog("--------\n")
                            self.log.writestat(str(-1)+"\n")
                            return 2

            forest = []
            for (key, val) in self._free_nodes_for_build._graph.items():
                forest.append([key])

            for graph_node_i in set(self._free_nodes_for_build._graph):
                for graph_node_j in set(self._free_nodes_for_build._graph[graph_node_i]):
                    for tr in forest:
                        if (graph_node_i in tr) and not (graph_node_j in tr):
                            for t in forest:
                                if (graph_node_j in t):
                                    for k in t:
                                        tr.append(k)
                                    forest.remove(t)
                                    break
            if (len(forest) != 1):
                for t in forest:
                    if (terminalVertices[0] in t):
                        for v in terminalVertices:
                            if (not(v in t)):
                                print "Stop. Status: Mapping couldn't be built."
                                self.log.writelog("STOP. NOT CONNECTED GRAPH\n")
                                self.log.writelog("--------\n")
                                self.log.writestat(str(-1)+"\n")
                                return 2

            resultSteinerTree = self._free_nodes_for_build.build_Steiner_tree_2_approxim(terminalVertices)
            # Print resultSteinerTree
            print "Result Steiner Tree:"
            for (key, value) in resultSteinerTree.items():
                print "\t", key, value
            print "Free Nodes:"
            for (key, value) in self._free_nodes._graph.items():
                print "\t", key, value


            for n1 in set(resultSteinerTree):
                for x in set(self._free_nodes._graph):
                    for y in set(self._free_nodes._graph[x]):
                        if (y == n1):
                            self._free_nodes._graph[x].pop(y, None)
                    if (x == n1 or self._free_nodes._graph[x] == {}):
                        self._free_nodes._graph.pop(x, None)
                        if (x in tver):
                            print "Stop. Status: Mapping couldn't be built."
                            print "CROSS !!!"
                            self.log.writelog("STOP. CROSS\n")
                            self.log.writelog("--------\n")
                            self.log.writestat(str(-1)+"\n")
                            return 3

            
            #=============== MODIFICATION BLOCK END ======================

            rst = Graph(resultSteinerTree)
            self.SteinerTrees[i] = rst
            tmp = {}
            print self.listOfTerminalVertices    
            for v in self.listOfTerminalVertices[i]:
                (path, dist, hops) = rst.Dijkstra_algorithm(v,"hops")
                for k in self.listOfTerminalVertices[i]:
                    if v != k:
                        res_path, res_dist = rst.get_path(k, hops, path, dist)
                        tmp[(v,k)] = res_path
            self.resultBigSwitchRouteMapping[i] = tmp
            vBS = set(resultSteinerTree)
            tmptmp = list(vBS)
            self.resultVerticesMapping[count] = tmptmp
            self.listOfTerminalVertices[i]=list(vBS)
            count += 1
            verticesForBS =  verticesForBS.union(vBS)
            listForCommonNodeFinding.append(vBS)
        for i in xrange(len(listForCommonNodeFinding)):
            for j in xrange(len(listForCommonNodeFinding)):

                #if there is vertice which belongs two Steiner Trees then 1. Print "STOP" and algorithm finishes work.
                #                              2. Log state to file
                if i!= j and len(listForCommonNodeFinding[i].intersection(listForCommonNodeFinding[j])) > 0:
                    print "Stop. Status: Mapping couldn't be built."
                    self.log.writelog("STOP. STEINTER ")
                    self.log.writelog("[")
                    for k in self.SteinerTrees[i].get_graph().keys():
                        self.log.writelog(str(k)+" ")
                    #self.log.writelog(str(self.SteinerTrees[i])+" ")
                    self.log.writelog("]")
                    self.log.writelog("[")
                    for k in self.SteinerTrees[j].get_graph().keys():
                        self.log.writelog(str(k)+" ")
                    self.log.writelog("]\n")
                    self.log.writelog("--------\n")
                    self.log.writestat(str(-1)+"\n")
                    return 3 

        #Calculate the number of free remaining physical vertices and remaining virtual vertices
        self.remainingPhyVertices = set(self._physical_graph.get_graph()).difference(verticesForBS)
        remainingVirVertices_t = set(self._virtual_graph.get_graph())
        self.remainingVirVertices = list(remainingVirVertices_t)    
        self.remainingVirVertices.sort()
        for i in xrange(len(self.listOfTerminalVertices)):
            self.remainingVirVertices.pop(0)
        return 0

    #Check: comparison remaining physical vertices and remaining virtual vertices. Log the state if rem. p.v < rem. v.v.
    def _second_step_checking_mapping(self):
        if len(self.remainingPhyVertices) < len(self.remainingVirVertices):
            print "Stop. Status: Mapping couldn't be built."
            self.log.writelog("STOP\n")
            self.log.writelog("--------\n")
            self.log.writestat(str(-1)+"\n")
            return 1
        return 0

    #Third step: 1. Set mapping for virtual links (to physical pathes) between VBSs
    #         2. Set mapping for virtual switches (to physical switches): generate test permutation for virtual switches allocation
    #         3. Set mapping for virtual links (to physical pathes) between virtual swithes which allocated on physical switches by test permutation
    def _third_step_construct_virtual_switches_and_virtual_links_mapping(self):
        permutPhy = self._generatePermutataionsWithoutRepetition(frozenset(self.remainingPhyVertices),len(self.remainingVirVertices))
        wasFound = True
        pv = self.remainingVirVertices
        connected = []
        switchRouteMapping_1 = {}
        
        #Set mapping for virtual links (to physical pathes) between VBSs
        for vs in self._virtual_graph.get_graph().keys():
            if vs < len(list(self.listOfTerminalVertices)):
                aVS =  self._virtual_graph.get_adjacent_vertices(vs)
                for avs in aVS: 
                    if avs < len(list(self.listOfTerminalVertices)):
                        if (vs,avs) in connected:
                            continue
                        distPathMap = {}
                        #Find the shortest pathes between all pairs of physical vertices (which belongs different VBSs) 
                        for t in self.listOfTerminalVertices[vs]:
                            (path, dist, hops) = self._physical_graph.Dijkstra_algorithm(t,"throughput")
                            for v in self.listOfTerminalVertices[avs]:
                                result_path, result_dist = self._physical_graph.get_path(v,hops,path,dist)
                                distPathMap[result_dist] = [result_path,t,v]
                        #Find the shortest of shortest pathes
                        keys = distPathMap.keys()
                        keys.sort()
                        bottleneck_value = self._find_bottleneck(distPathMap[keys[0]][0])
                        #Check path's bottleneck for Virtual link's SLA
                        if bottleneck_value > self._virtual_graph.get_graph()[vs][avs]:
                            tmp = copy.deepcopy(distPathMap[keys[0]][0])
                            tmp.reverse()
                            self.resultVirtualLinksMapping[(vs,avs)] = distPathMap[keys[0]][0]
                            self.resultVirtualLinksMapping[(avs,vs)] = tmp
                            self._physical_graph.update_throughputs(tmp, self._virtual_graph.get_graph()[vs][avs])
                            if avs not in switchRouteMapping_1.keys():
                                switchRouteMapping_1.setdefault(avs,[])
                            if distPathMap[keys[0]][2] not in switchRouteMapping_1[avs]:
                                switchRouteMapping_1[avs].append(distPathMap[keys[0]][2])
                            if vs not in switchRouteMapping_1.keys():
                                switchRouteMapping_1.setdefault(vs,[])
                            if distPathMap[keys[0]][1] not in switchRouteMapping_1[vs]:
                                switchRouteMapping_1[vs].append(distPathMap[keys[0]][1])
                            connected.append((vs,avs))
                            connected.append((avs,vs))
                        else:
                            wasFound = False
                            break
                if wasFound == False:
                    break
        #If path was not found then 1. Print 'STOP'
        #                2. Log the state
        if wasFound == False:
            print "Stop. Status: Mapping couldn't be built."
            self.log.writelog("STOP\n")
            self.log.writelog("--------\n")
            self.log.writestat(str(-1)+"\n")
            return 1
        self._physical_graph.do_reset_copy_of_graph()    
        permutation_counter = 0
        
        #Factorial of n calculation
        def factorial(n):
            if n == 1 or n == 0:
                return 1
            else:
                return n*factorial(n-1)

        self.log.writelog(str(len(self.remainingPhyVertices))+" "+str(len(self.remainingVirVertices))+" ")
        permut_var = str(factorial(len(self.remainingPhyVertices))/factorial(len(self.remainingPhyVertices)-len(self.remainingVirVertices)))

        #Generate test physical switch permuattaion for virtual switch allocation
        for pp in self. _generatePermutataionsWithoutRepetition(list(self.remainingPhyVertices),len(self.remainingVirVertices)):
            #Timeout situation (exceeding the number of iteration without success mapping)
            if (permutation_counter >= self.iter_param):
                print "Stop. Status: Mapping couldn't be built."
                self.log.writelog("STOP TIMEOUT\n")
                self.log.writelog("--------\n")
                self.log.writestat(str(-1)+"\n")
                return 1
            permutation_counter += 1
            wasFound = True
            VerticesMapping = dict.fromkeys(pv)
            i = 0
            for vs in VerticesMapping.keys():
                VerticesMapping[vs] = pp[i]
                i+=1
            wasFound = True
            self._physical_graph.reset_throughputs()
            switchRouteMapping = {}
            connected = []
            virtualLinksMapping = {}

            #Set mapping for virtual links (to physical pathes) between virtual swithes which allocated on physical switches by test permutation
            for vs in pv:
                    
                aVS =  self._virtual_graph.get_adjacent_vertices(vs)
                (path, dist, hops) = self._physical_graph.Dijkstra_algorithm(VerticesMapping[vs],"throughput")
                for avs in aVS: 
                    #If adjacent vertice is VBS
                    if avs < len(list(self.listOfTerminalVertices)):
                        if (vs,avs) in connected:
                            continue
                        distPathMap = {}
                        for v in self.listOfTerminalVertices[avs]:
                            result_path, result_dist = self._physical_graph.get_path(v,hops,path,dist)
                            distPathMap[result_dist] = [result_path,v]
                        keys = distPathMap.keys()
                        keys.sort()
                        bottleneck_value = self._find_bottleneck(distPathMap[keys[0]][0])
                        #Check path's bottleneck for Virtual link's SLA
                        if bottleneck_value > self._virtual_graph.get_graph()[vs][avs]:
                            tmp = copy.deepcopy(distPathMap[keys[0]][0])
                            tmp.reverse()
                            virtualLinksMapping[(vs,avs)] = distPathMap[keys[0]][0]
                            virtualLinksMapping[(avs,vs)] = tmp
                            self._physical_graph.update_throughputs(tmp, self._virtual_graph.get_graph()[vs][avs])
                            if avs not in switchRouteMapping.keys():
                                switchRouteMapping.setdefault(avs,[])
                            if distPathMap[keys[0]][1] not in switchRouteMapping[avs]:
                                switchRouteMapping[avs].append(distPathMap[keys[0]][1])
                            connected.append((vs,avs))
                            connected.append((avs,vs))
                        else:
                            wasFound = False
                            break
                    #If adjacent vertice is VS
                    else:    
                        if (vs,avs) in connected:
                            continue
                        result_path, result_dist = self._physical_graph.get_path(VerticesMapping[avs],hops,path,dist)
                        bottleneck_value = self._find_bottleneck(result_path)
                        #Check path's bottleneck for Virtual link's SLA
                        if bottleneck_value >=self._virtual_graph.get_graph()[vs][avs]: 
                            tmp = copy.deepcopy(result_path)
                            tmp.reverse()
                            virtualLinksMapping[(vs,avs)] = result_path
                            virtualLinksMapping[(avs,vs)] = tmp
                            self._physical_graph.update_throughputs(tmp, self._virtual_graph.get_graph()[vs][avs])
                            connected.append((vs,avs))
                            connected.append((avs,vs))
                        else:
                            wasFound = False
                            break
                if wasFound == False:
                    break
            if wasFound == True:
                self.resultVirtualLinksMapping.update(virtualLinksMapping)
            
                #add vertices to correct switch routes providing    
                tmp = dict.fromkeys(VerticesMapping)
                for t in tmp.keys():
                    tmp[t] = []
                    tmp[t].append(VerticesMapping[t])
                self.resultVerticesMapping.update(tmp)
                #for k in switchRouteMapping.keys():
                for k in switchRouteMapping_1.keys():
                #tmp = switchRouteMapping[k]
                    tmp = switchRouteMapping_1[k]
                    for t in tmp:
                        if switchRouteMapping.has_key(k):
                            if t not in switchRouteMapping[k]:
                                switchRouteMapping[k].append(t)
                        else:
                            switchRouteMapping[k] = []
                            switchRouteMapping[k].append(t)
                res = {}
                for i in switchRouteMapping.keys():
                    rst = self.SteinerTrees[i]
                    for j in switchRouteMapping[i]:
                        (path, dist, hops) = rst.Dijkstra_algorithm(j,"hops")
                        tmp = {}
                        for v in self.listOfTerminalVertices_backup[i]:
                            if v != j:
                                res_path, res_dist = rst.get_path(v, hops, path, dist)
                                tmp[(j,v)] = res_path
                                t = copy.deepcopy(res_path)
                                t.reverse()
                                tmp[(v,j)] = t
                        for v in switchRouteMapping[i]:
                            if v != j:
                                res_path, res_dist = rst.get_path(v, hops, path, dist)
                                tmp[(j,v)] = res_path
                                t = copy.deepcopy(res_path)
                                t.reverse()
                                tmp[(v,j)] = t
                        val = self.resultBigSwitchRouteMapping[i]
                        val.update(tmp)
                        self.resultBigSwitchRouteMapping[i] = val
                break
        
        #If mapping was not found then 1. Print 'STOP'
        #                   2. Log the state
        if wasFound == False:
            print "Stop. Status: Mapping couldn't be built."
            self.log.writelog("STOP\n")
            self.log.writelog("--------\n")
            self.log.writestat(str(-1)+"\n")
            return 1
        else:
            state = str(permutation_counter)
            state+="/"
            state+=permut_var+"\n"
            self.log.writelog(state)
            self.log.writelog("--------\n")
            self.log.writestat(str(permutation_counter)+"\n")
            return 0

    #Print all results    
    def _print_results(self):
        print "result Vertices Mapping"
        print self.resultVerticesMapping
        print "Result BigSwitchRoutes Mapping"
        print self.resultBigSwitchRouteMapping
        print "Result Virtual Links Mapping"
        print self.resultVirtualLinksMapping

    #Build "virtual-to-physical" mapping consist of 3 main steps. Check 'status' after every step finishing
    def build_virtual_to_physical_mapping(self, physical_network, virtual_network, listOfTerminalVertices):
        res = self._first_step_construct_Big_switches_mapping(physical_network, virtual_network, listOfTerminalVertices)
        if res != 0:
            return res
            
        res = self._second_step_checking_mapping()
        if res != 0:
            return res
            
        res = self._third_step_construct_virtual_switches_and_virtual_links_mapping()
        if res == 0:
            self._print_results()

        return res
    
    #Perumtation without repetition generator (in lexicographical order.    
    def _generatePermutataionsWithoutRepetition(self,lst,n):
        if n == 0:
            yield []
        else:
            for i in xrange(len(lst)):
                for cc in self._generatePermutataionsWithoutRepetition(lst[:i]+lst[i+1:],n-1):
                    yield[lst[i]]+cc 

    #Find the link with minimal throughput in path (that is 'bottleneck')
    def _find_bottleneck(self, path):
        tmp = []
        for i in xrange(len(path)-1):
            tmp.append(self._physical_graph.get_weight_of_edge(path[i],path[i+1]))
        tmp.sort()
        return tmp[0]


if __name__=="__main__":
    args = []
    count = 0 
    for arg in sys.argv:
        if count:
            args.append(int(arg))
        count+=1
    print args
    log = VPALogger("logfile", "stat")
    
    test_amount = args[1]
    iterations = args[2]
    test_model = args[0]
    
    if test_model == 0:
        vpa = VPAlgorithm(log,1)
        vpa.build_virtual_to_physical_mapping(None,None,None)
    else:
        vpa = VPAlgorithm(log, iterations)
        
    tester = VPATester(log,vpa)
        
    if test_model == 1:
        result = tester.test_data_centers(test_amount)
    elif test_model == 2:
        result = tester.test_enterprise(test_amount)
    elif test_model == 3:
        result = tester.test_model_1(test_amount)
    elif test_model == 4:
        result = tester.test_model_2(test_amount)
        
    #tester.test_plod(50)
    
    print "RESULT: ", result[0], " successeful from ", test_amount, " tests - ", 100.0 * result[0] / test_amount, "%" 
    print "TYPE 1: ", result[1]
    print "TYPE 2: ", result[2]
    print "TYPE 3: ", result[3]
