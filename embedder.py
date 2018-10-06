#!/usr/bin/env python

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import sys
import json
import threading
import logging as log
import urllib2
from argparse import ArgumentParser
import subprocess
import time
#------------------------------------
import VPAlgorithm
from VPAlgorithm import VPAlgorithm
from Logger import VPALogger

CLONE_VM = '/usr/bin/VBoxManage clonevm OVX --snapshot Master --mode machine --options link --name %s --register'
GET_IP_VM = '/usr/bin/VBoxManage guestcontrol %s execute --image /home/ovx/get-ip.sh --wait-exit --username ovx --password ovx --wait-stdout -- eth0'
START_VM = '/usr/bin/VBoxManage startvm %s --type headless'
#START_VM = '/usr/bin/VBoxManage startvm %s'
STOP_VM = '/usr/bin/VBoxManage controlvm %s poweroff'
UNREGISTER_VM = '/usr/bin/VBoxManage unregistervm %s --delete'

class ERROR_CODE:
    PARSE_ERROR = -32700          # Invalid JSON was received by the server.
    INVALID_REQ = -32600          # The JSON sent is not a valid Request object.
    METHOD_NOT_FOUND = -32601     # The method does not exist / is not available.
    INVALID_PARAMS = -32602       # Invalid method parameter(s).
    INTERNAL_ERROR = -32603          # Internal JSON-RPC error.

class OVXException(Exception):
    def __init__(self, code, msg, tenantId, rollback=False):
        self.code = code
        self.msg = msg
        self.rollback = rollback
        self.tenantId = tenantId

    def __str__(self):
        return '%s (%s)' % (self.msg, self.code)

class EmbedderException(Exception):
    def __init__(self, code, msg):
        self.code = code
        self.msg = msg

    def __str__(self):
        return '%s (%s)' % (self.msg, self.code)

# Convert dotted hex to long value
def hexToLong(h):
    return int(h.replace(':', ''), 16)

# Convert long value to dotted hex value with specified length in bytes
def longToHex(l, length=8):
    h = ("%x" % l)
    if len(h) % 2 != 0:
        h = '0' + h
    result = ':'.join([h[i:i+2] for i in range(0, len(h), 2)])
    prefix = '00:' * (length - (len(h) / 2) - (len(h) % 2))
    return prefix + result

class Routing():
    def __init__(self, topology):
        try:
            self.nodes = topology['switches']
            self.links = {}
            for link in topology['links']:
                src = link['src']
                dst = link['dst']
                self.links[(src['dpid'], src['port'])] = (dst['dpid'], dst['port'])
            self.SP = {}
        except:
            pass
    
    def _neighbours(self, node):
        """Returns list of nodes that are neighbour to node.

        Assumes nodes are connected on at most one port, i.e., multigraphs are not supported (should
        delete duplicate entries from result.

        """
        return [dst_node for (src_node,src_port),(dst_node,dst_port) in self.links.iteritems() if src_node == node]

    def _shortestPath(self, src, dst):
        """Calculates shortest path between src and dst switches and stores it in the SP dict.
        
        Assumes graph is connected.
        
        """
        distance = {}
        previous = {}
        for node in self.nodes:
            distance[node] = sys.maxint
        distance[src] = 0
        # Sort Q according to distance
        Q = sorted(distance, key=distance.get)
            
        while Q:
            current = Q.pop(0)
            if distance[current] == sys.maxint:
                log.error("Graph is disconnected")
                # TODO: raise expection
                break
            for neighbour in self._neighbours(current):
                alt = distance[current] + 1
                if alt < distance[neighbour]:
                    distance[neighbour] = alt
                    previous[neighbour] = current
                    # TODO: really should use a heap instead of resorting every time
                    Q = sorted(distance, key=distance.get)
            # Path is between current and src (first iteration of outer while: current == src, previous[current] undefined)
            x = current
            path = []
            while previous.get(x) >= 0:
                path.append(x)
                x = previous[x]
            path.append(src)
            path.reverse()
            self.SP[(src, current)] = path

    def _findPorts(self, dpid1, dpid2):
        """Returns tuple (port_out, port_in) with port_out on dpid1 and port_in on dpid2, None if switches are not connected."""
        # Iterates over all links in worst case!
        for (dpid_out, port_out), (dpid_in, port_in) in self.links.iteritems():
            if (dpid1 == dpid_out) and (dpid2 == dpid_in):
                return (port_out, port_in)
        return None

    def _findOutPort(self, dpid1, dpid2):
        """Returns output port on dpid1 that connects to dpid2, None if switches are not connected."""
        return self._findPorts(dpid1, dpid2)[0]

    def _findInPort(self, dpid1, dpid2):
        """Returns input port on dpid2 that is connected to dpid1, None if switches are not connected."""
        return self._findPorts(dpid1, dpid2)[1]

    def getRoute(self, dpid_in, dpid_out):
        """Find route between dpid_in and dpid_out.

        Route is of form [ dpid ]

        """
        # Catch trivial path
        if dpid_in == dpid_out:
            return [ (dpid_in) ]

        # Calculate path
        if (dpid_in, dpid_out) not in self.SP.keys():
            self._shortestPath(dpid_in, dpid_out)

        route = self.SP[(dpid_in, dpid_out)]

        return route

    def parseRoute(self, route):
        """Parse route specified and return OVX-type path string.
        
        Input route is of form [ dpid ], while return path is of form dpid1/port1-dpid2/port2,...
        
        """
        path = ''
        for index in xrange(0, len(route) - 1):
            outPort = self._findOutPort(route[index], route[index + 1])
            inPort = self._findInPort(route[index], route[index + 1])
            path += "%s/%s-%s/%s," % (parseDpid(route[index]), outPort, parseDpid(route[index + 1]), inPort)
        # Remove final comma
        return path[:-1]
  
