import hashlib
import json
import sys
from time import time
from textwrap import dedent
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from uuid import uuid4

import requests
from flask import Flask, jsonify, request

class Blockchain:
    def __init__(self):
        self.chain = []
        self.current_transaction = []
        self.last_consensus = 0
        self.new_block(proof =100, previous_hash = '1')
        self.nodes = set()
	#To add a new block to the chain
    def new_block(self, proof, previous_hash = None):
        block = {
            'index' : len(self.chain)+1,
            'timestamp' : time(),
            'transaction' : self.current_transaction,
            'proof' : proof,
            'previous_hash' : previous_hash or self.hash(self.chain[-1])
        }

        self.current_transaction = []
        self.chain.append(block)

        return block
	#To add a new transaction to the list of transactions.
    def new_transaction(self, vote = None, verifier = None):
        self.current_transaction.append({'verifier': verifier, 'vote': vote})

        nodes = self.nodes

        # for node in nodes:
        #     header = {'Content-type': 'application/json'}
        #     response = requests.post(f'http://{node}/tran_broadcast', json={'verifier': verifier, 'vote': vote},headers=header)

        return self.last_block()+1
    # #To broadcast a new transaction to all the nodes in the network so that miners can add this transaction into their block from any node.
    # def tran_broadcast(self, vote = None, verifier = None):
    #
    #     self.current_transaction.append({'verifier': verifier, 'vote': vote})
    #     #nodes = self.nodes
    #
    #     # for node in nodes:
    #     #     header = {'Content-type': 'application/json'}
    #     #     response = requests.post(f'http://{node}/tran_new', json={'verifier': verifier, 'vote': vote},headers=header)
	#To calculate the proof of work and return the proof to miner
    def proof_of_work(self,prev_proof):

        curr_proof = 0
        prev_hash = self.hash(self.chain[-1])
        while self.proof_check(curr_proof,prev_proof,prev_hash) is False:
            curr_proof +=1

        return curr_proof
	#To register a node in the network
    def node_register(self, address):
        url_parsed = urlparse(address)
        self.nodes.add(url_parsed.netloc)
        print(list(self.nodes), file=sys.stderr)
        print(url_parsed, file=sys.stderr)
        # Send the list of nodes in votechain to the voter registration chain
        #for node in self.nodes:
        header = {'Content-type': 'application/json'}
        response = requests.post(f'http://localhost:5000/vote_nodes',json={'node': url_parsed.netloc},headers=header)

	#To validate the chain by checking the previous hash and current proof of work
    def valid_chain(self,chain):

        prev_block = chain[self.last_consensus]
        curr_index = self.last_consensus+1
        count = 0
        #print(f'curr index is {curr_index}', file=sys.stderr)
        while curr_index < len(chain):
            curr_block = chain[curr_index]

            if(curr_block['previous_hash']) != self.hash(prev_block):
                #print(f'previous hash mismatch {prev_block}', file=sys.stderr)
                return False

            if not (self.proof_check(curr_block['proof'],prev_block['proof'],curr_block['previous_hash'])):
                #print(f'proof error {prev_block}', file=sys.stderr)
                return False

            prev_block = curr_block
            curr_index += 1
            count += 1
        #print(f'count is{count}', file=sys.stderr)
        return True
	#Resolve conflict within nodes in a network by comparing length of their chain.
    def consensus_resolver(self):

        neighbours = self.nodes
        max_length = len(self.chain)
        new_chain = None

        self.all_translist = []
        self.all_tranlist_neighbour = []
        self.translist_retain = []

        for node in neighbours:
            response = requests.get(f'http://{node}/view_chain')

            if response.status_code == 200:
                length = response.json()['length of chain']
                chain = response.json()['chain']

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

                    #Check which transactions need to be retained

                    i = 0
                    while i < len(self.chain):
                        self.all_translist.extend(self.chain[i]['transaction'])
                        i += 1
                    self.all_translist.extend(self.current_transaction)
                    j = 0
                    while j <len(chain):
                        self.all_tranlist_neighbour.extend(chain[j]['transaction'])
                        j += 1

                    for k in self.all_translist:
                        if k not in self.all_tranlist_neighbour:
                            self.translist_retain.append(k)


                    self.current_transaction = []

        if new_chain:
            self.chain = new_chain
            self.current_transaction = self.translist_retain
            self.last_consensus = new_chain[-1]['index']

            return True
        self.current_transaction = self.translist_retain
        return False
	#Count the total number of votes
    def vote_count(self):
        catcount = 0
        dogcount = 0

        i = 0
        while i < len(self.chain):
            tranlist = self.chain[i]['transaction']
            j = 0
            while j < len(tranlist):
                if (tranlist[j]['vote']=='cat'):
                    catcount += 1
                elif (tranlist[j]['vote'] == 'dog'):
                    dogcount +=1
                else:
                    pass
                j += 1
            i += 1
        result = {
            'Votes for Dog': f'{dogcount}',
            'Votes for Cat': f'{catcount}'}
        return result
	#Calculate the proof of work
    @staticmethod
    def proof_check(curr_proof,prev_proof,prev_hash):
        guessing = f'{curr_proof}{prev_proof}{prev_hash}'.encode()
        guessed_hash = hashlib.sha256(guessing).hexdigest()

        return guessed_hash[:4] == "0000"
	#Generate hash for previous block.
    @staticmethod
    def hash(block):
        sorted_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(sorted_block).hexdigest()

    def last_block(self):
        return self.chain[-1]['index']



