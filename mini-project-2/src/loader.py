import json
import os
from .model import Link, Node, Stream, Route

## 没有加载domain，没有记录link的destinationPort
def load_topology(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    topo = data['topology']
    nodes = {}
    for sw in topo['switches']:
        nodes[sw['id']] = Node(sw['id'], sw['ports'])
    for es in topo['end_systems']:
        nodes[es['id']] = Node(es['id'], 1)
        
    links = {}
    for l in topo['links']:
        link = Link(l['id'], l['source'], l['destination'], l['bandwidth_mbps'], l['delay'])
        links[l['id']] = link
        if l['source'] in nodes:
            nodes[l['source']].outgoing_links[l['sourcePort']] = link
            
    return nodes, links

def load_streams(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    streams = []
    for s in data['streams']:
        dests = [d['id'] for d in s['destinations']]
        deadline = s['destinations'][0]['deadline']
        streams.append(Stream(s['id'], s['source'], dests, s['size'], s['period'], s['PCP'], deadline))
    return streams

## 潜规则: paths的list只有一个元素
def load_routes(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    routes = {}
    for r in data['routes']:
        routes[r['flow_id']] = Route(r['flow_id'], r['paths'][0])
    return routes