class OVXClient():
    def __init__(self, host, port, user, password):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.base_url = "http://%s:%s/" % (self.host, self.port)
        self.tenant_url = self.base_url + 'tenant'
        self.status_url = self.base_url + 'status'
        
    def _buildRequest(self, data, url, cmd):
        j = { "id" : "ovxembedder", "method" : cmd, "jsonrpc" : "2.0" }
        h = {"Content-Type" : "application/json"}
        if data is not None:
            j['params'] = data
        return urllib2.Request(url, json.dumps(j), h)

    def _parseResponse(self, data):
        j = json.loads(data)
        if 'error' in j:
            e = OVXException(j['error']['code'], j['error']['message'], -1)
            log.error(e)
            raise e
        return j['result']

    def _connect(self, cmd, url, data=None):
        log.debug("%s: %s" % (cmd, data))
        try:
            passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
            passman.add_password(None, url, self.user, self.password)
            authhandler = urllib2.HTTPBasicAuthHandler(passman)
            opener = urllib2.build_opener(authhandler)
            req = self._buildRequest(data, url, cmd)
            ph = opener.open(req)
            return self._parseResponse(ph.read())
        except urllib2.URLError as e:
            log.error(e)
            sys.exit(1)
        except urllib2.HTTPError as e:
            if e.code == 401:
                log.error("Authentication failed: invalid password")
                # TODO
                sys.exit(1)
            elif e.code == 504:
                log.error("HTTP Error 504: Gateway timeout")
                # TODO
                sys.exit(1)
            else:
                log.error(e)
        except RuntimeError as e:
            log.error(e)

    def createNetwork(self, ctrls, net_address, net_mask):
        req = {'controllerUrls': ctrls, 
               'networkAddress': net_address, 'mask': net_mask}
        try:
            ret = self._connect("createNetwork", self.tenant_url, data=req)
            tenantId = ret.get('tenantId')
            if tenantId:
                log.info("Network with tenantId %s has been created" % tenantId)
            return tenantId
        except OVXException as e:
            e.rollback = False
            raise

    def removeNetwork(self, tenantId):
        req = {'tenantId': tenantId}
        try:
            ret = self._connect("removeNetwork", self.tenant_url, data=req)
            log.info("Network with tenantId %s has been removed" % tenantId)
        except OVXException as e:
            e.rollback = False
            raise
        
    def createSwitch(self, tenantId, dpids, dpid=None):
        req = {'tenantId': tenantId, 'dpids': dpids}
        if dpid:
            req["vdpid"] = dpid
        try:
            ret = self._connect("createSwitch", self.tenant_url, data=req)
            switchId = ret.get('vdpid')
            if switchId:
                pass
        #log.info("Switch with switchId %s has been created" % longToHex(switchId))
            return switchId
        except OVXException as e:
            e.rollback = True
            e.tenantId = tenantId
            raise

    def createPort(self, tenantId, dpid, port):
        req = {'tenantId': tenantId, 'dpid': dpid, 'port': port}
        try:
            ret = self._connect("createPort", self.tenant_url, data=req)
            switchId = ret.get('vdpid')
            portId = ret.get('vport')
            if switchId and portId:
                pass
                #log.info("Port on switch %s with port number %s has been created" % (longToHex(switchId), portId))
            return (switchId, portId)
        except OVXException as e:
            e.rollback = True
            e.tenantId = tenantId
            raise

    def connectLink(self, tenantId, srcDpid, srcPort, dstDpid, dstPort, algorithm, backup_num):
        req = {'tenantId': tenantId, 'srcDpid': srcDpid, 'srcPort': srcPort, 'dstDpid': dstDpid, 'dstPort': dstPort, 'algorithm': algorithm, 'backup_num': backup_num}
    #print "cl", req
    try:
            ret = self._connect("connectLink", self.tenant_url, data=req)
            linkId = ret.get('linkId')
            if linkId:
                pass
                #log.info("Link with linkId %s has been created" % linkId)
            return linkId
        except OVXException as e:
              e.rollback = True
              e.tenantId = tenantId
              raise

    def setLinkPath(self, tenantId, linkId, path, priority):
        req = {'tenantId': tenantId, 'linkId': linkId, 'path': path, 'priority': priority}
    #print "request here", req
    try:
            ret = self._connect("setLinkPath", self.tenant_url, data=req)
            if ret:
                pass
                #log.info("Path on link %s has been set" % linkId)
            return ret
        except OVXException as e:
            e.rollback = True
            e.tenantId = tenantId
            raise
        
    def connectHost(self, tenantId, dpid, port, mac):
        req = {'tenantId': tenantId, 'vdpid': dpid, 'vport': port, 'mac': mac}
        try:
            ret = self._connect("connectHost", self.tenant_url, data=req)
            hostId = ret.get('hostId')
            if hostId:
                pass
                #log.info("Host with hostId %s connected" % hostId)
            return hostId
        except OVXException as e:
            e.rollback = True
            e.tenantId = tenantId
            raise
            
    def connectRoute(self, tenantId, switchId, srcPort, dstPort, path, priority):
        req = {'tenantId': tenantId, 'vdpid': switchId, 'srcPort': srcPort, 'dstPort': dstPort, 'path': path, 'priority': priority}
        #print "connectroute", req
    try:
            ret = self._connect("connectRoute", self.tenant_url, data=req)
            routeId = ret.get('routeId')
            if routeId:
                pass
                log.info("Route with routeId %s on switch %s between ports (%s,%s) created" % (routeId, switchId, srcPort, dstPort))
            return routeId
        except OVXException as e:
            e.rollback = True
            e.tenantId = tenantId
            raise
        
    def createSwitchRoute(self, tenantId, switchId, srcPort, dstPort, path):
        req = {'tenantId': tenantId, 'dpid': switchId, 'srcPort': srcPort, 'dstPort': dstPort, 'path': path}
        try:
            ret = self._connect("createSwitchRoute", self.tenant_url, data=req)
            if ret:
                log.info("Route on switch %s between ports (%s,%s) created" % (switchId, srcPort, dstPort))
            return ret
        except OVXException as e:
            e.rollback = True
            e.tenantId = tenantId
            raise

    def startNetwork(self, tenantId):
        req = {'tenantId': tenantId}
        try:
            ret = self._connect("startNetwork", self.tenant_url, data=req)
            if ret:
                log.info("Network with tenantId %s has been started" % tenantId)
            return ret
        except OVXException as e:
            e.rollback = True
            e.tenantId = tenantId
            raise

    def getPhysicalTopology(self):
        ret = self._connect("getPhysicalTopology", self.status_url)
        try:
            if ret:
                log.info("Physical network topology received")
            return ret
        except OVXException as e:
            e.rollback = False
            raise

    def setInternalRouting(self, tenantId, dpid, algorithm, backup_num):
        req = {'tenantId': tenantId, 'vdpid': dpid, 'algorithm': algorithm, 'backup_num': backup_num}
        try:
            ret = self._connect("setInternalRouting", self.tenant_url, data=req)
            if ret:
                pass
        log.info("Internal routing of switch %s has been set to %s" % (longToHex(dpid), algorithm))
            return ret
        except OVXException as e:
            e.rollback = True
            e.tenantId = tenantId
            raise
        
