import random as rnd
import networkx as nx
from graphviz import Digraph
import numpy as np


def measure_node_distance(firm_pos,path_pos):
    """Support function to measure distance between product and firm

    Args:
        node_pos (list): multi-dimensional position of the firm
        path_pos (list): multi-dimensional position of the product

    Returns:
        float: Euclidean distance between firm and product
    """
    return np.sqrt(np.sum([(firm_pos[i] - path_pos[i])**2 for i in range(len(firm_pos))]))

def create_graph(graph_num,firms_per_label, number_products, connect_vector, radius, seed):
    """Creates a single SCN graph

    Args:
        graph_num (int): identifying number of the graph to generate
        firms_per_label (list): number of firms (int) associated with each label
        number_products (int): number of products that should be generated
        connect_vector (list): number of firms at each label that can at most be used in the production of one product
        radius (float): radius within which connection occurs
        seed (int): random seed

    Returns:
        dictionary: NetworkX-generated graph dictionary
        string: pdf file name
    """
    rnd.seed(seed)
    labels = len(firms_per_label)

    # Create auxiliary graph with nodes
    G = nx.DiGraph()
    label_nodes = {}
    position = {}
    node = 0
    for label in range(labels):
        sup = []
        for i in range(firms_per_label[label]):
            G.add_node(node)
            G.nodes[node]["label"] = label
            sup.append(node)
            position[node] = [rnd.random()*np.sqrt(np.sum(firms_per_label)) for _ in range(2)]
            node += 1
        label_nodes[label] = sup


    # Create products and connect to nodes based on Euclidean distances
    # Throw out products with only one node
    product_list = []
    for _ in range(number_products):
        new_product = []
        product_pos = [rnd.random()*np.sqrt(np.sum(firms_per_label)) for _ in range(2)]
        for label in range(labels):
            node_distances = {n:measure_node_distance(position[n],product_pos) for n in label_nodes[label]}
            nodes_in_range = [key for (key,value) in node_distances.items() if value < radius]
            if len(nodes_in_range) > 0:
                chosen_nodes = rnd.sample(nodes_in_range,min(len(nodes_in_range),connect_vector[label]))
                new_product += chosen_nodes
        if (not new_product in product_list) and len(new_product) > 1:
            product_list.append(new_product)
            G.add_node(node)
            for chosen_node in new_product:
                G.add_edge(chosen_node,node)
            node += 1

    # Delete any node that does not contribute to a product
    for n in range(node):
        if len(list(G.successors(n))) == 0 and len(list(G.predecessors(n))) == 0:
            G.remove_node(n)

    # Relabel nodes to start from zero and go consecutively (i.e. if i->j, then i<j)
    mapping = {}
    new_node = 0
    for node in G.nodes:
        mapping[node] = new_node
        new_node += 1
    G = nx.relabel_nodes(G, mapping)

    # Create product-list from auxiliary graph
    product_list = []
    node_set = set()
    for node in G.nodes:
        if len(list(G.predecessors(node))) > 0:
            product = {label:[] for label in range(labels)}
            firms_to_add = G.predecessors(node)
            for firm in firms_to_add:
                product[G.nodes[firm]["label"]].append(firm)
            product_list.append(product)
            node_set.update(list(G.predecessors(node)))

    # Create original graph based on product-list
    OG = nx.DiGraph()
    OG.add_nodes_from(node_set)
    for product in product_list:
        active_labels = [key for key in product.keys() if len(product[key]) > 0]
        for i in range(len(active_labels)-1):
            for firm1 in product[active_labels[i]]:
                for firm2 in product[active_labels[i+1]]:
                    OG.add_edge(firm1,firm2)
    graph_dict = nx.node_link_data(OG)

    # Print SCN
    dot = Digraph(name='graph_'+str(graph_num),format='pdf')
    dot.attr(rankdir='TB',size='8',label="SCN",labelloc="top")
    dot.attr('node', shape='circle')
    for node in OG.nodes:
        node_label = str(node)
        color = "lightblue"
        dot.node(str(node), label = node_label,color="black", fillcolor=color, style="filled")
    for edge in OG.edges:
        dot.edge(str(edge[0]),str(edge[1]))
    dot.attr(fontsize='14')
    pdf = dot.render(filename = '/static/graph_' + str(graph_num),view=False,format='pdf')

    return graph_dict, pdf




def create_multiple_graphs(number_graphs,number_firms,number_products,number_labels,radius,connect_vector,seed):
    """Creates multiple SCN graphs

    Args:
        number_graphs (int): number of graphs to be generated
        number_firms (int): maximum number of firms in each graph
        number_products (int): maximum number of products to be generated
        number_labels (int): number of labels to which firms are assigned
        radius (float): radius within which connection occurs
        seed (int): random seed

    Returns:
        dictionary: dictionary of all graphs, containing a NetworkX-generated dictionary for each, plus generation information
        list: list of pdf file names
    """
    # Compute remaining parameters
    firms_per_label = [round(number_firms/number_labels)]*number_labels
    if connect_vector is None:
        connect_vector = [1]*number_labels
    rnd.seed(seed)
    seeds = [rnd.randint(1,100000) for _ in range(number_graphs)]

    # Create graphs
    pdfs = []
    full_dict = {   "firms_per_label": firms_per_label,
                    "number_products": number_products,
                    "radius": radius,
                    "seed": seed,
                    "graphs": []}
    for i in range(number_graphs):
        graph_dict, pdf = create_graph(i,firms_per_label, number_products, connect_vector, radius, seeds[i])
        full_dict['graphs'].append(graph_dict)
        pdfs.append(pdf)
    
    return full_dict, pdfs

