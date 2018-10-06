import copy

#Construct the FatTree with 'lev_num' levels, 
#'node_per_lev_num' vertices per level and 2*'links' links 
#for every core's vertice
#An example of FatTree with (4,2,2) configuration:
#  _    _    _    _
# |_|--|_|--|_|--|_|
# | \  / |  | \  / |
# |  \/  |  |  \/  |
# |  /\  |  |  /\  |
# |_/  \_|  |_/  \_|
# |_|--|_|  |_|--|_|
def construct_fattree(node_per_lev_num, lev_num, links):
    
    #Set links between 'first' and 'second' levels 
    def do_links(graph, first, second, step, curr_lev):
        
        #cyclic shift
        def rotate(lst, shift):
            return lst[-shift:] + lst[:-shift]

        step = len(first)/links
        second_backup_1 = copy.deepcopy(second)
        second_backup_2 = copy.deepcopy(second)
        for i in xrange(len(first)):
            for j in xrange(links):
                graph[first[i]][second[j*step]] = 100
                graph[second[j*step]][first[i]] = 100
            second = rotate(second, -1)
        if step == 1:
            return
        second_backup_1 = get_left_part(second_backup_1)
        second_backup_2 = get_right_part(second_backup_2)
        lvl_curr = get_level(curr_lev+1)
        lvl_2 = get_level(curr_lev+2)
        sec_1 =  find_peace(lvl_curr,lvl_2, len(second_backup_1), second_backup_1[0])
        sec_2 =  find_peace(lvl_curr,lvl_2, len(second_backup_2), second_backup_2[0])
        
        #Do it for halves
        do_links(graph, second_backup_1, sec_1, links, curr_lev+1)
        do_links(graph, second_backup_2, sec_2, links, curr_lev+1)


    def find_peace(lst_1, lst_2, l, b_elem):
        mode = False
        idx = -1
        count=0
        res = []
        for i in xrange(len(lst_1)):
            if lst_1[i] == b_elem:
                idx = i
                break
        for i in xrange(l):
            res.append(lst_2[i+idx])
        return res
    #Get left half of list
    def get_left_part(lst):
        n_lst = []
        for i in xrange(len(lst)/2):
            n_lst.append(lst[i])
        return n_lst
    #Get right half of list
    def get_right_part(lst):
        n_lst = []
        for i in xrange(len(lst)/2):
            n_lst.append(lst[i+len(lst)/2])
        return n_lst
    
    #Generate level with 'num' number
    def get_level(num):
        lev = []
        for i in xrange(num*node_per_lev_num,num*node_per_lev_num+node_per_lev_num):
            lev.append(i)
        return lev

    #Generatye the FatTree
    graph = {}
    for i in xrange(node_per_lev_num*lev_num):
        graph.setdefault(i,{})
    
    for i in xrange(5):
        get_level(i)
    first = get_level(0)
    second = get_level(1)
    do_links(graph, first,second, links, 0)
    for k in graph.keys():
        print k, graph[k]
    return graph

if __name__=="__main__":
    fattree_gen(16,5,2)