class OVXEmbedderHandler(BaseHTTPRequestHandler):
    """
    Implementation of JSON-RPC API, defines all API handler methods.
    """
  
    def _buildResponse(self, json_id, result=None, error=None):
        """Returns JSON 2.0 compliant response"""
        res = {}
        res['jsonrpc'] = '2.0'
        # result and error are mutually exclusive
        if result is not None:
            res['result'] = result
        elif error is not None:
            res['error'] = error
        res['id'] = json_id
        return res

    def _buildError(self, code, message, data=None):
        """Returns JSON RPC 2.0 error object"""
        res = {}
        res['code'] = code
        res['message'] = message
        if data:
            res['data'] = data
        return res
#---------------------------------------------------------------------------------------------------
    #It allows try to set mapping for arbitrary topologies
    def doCustomTopoNetwork(self, controller, routing, subnet, hosts, switches, links):
    #translate path to OVX server adaptive format
    def translate_path(path_string):
        hop_list = path_string.split(",")
        path = ""
        for hop in hop_list:
            src, dst = hop.split("-")
            src_dpid, src_port = src.split("/")
            dst_dpid, dst_port = dst.split("/")
            src_long_dpid = int(src_dpid.replace(":", ""), 16)
            dst_long_dpid = int(dst_dpid.replace(":", ""), 16)
            path = path + str(src_long_dpid) + "/" + str(src_port) + "-" + str(dst_long_dpid) + "/" + str(dst_port) + ","
        if len(path) > 0:
            path.rstrip(",")
        return path
    
    print "*****BEGIN OF DO CUSTOM TOPO*****"    
    
    """Try to create OVX network with custom topology""" 
    client = self.server.client
        
    #get physical topology from OVX
    phyTopo = client.getPhysicalTopology()

        
    log_1 = VPALogger("uniq_4", "un_123")
    vpa = VPAlgorithm(log_1,1000)
    
    #data structures for storage of physical topology as a graph
    physical_graph = {}
    physical_dpid_to_node_map = {}
    physical_node_to_dpid_map = {}
    physical_link_to_edge_map = {}
    physical_edge_to_link_map = {}
    
    physical_dpids_count = 0
    
    #data structures for storage of virtual topology as a graph 
    virtual_graph = {}
    virtual_dpid_to_node_map = {}
    virtual_node_to_dpid_map = {}
    virtual_link_to_edge_map = {}
    virtual_edge_to_link_map = {}

    virtual_dpids_count = 0
    
    #construct physical graph (and graph -- topo maps)
    for dpid in phyTopo['switches']:
        physical_graph.setdefault(physical_dpids_count,{})
        physical_node_to_dpid_map[physical_dpids_count] = dpid
        physical_dpid_to_node_map[dpid] = physical_dpids_count
        physical_dpids_count += 1
    for link in phyTopo['links']:
        physical_edge_to_link_map[(physical_dpid_to_node_map[link['src']['dpid']],\
                            physical_dpid_to_node_map[link['dst']['dpid']])]= \
                    (link['src']['dpid'], link['src']['port'],\
                     link['dst']['dpid'], link['dst']['port'])
        physical_edge_to_link_map[(physical_dpid_to_node_map[link['dst']['dpid']],\
                            physical_dpid_to_node_map[link['src']['dpid']])]= \
                    (link['dst']['dpid'], link['dst']['port'],\
                     link['src']['dpid'], link['src']['port'])
        physical_graph[physical_dpid_to_node_map[link['src']['dpid']]].setdefault(physical_dpid_to_node_map[link['dst']['dpid']],1000)
        physical_graph[physical_dpid_to_node_map[link['dst']['dpid']]].setdefault(physical_dpid_to_node_map[link['src']['dpid']],1000)
    listOfTerminalVertices = []
    print "physical topo"
    for dpid in phyTopo['switches']:
        print dpid
    print ""
    print "HOSTS"
    print hosts
    
    #construct virtual graph (and graph -- topo maps) and terminal vertices
    for sw in switches:
        virtual_graph.setdefault(virtual_dpids_count,{})
        virtual_node_to_dpid_map[virtual_dpids_count] = sw['dpid']
        virtual_dpid_to_node_map[sw['dpid']] = virtual_dpids_count
        virtual_dpids_count += 1
        terminalVertices = []
        for host in  sw['attached_hosts']:
            if host != "NULL":
                for h in hosts:
                    if h['mac'] == host:
                        if physical_dpid_to_node_map[h['dpid']] not in terminalVertices:
                            terminalVertices.append(physical_dpid_to_node_map[h['dpid']])
                            print h['dpid']
        if len(terminalVertices) > 0:
            listOfTerminalVertices.append(terminalVertices)
    for link in links:
        virtual_edge_to_link_map[(virtual_dpid_to_node_map[link['dpid_dst']],\
                    virtual_dpid_to_node_map[link['dpid_src']])]=\
                    (link['dpid_dst'], link['dpid_src'])
        virtual_edge_to_link_map[(virtual_dpid_to_node_map[link['dpid_src']],\
                    virtual_dpid_to_node_map[link['dpid_dst']])]=\
                    (link['dpid_src'], link['dpid_dst'])
        virtual_graph[virtual_dpid_to_node_map[link['dpid_src']]].setdefault(virtual_dpid_to_node_map[link['dpid_dst']],int(link['SLA']))
        virtual_graph[virtual_dpid_to_node_map[link['dpid_dst']]].setdefault(virtual_dpid_to_node_map[link['dpid_src']],int(link['SLA']))
    
    print "Physical graph:"
    print physical_graph
    print "Virtual graph:"
    print virtual_graph
    print "listOfTerminalVertices"
    print listOfTerminalVertices
    "MAP FROM PHY NET TO GRAPH"
    print physical_dpid_to_node_map
    "MAP FROM VIR NET TO GRAPH"
    print virtual_dpid_to_node_map
    
    #start VPA for physical graph, virtual graph and listOfTerminalVertices
    resultVerticesMapping,resultBigSwitchRouteMapping,resultVirtualLinksMapping = \
    vpa.build_virtual_to_physical_mapping(physical_graph, virtual_graph, listOfTerminalVertices)    
    if resultVerticesMapping == None:
        return
    #phuscial_link_to_edge_map
    # spawn controller if necessary
        # TODO: do proper string comparison
        if controller['type'] == 'default':
            proto = self.server.ctrlProto
            host = self.server._spawnController()
            port = self.server.ctrlPort
            ctrls = ["%s:%s:%s" % (proto, host, port)]
        elif controller['type'] == 'custom':
            ctrls = controller['ctrls']
        else:
            raise EmbedderException(ERROR_CODE.INVALID_REQ, 'Unsupported controller type')
        (net_address, net_mask) = subnet.split('/')
        tenantId = client.createNetwork(ctrls, net_address, int(net_mask))
    
    #cosnstruct path as a "dpid_src/port_src-dpid_dst/port_dst-..." form     
    def construct_path(link, storage):
        res_path = ""
        path = storage[link]
        for i in xrange(len(path)-1):
            (dpid_src, port_src, dpid_dst, port_dst) = physical_edge_to_link_map[(path[i],path[i+1])]
            res_path+=str(dpid_src)+"/"+str(port_src)+"-"+str(dpid_dst)+"/"+str(port_dst)
            if i != len(path)-2:
                res_path+=","
        return str(res_path)

    #construct big switches which based on physical switches (use "createSwitch" call)
    print ""
    print "*****BEGIN OF CONSTRUCT SWITCHES*****"

    vport_pdpid_map = {}
    switchid_pdpid_map = {}

    for vertice in resultVerticesMapping.keys():
        print "virtual switch with dpid:",virtual_node_to_dpid_map[vertice], "was mapped to:"
        for node in resultVerticesMapping[vertice]:
            print "physical dpid:",physical_node_to_dpid_map[node] 
        print ""
        dpids = [hexToLong(physical_node_to_dpid_map[node]) for node in resultVerticesMapping[vertice]]
        switchId = client.createSwitch(tenantId, dpids, hexToLong(virtual_node_to_dpid_map[vertice]))
        for node in resultVerticesMapping[vertice]:
            switchid_pdpid_map[physical_node_to_dpid_map[node]] = switchId
    print "*****END OF CONSTRUCT SWITCHES*****"
        
    #host attaching to virtual switches (firstly, create virtual port using "createPort" call for this case, 
    #secondly, use "connectHost" for host attaching
    print ""
    print "*****BEGIN OF HOSTS ATTACHING******"
    for host in hosts:
        (vdpid, vport) = client.createPort(tenantId, hexToLong(host['dpid']), host['port'])
        client.connectHost(tenantId, vdpid, vport, host['mac'])
        if host['dpid'] not in vport_pdpid_map.keys():
            vport_pdpid_map[host['dpid']] = []
            vport_pdpid_map[host['dpid']].append(vport)
        else:
            vport_pdpid_map[host['dpid']].append(vport)
        print "host with mac:", host['mac'], "was attached to virtual switch with dpid:", host['dpid'], "via virtual port:", vport
        print ""
    print "*****END OF HOSTS ATTACHING*****"
    #construct virtual links using information from VPA.
    # 1. use "createPort" call to create port on virtual switch which based on physical switch.
    # 2. get physical path from VPA for virtual link and get OVX server-like form.
    # 3. use "connectLink" call to connect two virtual ports.
    # 4. use "setLinkPath" to set physical path.
    print ""
    print "*****BEGIN OF CONSTRUCT LINKS*****"
    connected = []
    print resultVirtualLinksMapping
    for link in resultVirtualLinksMapping.keys():
        if link not in connected:
            res = resultVirtualLinksMapping[link]
            if len(res)>2:
                (src_Dpid_1, src_Port_1, dst_Dpid_1, dst_Port_1) = physical_edge_to_link_map[(res[0],res[1])]
                (src_Dpid_2, src_Port_2, dst_Dpid_2, dst_Port_2) = physical_edge_to_link_map[(res[len(res)-2],res[len(res)-1])]
                        dst_dpid = hexToLong(dst_Dpid_2)
                src_dpid = hexToLong(src_Dpid_1)
                dst_port = int(dst_Port_2)
                src_port = int(src_Port_1)
                (srcVDpid, srcVPort) = client.createPort(tenantId, src_dpid, src_port)
                (dstVDpid, dstVPort) = client.createPort(tenantId, dst_dpid, dst_port)
                if dst_Dpid_2 not in vport_pdpid_map.keys():
                    vport_pdpid_map[dst_Dpid_2] = []
                    vport_pdpid_map[dst_Dpid_2].append(dstVPort)
                else:
                    vport_pdpid_map[dst_Dpid_2].append(dstVPort)
                if src_Dpid_1 not in vport_pdpid_map.keys():
                    vport_pdpid_map[src_Dpid_1] = []
                    vport_pdpid_map[src_Dpid_1].append(srcVPort)
                else:
                    vport_pdpid_map[src_Dpid_1].append(srcVPort)
            else:
                (src_Dpid_1, src_Port_1, dst_Dpid_1, dst_Port_1) = physical_edge_to_link_map[(res[0],res[1])]
                        dst_dpid = hexToLong(dst_Dpid_1)
                src_dpid = hexToLong(src_Dpid_1)
                dst_port = int(dst_Port_1)
                src_port = int(src_Port_1)
                (srcVDpid, srcVPort) = client.createPort(tenantId, src_dpid, src_port)
                (dstVDpid, dstVPort) = client.createPort(tenantId, dst_dpid, dst_port)
                if dst_Dpid_1 not in vport_pdpid_map.keys():
                    vport_pdpid_map[dst_Dpid_1] = []
                    vport_pdpid_map[dst_Dpid_1].append(dstVPort)
                else:
                    vport_pdpid_map[dst_Dpid_1].append(dstVPort)
                if src_Dpid_1 not in vport_pdpid_map.keys():
                    vport_pdpid_map[src_Dpid_1] = []
                    vport_pdpid_map[src_Dpid_1].append(srcVPort)
                else:
                    vport_pdpid_map[src_Dpid_1].append(srcVPort)
            path =  construct_path(link, resultVirtualLinksMapping)
            rev_path =  construct_path((link[1],link[0]), resultVirtualLinksMapping)
            linkId = client.connectLink(tenantId, srcVDpid, srcVPort, dstVDpid, dstVPort, 'manual', 0)
            client.setLinkPath(tenantId,linkId,translate_path(path),1)
            rev_link = (link[1],link[0])
            print "link: ", virtual_edge_to_link_map[link][0], "/", srcVPort, " - ",virtual_edge_to_link_map[link][1],"/",dstVPort, " was mapped into physical path:"
            print path
            print ""
            print "link: ", virtual_edge_to_link_map[link][1], "/", dstVPort, " - ",virtual_edge_to_link_map[link][0],"/",srcVPort, " was mapped into physical path:"
            print rev_path
            print ""
            #path =  construct_path(rev_link, resultVirtualLinksMapping)    
            #client.setLinkPath(tenantId,linkId,translate_path(path),1)
            connected.append(link)
            connected.append(rev_link)
    print "*****END OF CONSTRUCT LINKS*****"

    #construct internal routes (big switch routes) using information from VPA.
    # 1. get physical path from VPA for internal routes (between all pairs of big switch's "ports").
    # 3. use "setInternalRouting" call to decalre "manually" setting of path.
    # 4. use "connectPath" to set physical path.
    print ""
    print "*****BEGIN OF CONSTRUCT BIG SWITCH ROUTES*****"
    print resultBigSwitchRouteMapping
    for dpid in resultBigSwitchRouteMapping.keys():
        connected = []
        for route in resultBigSwitchRouteMapping[dpid]:
            path = resultBigSwitchRouteMapping[dpid][route]
            res_path = construct_path(route, resultBigSwitchRouteMapping[dpid])
            rev_path = resultBigSwitchRouteMapping[dpid][(route[1],route[0])]
            res_rev_path = construct_path((route[1],route[0]), resultBigSwitchRouteMapping[dpid])
            srcVPorts = vport_pdpid_map[physical_node_to_dpid_map[path[0]]]
            dstVPorts = vport_pdpid_map[physical_node_to_dpid_map[path[len(path)-1]]]
            for srcVPort in srcVPorts:
                for dstVPort in dstVPorts:
                    if (srcVPort, dstVPort) not in connected and (dstVPort,srcVPort) not in connected:
                        client.setInternalRouting(tenantId, switchid_pdpid_map[physical_node_to_dpid_map[path[0]]], 'manual', 1)
                        client.connectRoute(tenantId, int(virtual_node_to_dpid_map[dpid].replace(":",""),16), \
                        int(srcVPort), int(dstVPort), translate_path(res_path), 1)
                        print "internal route for virtual switch with dpid:", virtual_node_to_dpid_map[dpid], "between virtual ports: ", srcVPort, dstVPort
                        print "was set during physical path: ", res_path 
                        print ""
                        connected.append((srcVPort,dstVPort))
                        connected.append((dstVPort,srcVPort))
                    #client.setInternalRouting(tenantId, switchid_pdpid_map[physical_node_to_dpid_map[path[0]]], 'manual', 1)
                    #client.connectRoute(tenantId, int(virtual_node_to_dpid_map[dpid].replace(":",""),16), \
                    #int(dstVPort), int(srcVPort), translate_path(res_rev_path), 120)
    print "*****END OF CONSTRUCT BIG SWITCH ROUTES*****"
    client.startNetwork(tenantId)
    print "*****END OF DO CUSTOM TOPO*****"    
    return tenantId
