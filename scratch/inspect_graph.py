import sys
sys.path.append("/home/diaz/Documents/golekbengkel-backend-1")
from config import GRAPH_PATH
from core.graph_loader import get_graph

def inspect_graph():
    graph = get_graph(GRAPH_PATH)
    print(f"Nodes: {graph.number_of_nodes()}, Edges: {graph.number_of_edges()}")
    
    # Check a few nodes
    node_iter = iter(graph.nodes(data=True))
    print("Sample node data:")
    for i in range(2):
        print(next(node_iter))
        
    # Check a few edges
    edge_iter = iter(graph.edges(data=True))
    print("\nSample edge data:")
    for i in range(5):
        print(next(edge_iter))

if __name__ == "__main__":
    inspect_graph()
