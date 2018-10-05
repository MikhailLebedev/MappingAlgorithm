import os
from fattree_gen import construct_fattree
from converter import convert_from_gml
from converter import get_node_number
from graph_generator import PLOD_based_generator
from graph_generator import do_visual_representation
import random

#class for "virtual-to-physical algorithm" testing
class VPATester:
    def __init__(self, logger, algorithm):
        self.log = logger
        self.algorithm = algorithm
    
    #get second-order neighbours of vertex
    def get_neighbours(self, graph, vert):
        res = set()
        for v in graph[vert].keys():
            res.add(v)
            for t in graph[v].keys():
                res.add(t)    
        return res

    #Both physical and virtual topologies are PLOD-like topologies.
    #There are two groups of terminal vertices (that is two big (border) switches). 
    #Every group consists of from 2 to 4 second- or first- order neighbours.
    def test_plod(self, iter_param):
        
        #remove element from list
        def rm_elem(lst, elem):
            new_lst = []
            for i in xrange(len(lst)):
                if lst[i] != elem:
                    new_lst.append(lst[i])
            return new_lst
        #DFS for graph implementation 
        def Depth_first_search(graph,v,vertices,count):
            vertices[v] = (1,count[0])
            for vert in graph[v].keys():
                if vertices[vert][0] == 0:
                    count[0]+=1
                    Depth_first_search(graph,vert,vertices,count)

        counter = 0
        while counter != iter_param:
            #Generate physical graph
            physical = PLOD_based_generator(60,80,0.5,50,100,100)
            
            #Simply connectivity of generated physical graph checking
            vertices = dict.fromkeys(physical,(0,-3))
            count = [0]
            Depth_first_search(physical, 0, vertices, count)
            nums = 0
            for v in vertices.keys():
                if vertices[v][1]!=-3:
                    nums+=1
            #if graph is non-simply connected then go to next graph
            if nums != 60:
                continue
            
            #Generate graph description in .dot format for GraphViz visualization
            do_visual_representation(physical,"physical/plod"+str(counter))
            
            #generate virtual graph
            virtual = PLOD_based_generator(30,40,0.8,30,20,20)  

            t_seq = []
            for i in xrange(60):
                t_seq.append(i)
            f_group = []
            s_group = []
            f_count = random.randint(2,4)
            s_count = random.randint(2,4)            
            self.log.writelog("{ ")

            #get random vertice
            a = random.choice(t_seq)

            self.log.writelog("src "+str(a)+" ")
            
            #get it's neighbours 
            neighbour = list(self.get_neighbours(physical,a))
            if len(neighbour) == 0:
                continue
            for i in xrange(len(neighbour)):    
                self.log.writelog(str(neighbour[i])+" ")
            self.log.writelog("} [ ")
            has_elem = True
            
            #fill the first group of terminal vertices from neighbours
            for i in xrange(f_count):
                if len(neighbour) == 0:
                    has_elem = False
                    break
                a = random.choice(neighbour)        
                f_group.append(a)
                neighbour = rm_elem(neighbour,a)
                t_seq = rm_elem(t_seq,a)
                self.log.writelog(str(a)+" ")
            if has_elem == False:
                continue
            self.log.writelog("] {")

            #Similarly, get random vertcies
            a = random.choice(t_seq)
            self.log.writelog("src "+str(a)+" ")
            
            #get it's neighbours
            neighbour = list(self.get_neighbours(physical,a))
            if len(neighbour) == 0:
                continue
            for i in xrange(len(neighbour)):    
                self.log.writelog(str(neighbour[i])+" ")
            self.log.writelog("} [ ")
            has_elem = True
            
            #fill the second group of terminal vertices from neighbours
            for i in xrange(f_count):
                if len(neighbour) == 0:
                    has_elem = False
                    break
                a = random.choice(neighbour)        
                s_group.append(a)
                neighbour = rm_elem(neighbour,a)
                t_seq = rm_elem(t_seq,a)
                self.log.writelog(str(a)+" ")
            if has_elem == False:
                continue
            self.log.writelog("]")
            l = []
            l.append(f_group)
            l.append(s_group)

            #start the VPA
            self.algorithm.build_virtual_to_physical_mapping(physical, virtual, l)
            counter+=1
            print "_______________________________________________"
    
    
    #Physical topology is FatTree topology.
    #Virtual topology is topology from TopologyZoo dataset.
    #There are two groups of terminal vertices (that is two big (border) switches). 
    #Every group consists of from 2 to 4 vertices from [48-55] and [56-63] ranges, respectively. 
    def test_data_centers(self, iter_param):
        
        def rm_elem(lst, elem):
            new_lst = []
            for i in xrange(len(lst)):
                if lst[i] != elem:
                    new_lst.append(lst[i])
            return new_lst
        
        directory = "../../../topos"
        files = os.listdir(directory)
        #Generate FatTree which consist of 4 level, 
        #16 vertices per level and 8 links for every core's vertices.
        physical = construct_fattree(16,4,4)
        counter = 0
        while counter != iter_param:
            while(True):
                f = random.choice(files)
                num_1 = get_node_number(directory+"/"+f)
                if (float(num_1) <= 0.7*16*5): 
     
                    #Get topology by converting from .gml format
                    virtual = convert_from_gml(directory+"/"+f,20)
                    break
            
            self.log.writelog(f+" "+str(num_1)+" ")
            t_seq_1 = [48,49,50,51,52,53,54,55]
            t_seq_2    = [56,57,58,59,60,61,62,63]
            f_group = []
            s_group = []
            f_count = random.randint(2,4)
            s_count = random.randint(2,4)
            self.log.writelog("[ ")
            
            #fill the first group of terminal vertices from neighbours
            for i in xrange(f_count):
                a = random.choice(t_seq_1)
                f_group.append(a)
                t_seq_1 = rm_elem(t_seq_1,a)
                self.log.writelog(str(a)+" ")
            self.log.writelog("] [")
            
            #fill the second group of terminal vertices from neighbours
            for j in xrange(s_count):
                a = random.choice(t_seq_2)
                s_group.append(a)
                t_seq_2 = rm_elem(t_seq_2,a)
                self.log.writelog(str(a)+" ")
            self.log.writelog("] ")
            l = []
            l.append(f_group)
            l.append(s_group)
            
            #start the VPA
            self.algorithm.build_virtual_to_physical_mapping(physical, virtual, l)
            counter+=1
            print "_______________________________________________"
    

    #Both physical and virtual topologies are topologies from TopologyZoo dataset.
    #There are two groups of terminal vertices (that is two big (border) switches). 
    #Every group consists of from 2 to 4 second- or first- order neighbours.
    def test_enterprise(self, iter_param):
        def rm_elem(lst, elem):
            new_lst = []
            for i in xrange(len(lst)):
                if lst[i] != elem:
                    new_lst.append(lst[i])
            return new_lst
        directory = "../../../topos"
        files = os.listdir(directory)
        num_1 = num_2 = 0
        counter = 0
        while counter != iter_param:
            while(True):
                f = random.choice(files)
                s = random.choice(files)
                num_1 = get_node_number(directory+"/"+f)
                num_2 = get_node_number(directory+"/"+s)
                if (float(num_1) <= 0.7*float(num_2)):  
                    
                    #Gets topologies by converting from .gml format
                    physical = convert_from_gml(directory+"/"+s,100)
                    virtual = convert_from_gml(directory+"/"+f,20)
                    break
            self.log.writelog("virtual:"+f+" "+str(num_1)+" ")
            self.log.writelog("physical:"+s+" "+str(num_2)+" ")
            t_seq = []
            for i in xrange(num_2-1):
                t_seq.append(i)
            f_group = []
            s_group = []
            f_count = random.randint(2,4)
            s_count = random.randint(2,4)
            
            self.log.writelog("{ ")
            
            #get random vertice
            a = random.choice(t_seq)
            self.log.writelog("src "+str(a)+" ")
            
            #get it's neighbours
            neighbour = list(self.get_neighbours(physical,a))
            if len(neighbour) == 0:
                continue
            for i in xrange(len(neighbour)):    
                self.log.writelog(str(neighbour[i])+" ")
            self.log.writelog("} [")
            has_elem = True
        
            #fill the first group of terminal vertices from neighbours
            for i in xrange(f_count):
                if len(neighbour) == 0:
                    has_elem = False
                    break
                a = random.choice(neighbour)        
                f_group.append(a)
                neighbour = rm_elem(neighbour,a)
                t_seq = rm_elem(t_seq,a)
                self.log.writelog(str(a)+" ")
            if has_elem == False:
                continue
            self.log.writelog("] {")
            
            #get random vertice
            a = random.choice(t_seq)
            self.log.writelog("src "+str(a)+" ")
            
            #get it's neighbours
            neighbour = list(self.get_neighbours(physical,a))
            if len(neighbour) == 0:
                continue
            for i in xrange(len(neighbour)):    
                self.log.writelog(str(neighbour[i])+" ")
            self.log.writelog("} [ ")
            has_elem = True    
            
            #fill the second group of terminal vertices from neighbours
            for i in xrange(f_count):
                if len(neighbour) == 0:
                    has_elem = False
                    break
                a = random.choice(neighbour)        
                s_group.append(a)
                neighbour = rm_elem(neighbour,a)
                t_seq = rm_elem(t_seq,a)
                self.log.writelog(str(a)+" ")
            if has_elem == False:
                continue
            self.log.writelog("]")
            l = []
            l.append(f_group)
            l.append(s_group)
            #start the VPA
            self.algorithm.build_virtual_to_physical_mapping(physical, virtual, l)
            counter+=1
            print "_______________________________________________"
    
             
    #Both physical and virtual topologies are PLOD-like topologies.
    #There are two groups of terminal vertices (that is two big (border) switches). 
    #Every group consists of 3 manually seted vertices.
    def test_model_1(self, iter_param):
        for i in xrange(iter_param):
            physical = PLOD_based_generator(14,50,0.5,50,100,100)  
            virtual = PLOD_based_generator(6,12,0.5,50,20,20)
            do_visual_representation(physical,"physical/"+str(i))
            do_visual_representation(virtual,"virtual/"+str(i))
            f_group = [0,1,2]
            s_group = [11,12,13]
            l = []
            l.append(f_group)
            l.append(s_group)
            #start the VPA
            self.algorithm.build_virtual_to_physical_mapping(physical, virtual, l)
            print "_______________________________________________"
    
    
    #Physical topology is PLOD-like topology.
    #Virtual topology is manually seted trinagle-like topology.
    #There are two groups of terminal vertices (that is two big (border) switches). 
    #Every group consists of from 2 manually seted vertices.
    def test_model_2(self, iter_param):
        for i in xrange(iter_param):
            physical = PLOD_based_generator(14,50,0.5,50,100,100)  
            virtual = {}
            for j in [0,1,2]:
                virtual[j] = {}
            virtual[0][1] = 20
            virtual[0][2] = 20
            virtual[1][0] = 20
            virtual[1][2] = 20
            virtual[2][0] = 20
            virtual[2][1] = 20
            do_visual_representation(physical,"physical/"+str(i))
            do_visual_representation(virtual,"virtual/"+str(i))
            f_group = [0,1]
            s_group = [9,10]
            l = []
            l.append(f_group)
            l.append(s_group)
            #start the VPA
            self.algorithm.build_virtual_to_physical_mapping(physical, virtual, l)
            print "_______________________________________________"