#---------------------------------------------------------------------------------------------------


    def doBigSwitchNetwork(self, controller, routing, subnet, hosts):
        """Create OVX network that is a single big switch"""
        
        client = self.server.client
        # request physical topology
        phyTopo = client.getPhysicalTopology()
    # spawn controller if necessary
        # TODO: do proper string comparison
        if controller['type'] == 'default':
            proto = self.server.ctrlProto
            host = self.server._spawnController()
            port = self.server.ctrlPort
            ctrls = ["%s:%s:%s" % (proto, host, port)]
        elif controller['type'] == 'custom':
            ctrls = controller['ctrls']
        else:
            raise EmbedderException(ERROR_CODE.INVALID_REQ, 'Unsupported controller type')
        # split subnet in netaddress and netmask
        (net_address, net_mask) = subnet.split('/')
        # create virtual network
        tenantId = client.createNetwork(ctrls, net_address, int(net_mask))
        # create virtual switch with all physical dpids
        dpids = [hexToLong(dpid) for dpid in phyTopo['switches']]
        switchId = client.createSwitch(tenantId, dpids)
        # set routing algorithm and number of backups, only for true bigswitches
        if (len(dpids) > 1):
            client.setInternalRouting(tenantId, switchId, routing['algorithm'], routing['backup_num'])
        # create virtual ports and connect hosts
        for host in hosts:
            (vdpid, vport) = client.createPort(tenantId, hexToLong(host['dpid']), host['port'])
            client.connectHost(tenantId, vdpid, vport, host['mac'])
        # Start virtual network
        client.startNetwork(tenantId)

        return tenantId

    def doPhysicalNetwork(self, controller, routing, subnet, hosts, copyDpid = False):
        """Create OVX network that is clone of physical network"""
        
        client = self.server.client
        # request physical topology
        phyTopo = client.getPhysicalTopology()
        # spawn controller if necessary
        if controller['type'] == 'default':
            proto = self.server.ctrlProto
            host = self.server._spawnController()
            port = self.server.ctrlPort
            ctrls = ["%s:%s:%s" % (proto, host, port)]
        elif controller['type'] == 'custom':
            ctrls = controller['ctrls']
        else:
            raise EmbedderException(ERROR_CODE.INVALID_REQ, 'Unsupported controller type')
        # split subnet in netaddress and netmask
        (net_address, net_mask) = subnet.split('/')
        # create virtual network
        tenantId = client.createNetwork(ctrls, net_address, int(net_mask))
        # create virtual switch per physical dpid
        for dpid in phyTopo['switches']:
            if copyDpid:
                client.createSwitch(tenantId, [hexToLong(dpid)], dpid=hexToLong(dpid))
            else:
                client.createSwitch(tenantId, [hexToLong(dpid)])
        # create virtual ports and connect hosts
        for host in hosts:
            (vdpid, vport) = client.createPort(tenantId, hexToLong(host['dpid']), host['port'])
            client.connectHost(tenantId, vdpid, vport, host['mac'])
        # create virtual ports and connect virtual links
        connected = []
        for link in phyTopo['links']:
            if (link['src']['dpid'], link['src']['port']) not in connected:
                srcDpid = hexToLong(link['src']['dpid'])
                # Type conversions needed because OVX JSON output is stringified
                srcPort = int(link['src']['port'])
                (srcVDpid, srcVPort) = client.createPort(tenantId, srcDpid, srcPort)
                 
                dstDpid = hexToLong(link['dst']['dpid'])
                dstPort = int(link['dst']['port'])
                (dstVDpid, dstVPort) = client.createPort(tenantId, dstDpid, dstPort)
        
                src = "%s/%s" % (srcDpid, srcPort)
                dst = "%s/%s" % (dstDpid, dstPort)
        
                path = "%s-%s" % (src, dst)
                client.connectLink(tenantId, srcVDpid, srcVPort, dstVDpid, dstVPort, routing['algorithm'], routing['backup_num'])
                connected.append((link['dst']['dpid'], link['dst']['port']))
      
        # boot network
        client.startNetwork(tenantId)

        return tenantId

    def _exec_createNetwork(self, json_id, params):
        """Handler for automated network creation"""
    #print "HERE------------------------------"
        try:
            p = params.get('network')
            if p == None:
                raise EmbedderException(ERROR_CODE.INVALID_REQ, 'Missing network section')

            tenantId = -1

            networkType = p.get('type')
            if networkType == None:
                raise EmbedderException(ERROR_CODE.INVALID_REQ, 'Missing network type')
            elif networkType == 'bigswitch':
                tenantId = self.doBigSwitchNetwork(p['controller'], p['routing'], p['subnet'], p['hosts'])
            elif networkType == 'physical':
                tenantId = self.doPhysicalNetwork(p['controller'], p['routing'], p['subnet'], p['hosts'], copyDpid=p.get('copy-dpid', False))