def display_results(number_graphs=2,number_firms=10,number_products=50,number_labels=4,radius=1,connect_vector=None,seed=9453):
    # TODO: Add parameter checks

    graph_dict, pdfs = create_multiple_graphs(number_graphs,number_firms,number_products,number_labels,radius,connect_vector,seed)

    # TODO: display first pdf on page

    # TODO: zip pdfs and create download button

    # TODO: create download button for graph_dict (as json)


from flask import Flask, render_template,redirect
from flask import request,send_file
import zipfile
import json
import os
import shutil
import atexit
import traceback

def zip_files(files, zip_path):
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file_path in files:
            zipf.write(file_path)



app = Flask(__name__)

### The Initial Page
@app.route('/')
def init():
    #delete_static_folder() ### delete previous things on Static Folder
    return render_template('index.html')

### to Reset
@app.route("/initial")
def initial():
    #delete_static_folder() ### delete previous things on Static Folder
    return redirect("/")

### Get Input values
@app.route('/get_values', methods=['GET', 'POST'])
def get_values():
    if request.method == 'POST':
        # Get the values of the inputs
        number_graphs = int(request.form['number_graphs'])
        number_firms = int(request.form['number_firms'])
        number_products = int(request.form['number_products'])
        number_labels = int(request.form['number_labels'])
        seed = int(request.form['seed'])
        connect_vector = []
        for i in range(number_labels):
            input_value = int(request.form["number_labels" + str(i)])
            connect_vector.append(input_value)



        #### Adjustments and checkings on the inputs:
        err_mes = "" ### final error message to show, if there is any
        radius = request.form['radius']
        if len(radius)==0: ### default radius
            radius = 1/np.sqrt(number_firms)
        else:
            radius = float(radius)

        if radius == 0:
            err_mes = err_mes + "Radius must be Positive" + "\n"

        if number_labels > number_firms:
            err_mes = err_mes + "Number of Labels can not be larger than Number of Firms" + "\n"

        for idx, x in enumerate(connect_vector):
            if x > number_firms:
                err_mes = err_mes + "Maximum Number of Firms with Label" + str(idx) + " can not be larger than Number of Firms" + "\n"

        try:
            #### Construct the Graphs and PDFs
            graph_dict, pdfs = create_multiple_graphs(number_graphs, number_firms,
                                                      number_products, number_labels, radius, connect_vector,seed)
            ### Convert the dictionary to a json file
            with open('/static/graph_dict.json', 'w') as json_file:
                json.dump(graph_dict, json_file)
            ### zip all data
            files = pdfs + ['/static/graph_dict.json']
            zip_path = '/static/data.zip'
            zip_files(files, zip_path)

            ## Show the first Graph
            pdf_url = '/static/graph_0.pdf'
            massage = "Supply chains have been created for the following specification: "\
                      + '\n' + " Number of Graphs: " + str(number_graphs) +\
                      '\n' + 'Number of Firms: ' + str(number_firms)\
                      + '\n' + 'Number of Products: ' + str(number_products)\
                      + '\n' + 'Radius: ' + str(radius)\
                      + '\n' + "Number of Labels: " + str(number_labels)\
                      + '\n' + "And Following Vector for Maximum Number of Firms with Labels k: " + str(connect_vector)\
                      + "\n" + 'Here below you can find the First Graph!'
            massage = massage.split('\n')
            err_mes = err_mes.split('\n')

            if err_mes==['']:
                return render_template('index.html', massage=massage, pdf_url=pdf_url)
            else:
                return render_template('index.html', err_mes=err_mes)

        except Exception as e:
            py_err_mes = e
            err_mes = "Errors on Input Format:" + err_mes + "\n" + "Python Errors: " + str(traceback.format_exc())
            err_mes = err_mes.split('\n')

            return render_template('index.html', err_mes=err_mes)
    else:
        return render_template('index.html')


#### Path to download the data
@app.route('/download')
def download_file():
    file_path = '/static/data.zip'
    return send_file(file_path, as_attachment=True)


##### Delete everything on static folder after exit.
def delete_static_folder():
    folder = os.path.join(app.static_folder)
    for the_file in os.listdir(folder):
        file_path = os.path.join(folder, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(e)

### delete previous things on Static Folder after all!
atexit.register(delete_static_folder)


app.secret_key = 'some key that you will never guess'

if __name__ == "__main__":
    app.run(debug=True)
    # Run the app on localhost port 5000
    #app.run('127.0.0.1', 5000, debug = True)
