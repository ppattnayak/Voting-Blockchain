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
        self.vote_nodes = set()

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
	#Append a new transaction to list of transactions
    def new_transaction(self, name = None, id = None, verifier = None, voted = None):

        self.current_transaction.append({'Name': name, 'Id': id, 'Verifier' : verifier, 'Status': voted})

        return self.last_block()+1
	#Proof of Work to calculate previous hash and give current hash to the miner
    def proof_of_work(self,prev_proof):

        curr_proof = 0
        prev_hash = self.hash(self.chain[-1])
        while self.proof_check(curr_proof,prev_proof,prev_hash) is False:
            curr_proof +=1

        return curr_proof
	#To register nodes in the blockchain distributed system. Each node must be made aware of other nodes in the system.
    def node_register(self, address):
        url_parsed = urlparse(address)
        self.nodes.add(url_parsed.netloc)

    # To keep list of nodes in the votechain distributed system. This is used to broadcast new transactions to the votechain
    # as and when voters are verified. Currently, we don't have a proper broadcast system. Once we have that in place,
    # we can use that to broadcasst new voting transactions. And get rid if the below approach.
    def votenode_register(self, address):
        print(address, file=sys.stderr)

        #url_parsed = urlparse(address)
        self.vote_nodes.add(address)


	#To check if the current chain is valid and thus validate the proof of work
    def valid_chain(self,chain):

        prev_block = chain[self.last_consensus]
		#Current index to check for chain's validity from last known consensus.
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
	#Consensus resolver to check the chain with other nodes and retain/discard current chain based on length of chain.
    def consensus_resolver(self):

        neighbours = self.nodes
        max_length = len(self.chain)
        new_chain = None


        for node in neighbours:
            response = requests.get(f'http://{node}/view_chain')

            if response.status_code == 200:
                length = response.json()['length of chain']
                chain = response.json()['chain']

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            self.last_consensus = new_chain[-1]['index']
            return True
        return False
	#Vote function to validate the user's right to vote and register their vote on the voting chain.
    def vote(self, name, id, vote):
        count = 0
        verifier = None
        i=0
        while i<len(self.chain):
            tranlist = self.chain[i]['transaction']
            j=0
            while j<len(tranlist):
                if (self.proof_check(name, id, tranlist[j]['Verifier'])):
                    count += 1
                    verifier = tranlist[j]['Verifier']
                    print(f'{name} {id} {verifier}',file=sys.stderr)
                j+=1
            i+=1

        # for block in self.chain:
        #     for key in block.items():
        #         for eachtran in tran:
        #             if not(self.proof_check(name, id, eachtran['Verifier'])):
        #                 count+=1
        #                 verifier = eachtran['Verifier']


        if count==1:
            for node in self.vote_nodes:
                header = {'Content-type': 'application/json'}
                response = requests.post(f'http://{node}/tran_new', json={'verifier': verifier, 'vote': vote},headers=header)
            # header = {'Content-type': 'application/json'}
            # if node == 'node1':
            #     response = requests.post('http://34.212.33.143:5001/tran_new', json={'verifier': verifier, 'vote': vote},headers=header)
            # elif node == 'node2':
            #     response = requests.post('http://34.212.33.143:5002/tran_new', json={'verifier': verifier, 'vote': vote},headers=header)
            # elif node == 'node3':
            #     response = requests.post('http://34.212.33.143:5003/tran_new', json={'verifier': verifier, 'vote': vote},headers=header)

            self.new_transaction(name,id,verifier,'voted')
            jresponse = requests.get('http://localhost:5000/mine')
            print(f"calling new tran on votechain", file=sys.stderr)
        # elif count == 2:
        #     response = {"Message": "Already Voted"}
        # else:
        #     response = {"Message": "You are not registered to vote"}

        return count




	#to calculate the proof based on a hashing pattern match
    @staticmethod
    def proof_check(curr_proof,prev_proof,prev_hash):
        guessing = f'{curr_proof}{prev_proof}{prev_hash}'.encode()
        guessed_hash = hashlib.sha256(guessing).hexdigest()

        return guessed_hash[:4] == "0000"
	#calculates the hash of a block by passing the sorted block to the function
    @staticmethod
    def hash(block):
        sorted_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(sorted_block).hexdigest()
	#returns the last index of chain
    def last_block(self):
        return self.chain[-1]['index']



app = Flask(__name__)
node_identifier = str(uuid4()).replace('-', '')

blockchain_obj = Blockchain()

#Endpoints to map miner's request to calculate the proof and add the block.
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
        'Voting Transaction' : new_block['transaction'],
        'Calculated Proof' : new_block['proof'],
        'Previous hash' : new_block['previous_hash']
    }

    return jsonify(result),200

#Endpoint to add a new transaction to the list of transactions
@app.route('/tran_new', methods=['POST'])
def tran_new():
    received_val = request.get_json()

    required_key = ['name', 'id']
    if not all(k in received_val for k in required_key):
        return 'Some Values for this voting transaction are missing. Please enter all values!', 400
    curr_identifier = 0
    #prev_hash = blockchain_obj.hash(self.chain[-1])
    while blockchain_obj.proof_check(received_val['name'], received_val['id'], curr_identifier) is False:
        curr_identifier += 1

    index = blockchain_obj.new_transaction(name = received_val['name'],id = received_val['id'],verifier = curr_identifier)
    result = {"Message":f'Voting Transaction will be added to block with index# {index}'}
    return jsonify(result),201