#--------------------------------------          
            #if type of network in .json is "custom_topology"
        elif networkType == 'custom_topology':
                tenantId = self.doCustomTopoNetwork(p['controller'], p['routing'], p['subnet'], p['hosts'], p['switches'], p['links'])
#--------------------------------------            
            else:
                raise EmbedderException(ERROR_CODE.INVALID_REQ, 'Unsupported network type')
            response = self._buildResponse(json_id, result={ 'tenantId' : tenantId })
        except OVXException as e:
            if e.rollback:
                client = self.server.client
                client.removeNetwork(e.tenantId)
            err = self._buildError(e.code, e.msg)
            response = self._buildResponse(json_id, error=err)
        except EmbedderException as e:
            log.error(e)
            err = self._buildError(e.code, e.msg)
            response = self._buildResponse(json_id, error=err)
    
        return response

    def do_POST(self):
        """Handle HTTP POST calls"""

        def reply(response):
            response = json.dumps(response) + '\n'
            self.send_response(200, "OK")
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(response))
            self.end_headers()
            self.wfile.write(response)
    
        # Put JSON message in data dict
        l = self.headers.get("Content-Length", "")
        data = ''
        if l == "":
            data = self.rfile.read()
        else:
            data = self.rfile.read(int(l))
        try:
            data = json.loads(data)
        except:
            msg = "Error parsing JSON request"
            log.error(msg)
            err = self._buildError(ERROR_CODE.PARSE_ERROR, msg)
            result = self._buildResponse(None, error=err)
        # Check if JSONRPC 2.0 compliant (correct version and json_id given)
        print "DATA----------------------------------------"
    print data
    json_id = data.get('id', None)
        # Setup method to call
        try:
            methodName = "_exec_" + data.get('method')
            method = getattr(self, methodName)
            log.info(methodName)
        except:
            msg = "Method not found"
            log.info(msg)
            err = self._buildError(ERROR_CODE.METHOD_NOT_FOUND, msg)
            result = self._buildResponse(json_id, error=err)
        # Get method parameters
        params = data.get('params', {})
        # Call method
        result = method(json_id, params)

        reply(result)