app = Flask(__name__)
node_identifier = str(uuid4()).replace('-', '')

blockchain_obj = Blockchain()

#To mine a new block for the chain
@app.route('/mine', methods=['GET'])
def mine():
    prev_block = blockchain_obj.chain[-1]
    prev_proof = prev_block['proof']

    current_proof = blockchain_obj.proof_of_work(prev_proof)

    #blockchain_obj.new_transaction(verifier= node_identifier)

    prev_block_hash = blockchain_obj.hash(prev_block)
    new_block = blockchain_obj.new_block(current_proof, prev_block_hash)

    result = {
        'Response' : 'New Block has been added',
        'index of the newly added block' : new_block['index'],
        'Transaction' : new_block['transaction'],
        'Calculated Proof' : new_block['proof'],
        'Previous hash' : new_block['previous_hash']
    }
    blockchain_obj.current_transaction = []
    return jsonify(result),200

#To add a new transaction to the list of transactions
@app.route('/tran_new', methods=['POST'])
def tran_new():
    received_val = request.get_json()

    required_key = ['verifier', 'vote']
    if not all(k in received_val for k in required_key):
        print(received_val.text,file=sys.stderr)
        return 'Some Values for this voting transaction are missing. Please enter all values!', 400


    index = blockchain_obj.new_transaction(vote = received_val['vote'],verifier = received_val['verifier'])
    result = f'Voting Transaction will be added to block with index# {index}'
    return jsonify(result),201

#Broadcast the list of pending transactions to all nodes in network
@app.route('/tran_broadcast', methods=['POST'])
def tran_broad():
    received_val = request.get_json()
    required_key = ['verifier', 'vote']
    if not all(k in received_val for k in required_key):
        print(received_val.text, file=sys.stderr)
        return 'Some Values for this voting transaction are missing. Please enter all values!', 400
    blockchain_obj.tran_broadcast(vote=received_val['vote'],verifier=received_val['verifier'])

#View the chain
@app.route('/view_chain', methods=['GET'])
def view_chain():
    result = {
        'chain' : blockchain_obj.chain,
        'length of chain' : len(blockchain_obj.chain)
    }
    return jsonify(result), 200

#get current list of nodes in the network
@app.route('/node/get', methods=['GET'])
def get_node():
    result = {
        'Nodes in System' : list(blockchain_obj.nodes),
        'Count of Nodes' : len(blockchain_obj.nodes)
    }
    return jsonify(result)
#Register a new node into the blockchain network
@app.route('/node/register', methods = ['POST'])
def register_node():
    received_val = request.get_json()
    nodes = received_val.get('nodes')

    if nodes is None:
        return "Error: Please supply a valid node", 400

    for node in nodes:
        print(node, file=sys.stderr)
        blockchain_obj.node_register(node)

    response = {"Message" : "New nodes have been added", "Total Nodes in System" : list(blockchain_obj.nodes)}



    return jsonify(response), 201


#Resolve consensus within nodes in the blockchain network
@app.route('/node/resolve', methods = ['GET'])
def resolve():
    replaced = blockchain_obj.consensus_resolver()

    if replaced:
        response = {"Message" : "Our Chain was replaced", "New_Chain" : blockchain_obj.chain}
    else:
        response = {"Message": "Our Chain is Latest", "New_Chain": blockchain_obj.chain}

    return jsonify(response), 200

#Get the final vote_count
@app.route('/count_vote', methods=['GET'])
def vote_count():
    result = blockchain_obj.vote_count()

    return jsonify(result), 200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5001, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port, debug = True, threaded = True)




