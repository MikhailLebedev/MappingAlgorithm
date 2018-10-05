import sys
import random


#implemenation generator based on Power Law Out Degree (PLOD) algorithm and recursive generator (RSG)
#source: C.R. Palmer, J.G.Stephan "Generating Network Topologies That Obey Power Laws"
def PLOD_based_generator(vertices_number, edges_number, alpha, beta, left_border, right_border):
    graph = {}
    degrees = []
    #calculate the degree for every vertice in graph
    for i in xrange(vertices_number):
        x = random.randint(1,vertices_number)
        graph.setdefault(i,{})
        if x!=0:
            #power law 
            deg =  int(beta*x**(-alpha))
            if deg == 0:
                #It use for slimpy connectivity of graph providing
                degrees.append(2)
            else:
                degrees.append(deg)
        
        else:
            degrees.append(2)
    #set the edge between two random vertices with positive degree's credit
    for j in xrange(edges_number):
        while 1:
            r = random.randint(0,vertices_number-1)
            c = random.randint(0,vertices_number-1)
            if r != c and degrees[r] > 0 and degrees[c] > 0:
                degrees[r]-=1
                degrees[c]-=1
                weight = random.randint(left_border, right_border)
                graph[r].setdefault(c,weight)
                graph[c].setdefault(r,weight)
                break
    for j in graph.keys():
        if graph[j] == {}:
            while 1:
                r = random.randint(0,vertices_number-1)
                if r!=j:
                    break
            weight = random.randint(left_border, right_border)
            graph[j].setdefault(r,weight)
            graph[r].setdefault(j,weight)
            
    return graph

#Another graph generator
#source: C.R. Palmer, J.G.Stephan "Generating Network Topologies That Obey Power Laws"
def Recursive_Topology_Generator(vertices_number, edges_number, alpha, beta, gamma, epsilon):
    graph = {}
    def gensum(n):
        n_1 = (float(n)/2)**2 - float(n)/2
        n_2 = (float(n)/2)**2
        if n == 2.0 or n ==1.0:
            return [0,1]
        else:
            k = 1/float(float(alpha/n_1) + float((beta+gamma)/n_2) + float(epsilon/n_1))
            probability = random.random()
            prob_1 = float(alpha*k/n_1)
            prob_2 = prob_1 + float((beta+gamma)*k/n_2)
            prob_3 = prob_2 + float(epsilon*k/n_1)
            if prob_1 > probability:
                return gensum(n/2)
            elif prob_2 > probability:
                res = gen(n/2) 
                res[1] += n/2
                return res
            elif prob_3 > probability:
                res = gen(n/2)
                res[0]+=n/2
                res[1]+=n/2
                return res
    def gen(n):
        if n == 1.0:
            return [0,0]    
        prob_1 = alpha
        prob_2 = prob_1 + beta
        prob_3 = prob_2 + gamma
        prob_4 = prob_3 + epsilon
        probability = random.random()
        if prob_1 > probability:
            return gen(n/2)
        if prob_2 > probability:
            res = gen(n/2) 
            res[1] += n/2
            return res
        if prob_3 > probability:
            res = gen(n/2)
            res[0] += n/2
            return res
        if prob_4 > probability:
            res = gen(n/2) 
            res[0]+=n/2
            res[1]+=n/2
            return res

    for i in xrange(vertices_number):
        graph.setdefault(i,{})
    i = 0
    while i != edges_number:
        result = gensum(vertices_number-1)
        u = result[0]
        v = result[1]
        if v in graph[u].keys():
            graph[u][v] += 1
            graph[v][u] += 1
        else:
            graph[u].setdefault(v,1)
            graph[v].setdefault(u,1)
            i+=1
    return graph 
        
#Generate the undirected graph description in .dot format
def do_visual_representation(graph, name_of_graph):
                f = open(name_of_graph+".dot", "w")
                f.write("graph G{\n")
                for i in graph:
                        f.write(str(i)+" [label="+str(i)+"];\n")
                for i in graph:
                        for j in graph[i].keys():
                                if (j>i):
                                        f.write(str(i)+" -- "+str(j)+" [label="+str(graph[i][j])+"];\n")
                f.write("}")

if __name__=="__main__":
    N = int(sys.argv[1])
    M = int(sys.argv[2])
    alpha = int(sys.argv[3])
    beta = int(sys.argv[4])
    left_border = 791
    right_border  = 1480
    #graph = PLOD_based_generator(N,M,alpha,beta,left_border, right_border)
    graph = PLOD_based_generator(12,20,0.8,50,100,100)
    #graph = Recursive_Topology_Generator(20,100,0.1,0.4,0.4,0.1)