class OVXEmbedderServer(HTTPServer):
    def __init__(self, opts):
        HTTPServer.__init__(self, (opts['host'], opts['port']), OVXEmbedderHandler)
        self.client = OVXClient(opts['ovxhost'], opts['ovxport'], opts['ovxuser'], opts['ovxpass'])
        self.ctrlProto = opts['ctrlproto']
        self.ctrlPort = opts['ctrlport']
        self.controllers = []

    def _spawnController(self):
        ctrl = "OVX-%s" % len(self.controllers)
        devnull = open('/dev/null', 'w')
        log.info("Spawning controller VM %s" % ctrl)
        clone_cmd = CLONE_VM % ctrl
        subprocess.call(clone_cmd.split(), stdout=devnull, stderr=devnull)
        start_cmd = START_VM % ctrl
        subprocess.call(start_cmd.split(), stdout=devnull, stderr=devnull)
        get_ip_cmd = GET_IP_VM % ctrl
        while True:
            try:
                ret = subprocess.check_output(get_ip_cmd.split(), stderr=devnull)
            except subprocess.CalledProcessError:
                time.sleep(1)
                continue
            ip = ret
            break
        self.controllers.append(ctrl)
        log.info("Controller %s ready on %s" % (ctrl, ip))
        return ip
    
    def closeControllers(self):
        for controller in self.controllers:
            stop_cmd = STOP_VM % controller
            subprocess.call(stop_cmd.split())
            del_cmd = UNREGISTER_VM % controller
            subprocess.call(del_cmd.split())
    