#Voting endpoint1 to send the votes to node 1 of votechain
@app.route('/vote', methods=['POST'])
def vote():
    received_val = request.get_json()
    required_key = ['name', 'id', 'vote']

    if not all(k in received_val for k in required_key):
        return 'Some Values for this voting transaction are missing. Please enter all values!', 400
    # curr_identifier = 0
    # #prev_hash = blockchain_obj.hash(self.chain[-1])
    # while blockchain_obj.proof_check(received_val['name'], received_val['id'], curr_identifier) is False:
    #     curr_identifier += 1
    #
    # index = blockchain_obj.new_transaction(name = received_val['name'],id = received_val['id'],verifier = curr_identifier)
    # result = f'Voting Transaction will be added to block with index# {index}'
    # return jsonify(result),201
    count = blockchain_obj.vote(received_val['name'],received_val['id'],received_val['vote'])
    if count ==1:
        response = {"Message": "Your vote was registered"}
    elif count ==2:
        response = {"Message": "Already Voted"}
    elif count ==0:
        response = {"Message": "You are not registered to Vote"}
    else:
        response = {"Message": "Something went wrong. Please try again"}

    return jsonify(response)

#Voting endpoint2 to send the votes to node 2 of votechain
# @app.route('/vote2', methods=['POST'])
# def vote2():
#     received_val = request.get_json()
#     required_key = ['name', 'id', 'vote']
#     if not all(k in received_val for k in required_key):
#         return 'Some Values for this voting transaction are missing. Please enter all values!', 400
#     # curr_identifier = 0
#     # #prev_hash = blockchain_obj.hash(self.chain[-1])
#     # while blockchain_obj.proof_check(received_val['name'], received_val['id'], curr_identifier) is False:
#     #     curr_identifier += 1
#     #
#     # index = blockchain_obj.new_transaction(name = received_val['name'],id = received_val['id'],verifier = curr_identifier)
#     # result = f'Voting Transaction will be added to block with index# {index}'
#     # return jsonify(result),201
#     count = blockchain_obj.vote(received_val['name'],received_val['id'],received_val['vote'],'node2')
#     if count ==1:
#         response = {"Message": "Your vote was registered"}
#     elif count ==2:
#         response = {"Message": "Already Voted"}
#     elif count ==0:
#         response = {"Message": "You are not registered to Vote"}
#     else:
#         response = {"Message": "Something went wrong. Please try again"}
#
#     return jsonify(response)
#
# #Voting endpoint3 to send the votes to node 3 of votechain
# @app.route('/vote3', methods=['POST'])
# def vote3():
#     received_val = request.get_json()
#     required_key = ['name', 'id', 'vote']
#     if not all(k in received_val for k in required_key):
#         return 'Some Values for this voting transaction are missing. Please enter all values!', 400
#     # curr_identifier = 0
#     # #prev_hash = blockchain_obj.hash(self.chain[-1])
#     # while blockchain_obj.proof_check(received_val['name'], received_val['id'], curr_identifier) is False:
#     #     curr_identifier += 1
#     #
#     # index = blockchain_obj.new_transaction(name = received_val['name'],id = received_val['id'],verifier = curr_identifier)
#     # result = f'Voting Transaction will be added to block with index# {index}'
#     # return jsonify(result),201
#     count = blockchain_obj.vote(received_val['name'],received_val['id'],received_val['vote'],'node3')
#
#     if count ==1:
#         response = {"Message": "Your vote was registered"}
#     elif count ==2:
#         response = {"Message": "Already Voted"}
#     elif count ==3:
#         response = {"Message": "You are not registered to Vote"}
#     else:
#         response = {"Message": "Something went wrong. Please try again"}
#
#     return jsonify(response)

#to View the chain
@app.route('/view_chain', methods=['GET'])
def view_chain():
    result = {
        'chain' : blockchain_obj.chain,
        'length of chain' : len(blockchain_obj.chain)
    }
    return jsonify(result), 200

#To get list of nodes in the blockchain network.
@app.route('/getvnode', methods=['GET'])
def get_node():
    result = {
        'Nodes in System' : list(blockchain_obj.vote_nodes),
        'Count of Nodes' : len(blockchain_obj.vote_nodes)
    }
    return jsonify(result)

#To register a new node in the network
@app.route('/node/register', methods = ['POST'])
def register_node():
    received_val = request.get_json()
    nodes = received_val.get('nodes')

    if nodes is None:
        return "Error: Please supply a valid node", 400

    for node in nodes:
        blockchain_obj.node_register(node)

    response = {"Message" : "New nodes have been added", "Total Nodes in System" : list(blockchain_obj.nodes)}

    return jsonify(response), 201

#get list of nodes in the voting chain
@app.route('/vote_nodes', methods = ['POST'])
def vote_nodes():
    received_val = request.get_json()
    vote_nodes = received_val.get('node')
    print(vote_nodes, file=sys.stderr)
    if vote_nodes is None:
        return "Error: Please supply a valid voting node", 400

    else:
        blockchain_obj.votenode_register(vote_nodes)
        print(vote_nodes,file=sys.stderr)

    response = {"Message" : "Voting nodes have been added", "Total Voting Nodes in the second chain: " : list(blockchain_obj.vote_nodes)}

    return jsonify(response), 201
#To run a consensus resolving mechanism
@app.route('/node/resolve', methods = ['GET'])
def resolve():
    replaced = blockchain_obj.consensus_resolver()

    if replaced:
        response = {"Message" : "Our Chain was replaced", "New_Chain" : blockchain_obj.chain}
    else:
        response = {"Message": "Our Chain is Latest", "New_Chain": blockchain_obj.chain}

    return jsonify(response), 200



if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port, threaded=True, debug=True)