class OVXEmbedder(threading.Thread):
    """
    OpenVirteX planner JSON RPC 2.0 server
    """
    def __init__(self, opts):
        threading.Thread.__init__(self)
        self.httpd = OVXEmbedderServer(opts)
        self.setDaemon(True)
    
    # Multi-threaded webserver
    def run(self):
        """
        Main function run by thread
        """
        log.info("JSON RPC server starting")
        try:
            self.httpd.serve_forever()
        finally:
            self.httpd.server_close()
            self.httpd.closeControllers()

if __name__ == '__main__':
    parser = ArgumentParser(description="OpenVirteX network embedding tool.")
    parser.add_argument('--host', default='localhost', help='OpenVirteX embedder host (default="localhost")')
    parser.add_argument('--port', default=8000, type=int, help='OpenVirteX embedder port (default=8000)')
    parser.add_argument('--ovxhost', default='localhost', help='host where OpenVirteX is running (default="localhost")')
    parser.add_argument('--ovxport', default=8080, type=int, help='port where OpenVirteX is running (default=8080)')
    parser.add_argument('--ovxuser', default='admin', help='OpenVirteX user (default="admin")')
    parser.add_argument('--ovxpass', default='admin', help='OpenVirteX password (default="admin")')
    parser.add_argument('--ctrlproto', default='tcp', help='default controller protocol (default="tcp")')
    parser.add_argument('--ctrlport', default=10000, type=int, help='default controller port (default=10000)')
    parser.add_argument('--loglevel', default='INFO', help='log level (default="INFO")')
    parser.add_argument('--version', action='version', version='%(prog)s 0.1')
    args = parser.parse_args()
    opts = vars(args)
  
    log.basicConfig(format='%(asctime)s %(message)s', level=getattr(log, opts['loglevel'].upper()))
    embedder = OVXEmbedder(opts)
    embedder.run()
