#!/usr/bin/python
# coding: utf-8

# Contains functionality for further decompiling an EO AI script
# from its disassembly into a more easily readable form
#
# when calling this from outside, make sure to call set_game_specific_values()
# with the appropriate game code first
#
# written by TheOnlyOne (@modest_ralts)

import argparse
import copy
from sys import stderr
from itertools import compress

from unpack_ai import *
import eo_value_lookup
from eo_value_lookup import game_codes

def eprint(s):
  stderr.write(s + "\n")

def compose(f, g):
  return lambda x : f(g(x))

def parseArguments():
  # Create argument parser
  parser = argparse.ArgumentParser(description="Decompiles an Etrian Odyssey AI file (.bf, or something with the FLW0 tag.)")

  # Positional mandatory arguments
  parser.add_argument("game", choices=game_codes, help="which game the data is from")
  parser.add_argument("input_file", help="name of the file containing the raw flw0 data")
  parser.add_argument("output_file", help="name of the file in which to place the output") 

  # Optional arguments
  parser.add_argument("--show_output", action="store_true", help="output will be printed to console in addition to being saved to the output_file")
  parser.add_argument("--hide_alerts", action="store_true", help="warnings will not be printed to stderr if unexpected values are encountered")
  parser.add_argument("--fully_optimize", action="store_true", help="all optimization passes will be performed on the code; specific optimization flags will be ignored")
  parser.add_argument("--flatten_conditionals", action="store_true", help="(if t1 else if t2 else f) will be converted to (if t1 elif t2 else f) when permissable to reduce the nesting depth and resulting indentation of code")
  parser.add_argument("--flatten_elses", action="store_true", help="(if t return else f ) will be converted to (if t return f) when permissable to reduce the nesting depth and resulting indentation of code")
  parser.add_argument("--constant_folding", action="store_true", help="any arithmetic containing only constants will be replaced with the value of that expression")
  parser.add_argument("--simplify_conditions", action="store_true", help="boolean conditions will be simplified when it is permissable; see docs/ai_notes.txt for some warnings about this flag")
  parser.add_argument("--handwritten", action="store_true", help="use this for handwritten scripts if they don't seem to decompile well without it; see docs/ai_notes.txt for more details")

  # Print version
  parser.add_argument("--version", action="version", version='%(prog)s - Version 1.0')

  # Parse arguments
  args = parser.parse_args()

  return args

show_alerts = True

# add to the list of instruction names
operation_names = instruction_names
operation_names[0x23] = "FUNC" # a COMM with a return value
operation_names[0x24] = "SEND" # a COMM without a return value
operation_names[0x25] = "COND" # a conditional jump to one of two branches

# maps opcodes to the number of pushes and pops they do
# as a tuple (push, pop)
pushes_and_pops = {
  0x00 : (1, 0), # PUSHI
  0x01 : (1, 0), # PUSHF
  0x02 : (1, 0), # PUSHIX
  0x03 : (1, 0), # PUSHIF
  0x04 : (1, 0), # PUSHREG
  0x05 : (0, 1), # POPIX
  0x06 : (0, 1), # POPFX
  0x07 : (0, 0), # PROC
  0x09 : (0, 0), # END
  0x0C : (0, 0), # RUN
  0x0D : (0, 0), # GOTO
  0x0E : (1, 2), # ADD
  0x0F : (1, 2), # SUB
  0x10 : (1, 2), # MUL
  0x11 : (1, 2), # DIV
  0x12 : (1, 1), # MINUS
  0x13 : (1, 1), # NOT
  0x14 : (1, 2), # OR
  0x15 : (1, 2), # AND
  0x16 : (1, 2), # EQ
  0x17 : (1, 2), # NEQ
  0x18 : (1, 2), # LT
  0x19 : (1, 2), # GT
  0x1A : (1, 2), # LTE
  0x1B : (1, 2), # GTE
  0x1C : (0, 1), # IF
  0x1D : (1, 0), # PUSHIS
  0x1E : (1, 0), # PUSHLIX
  0x1F : (1, 0), # PUSHLFX
  0x20 : (0, 1), # POPLIX
  0x21 : (0, 1), # POPLFX
  0x22 : (1, 0), # PUSHSTR
  0x25 : (0, 1), # COND
}

# give names to the binary expressions, from operation opcodes
binop_names = {
  0x0E : "add",
  0x0F : "sub",
  0x10 : "mul",
  0x11 : "div",
  0x14 : "or",
  0x15 : "and",
  0x16 : "eq",
  0x17 : "neq",
  0x18 : "lt",
  0x19 : "gt",
  0x1A : "lte",
  0x1B : "gte",
}

# give names to the unary expressions, from operation opcodes
monop_names = {
  0x12 : "neg",
  0x13 : "bitnot",
}

# list of operations that push a literal to the stack
lit_ops = [0x00, 0x01, 0x02, 0x03, 0x1D]
litop_names = dict.fromkeys(lit_ops, "lit")

# list of operations that do a variable lookup
var_ops = [0x1E, 0x1F]
varop_names = dict.fromkeys(var_ops, "var")

# list of operations that do a variable assignment
assn_ops = [0x20, 0x21]
assnop_names = dict.fromkeys(assn_ops, "assign")

# symbols associated with binary expression tags
bin_symbols = {
  "add" : "+",
  "sub" : "-",
  "mul" : "*",
  "div" : "/",
  "or" : "|",
  "and" : "&",
  "eq" : "==",
  "neq" : "!=",
  "lt" : "<",
  "gt" : ">",
  "lte" : "<=",
  "gte" : ">=",
}

# symbols associated with unary expression tags
mon_symbols = {
  "neg" : "-",
  "bitnot" : "~",
  "boolnot" : "!",
}

native_functions = {}

# Modifies game specific maps
def set_game_specific_values(game):
  global native_functions

  native_functions = eo_value_lookup.native_functions[game]

# an operation is an opcode and a variable number of arguments
class Operation():

  # display an operation
  def display(self):
    output = [ operation_names[self.opcode] ]
    if self.args:
      output.append( str(self.args) )
    else:
      output.append( "" )
    output.append( "(+" + str(self.pushes) + " -" + str(self.pops) + ")" )
    return "\t".join(output)

  # create the operation from an opcode and a list of arguments
  def __init__(self, opcode, args):
    self.opcode = opcode
    self.args = args
    self.pushes = None
    self.pops = None

    # get the number of pushes and pops
    if self.opcode in [0x23, 0x24]:   # FUNC or SEND
      self.pushes = 1 if self.opcode == 0x23 else 0
      # pushes might remain None if we do not know it
      if self.args[0] in native_functions:
        self.pops = native_functions[ self.args[0] ].num_params
    elif self.opcode == 0x0B:   # CALL
      # we can't know anything about a call from the start
      pass
    else:
      self.pushes, self.pops = pushes_and_pops[self.opcode]

  __str__ = __repr__ = display

# stores the information about a procedure in the script
class Procedure_Info():

  # display a procedure header
  def display(self):
    output = [ self.name + " (Block " + str(self.block_num) + ")"]
    output.append( "(+" + str(self.pushes) + " -" + str(self.pops) + ")" )
    return "\t".join(output)
  
  def __init__(self, block_num, name):
    self.block_num = block_num
    self.name = name
    self.pushes = None
    self.pops = None

  __str__ = __repr__ = display

# collection of blocks making up a loop
class Control_Loop():

  def __init__(self, entry_block, continue_block, break_block, other_blocks):
    self.other_blocks = other_blocks
    self.entry_block = entry_block
    self.continue_block = continue_block
    self.break_block = break_block
    self.all_blocks = other_blocks.union(set([entry_block, continue_block, break_block]))

# graph functionality for handling graphs with directed cycles
class Control_Flow_Graph():
  
  # build the graph as an adjacency list, in both directions
  # storing the full edge set as well
  def build_graph(self, tree):
    # vertices are the used block indices
    self.vertices = set( compress(range(len(tree.block_nodes)), tree.block_used) )
    # sources are the starts of procedures
    self.sources = set(p.block_num for p in tree.procedure_info)
    # sinks are the special_gotos and returns
    # returns will be filled in below
    self.sinks = set(tree.special_gotos)
    # start with empty adjacency lists 
    self.succs = dict( (v, set([])) for v in self.vertices )
    self.preds = dict( (v, set([])) for v in self.vertices )
    self.edges = set([])
    # and fill them in using the operations in the blocks
    for tail in self.vertices:
      block = tree.block_nodes[tail]
      # by original construction, jumps only occur at the end of blocks,
      # and no blocks are empty
      last_stmt = tree.inner_nodes[ block.children[-1] ]
      heads = []
      # goto and if branch to specific blocks
      if last_stmt.tag in ["goto", "if"]:
        heads = last_stmt.vals
      # returns are sinks
      elif last_stmt.tag == "return":
        self.sinks.add(tail)
      # add this edge to the succs and preds sets
      for head in heads:
        self.succs[tail].add(head)
        self.preds[head].add(tail)
        self.edges.add( (tail, head) )

  # compute the set of dominators for each vertex if direction == "forward"
  # compute the set of post-dominators for each vertex if direction == "backward"
  def compute_dominators(self, direction):
    adjacency = {}
    roots = set([])
    # computing dominators relies on the sources and preds
    if direction == "forward":
      adjacency = self.preds
      roots = self.sources
    # computing post-dominators relies on the sink and succs
    if direction == "backward":
      adjacency = self.succs
      roots = self.sinks
    # using the naive quadratic algorithm: https://en.wikipedia.org/wiki/Dominator_(graph_theory)
    # initialize dominators for roots
    dominators = dict( (v, set([v])) for v in roots )
    # initialize dominators for everything else
    others = self.vertices.difference(roots)
    for v in others:
      dominators[v] = set(self.vertices)
    # fixed point algorithm to remove vertices that are not dominators
    changed = True
    while changed:
      changed = False
      for v in others:
        pred_doms = set.intersection( *[ dominators[p] for p in adjacency[v] ] )
        new_dom = set([v]).union(pred_doms)
        if new_dom != dominators[v]:
          changed = True
        dominators[v] = new_dom
    return dominators 

  # perform a depth-first seach and label the edges as
  # tree edges, forward edges, back edges, or cross edges
  # also mark if the graph has directed cycles 
  def dfs_info(self):
    self.has_cycles = False
    self.edge_labels = {}
    # my_path stores the first path used to discover a node
    # it also marks if a vertex is discovered if the vertex is a key
    my_path = {}
    # recursive step for the depth-first search
    def dfs(v, cur_path):
      my_path[v] = cur_path + [v]
      for u in self.succs[v]:
        if u not in my_path:
          # new vertex; edge is a tree edge, and we should keep searching
          self.edge_labels[(v,u)] = "tree"
          dfs(u, my_path[v])
        else:
          # old vertex, determine what kind of edge this is
          if u in my_path[v]:
            self.edge_labels[(v,u)] = "back"
            self.has_cycles = True
          elif v in my_path[u]:
            self.edge_labels[(v,u)] = "forward"
          else:
            self.edge_labels[(v,u)] = "cross"
    # start the dfs at each source node
    for v in self.sources:
      dfs(v, [])
    self.dfs_paths = my_path

  # find the loops in the control flow graph, and collect up the relevant blocks for each
  def build_loops(self):
    self.loops = []
    # every back edge signifies a loop (if the graph is sufficiently well behaved)
    for (u, v), label in self.edge_labels.items():
      if label == "back":
        entry_block = v
        continue_block = u
        # the entry should have 2 children, should dominate both of them and the continue block
        # and be post-dominated by the continue block
        # the continue block should only have 1 succ
        if len(self.succs[entry_block]) != 2:
          eprint("Entry block " + str(entry_block) + " does not have 2 children.")
        if len(self.succs[continue_block]) != 1:
          eprint("Continue block " + str(continue_block) + " does not have 1 child.")
        should_be_dominated = self.succs[entry_block].union(set([continue_block]))
        if not all( map(lambda b : entry_block in self.dominators[b], iter(should_be_dominated)) ):
          eprint("Entry block does not dominate a child or the continue block")
        if entry_block not in self.post_dominators[continue_block]:
          eprint("Entry block is not post-dominated by the continue block.")
        # the break block is the child that is not on the path to the continue block
        filtered_children = list(filter(lambda c : c not in self.dfs_paths[continue_block], self.succs[entry_block]))
        if len(filtered_children) != 1:
          eprint("Continue block is reached from " + str(len(filtered_childre)) + " children.")
        [break_block] = filtered_children
        # the other blocks in the loop are those reachable from the entry without passing the break block
        # exclude the three named blocks from this list
        explore_stack = [entry_block]
        other_blocks = set([])
        while explore_stack:
          next_block = explore_stack.pop()
          for succ in self.succs[next_block]:
            if succ not in (other_blocks.union([entry_block, continue_block, break_block])):
              explore_stack.append(succ)
              other_blocks.add(succ)
        # create and add the loop
        self.loops.append( Control_Loop(entry_block, continue_block, break_block, other_blocks) )
    # sort the loops so that any nested loop comes before the loop it is nested in
    self.loops.sort(key=lambda l : l.all_blocks)
        
  def __init__(self, tree):
    self.build_graph(tree)
    self.dominators = self.compute_dominators("forward")
    self.post_dominators = self.compute_dominators("backward")
    self.dfs_info()
    self.build_loops()

# node for an abstract syntax tree; it represents a single statement or expression
# a node has a tag saying what kind of statement or expression it is
# storage space for any literal values it might hold
# for jumps of any kind, the val will be a list of ints refering to the blocks they can jump to
# and a list of branches to pointers to sub-statements or expressions
# these pointers take the form of a string which is a key to the inner node map
#
# The specific tags are as follows (unspecified val or children are empty):
#
# Statements:
# "seq": a sequence of statements
#        children are these statements
# "assign": variable assignments
#           val[0] is the variable id
#           children[0] is the expression being assigned
# "send": native function call that does not return a value
#         val[0] is the native function id
#         children are the parameters being passed
# "call": calls another procedure in this script
#         this could potentially be an expression if it returns something
#         val[0] is the id of the procedure
#         children would be parameters if there are any procedures that actually take any
# "return": halts execution of the script
# "label": a label that can be jumped to by a "reallygoto"
#          val[0] is this label's id
# "goto": execution jumps to the given label
#         these are hidden away by the time the AST is displayed
#         val[0] is the block to jump to
# "reallygoto": as above, but the goto will not be hidden
#               it expresses a jump to a "label" statement
#               val[0] is the index of the label to jump to
# "if": conditional jump tabel
#       if there are multiple conditions, the subsequent will be elifs
#       if there is one fewer conditions than there are branches, the final branch will be an else
#       vals are the block destinations, in order
#       children are the conditional expressions, in order
# "loop": runs the inner block until the condition evaluates false
#         after which, it jumps to the break block
#         the update block is run after each iteration of the loop before jumping back to the inner block
#         vals = [inner block, break block, update block]
#         the update block is optional
#         children[0] is the loop condition
# "continue": inside a loop, jump back to the update block and then iterate again
# "break": inside a loop, jump straight out to the break block, ending the loop
#
# Expressions:
# "lit": contains a literal value
#        val[0] is this value
# "var": a variable lookup
#        val[0] is the variable's id
# "func": native function call that returns a value
#         val[0] is the native function id
#         children are the parameters being passed
# for binary and unary operators, the children are the operands
# these operators are listed in bin_symbols and mon_symbols
class AST_Node():

  def copy_node(self, other):
    self.tag = other.tag
    self.vals = other.vals
    self.children = other.children
    self.type = other.type

  def update(self, tag, vals, children, new_type):
    self.tag = tag
    self.vals = vals
    self.children = children
    self.type = new_type

  def __init__(self, tag, vals, children):
    self.tag = tag
    self.vals = vals
    self.children = children
    self.type = "unknown"

  def __str__(self):
    output = ["tag: " + self.tag]
    output.append( "type: " + str(self.type) )
    output.append( "vals: " + str(self.vals) )
    output.append( "children: " + str(self.children) )
    return ", ".join(output)

  __repr__ = __str__

# abstract block syntax tree for the ai program
# contains a list of block nodes (a seq-statement) indexed as the blocks are
# and a map mapping inner node identifiers to actual nodes
# block at index 0 is assumed to be the root of the tree
# note that this technially not be a tree if there are directed cycles in the flow
# but each block will be a tree
class ABST():

  # returns a unique string, used for a node pointer
  def fresh_var(self):
    self.var_count += 1
    return "v" + str(self.var_count)

  # creates and returns two functions that capture self for easier node lookup
  # this is dirty and I know it, but this makes so much easier to write
  def get_node_lookup_functions(self):
    # get a block node from the tree
    def b_node(index):
      return self.block_nodes[index]
    # get an inner node from the tree
    def in_node(pointer):
      return self.inner_nodes[pointer]
    return (b_node, in_node)

  # fixed point operations will perform the given functions on all blocks
  # until no new changes occur
  def fixed_point_block_loop(self, funcs):
    changed = True
    timeout = 1000
    tries = 0
    while changed and tries < timeout:
      changed = False
      tries += 1
      for idx in range( len(self.block_nodes) ):
        if self.block_used[idx]:
          changed |= any( map(lambda f : f( self.block_nodes[idx] ), funcs) )

  # performs the given function on all blocks
  def block_loop(self, func):
    for idx in range( len(self.block_nodes) ):
      if self.block_used[idx]:
        func( self.block_nodes[idx] )

  # creates and stores a new expression that is the boolean negation of the given
  # exp should be a pointer to an exp node
  # returns the pointer to the new expression
  def negate_bool(self, exp):
    loc = self.fresh_var()
    flipped = AST_Node("boolnot", [], [exp])
    self.inner_nodes[loc] = flipped
    self.inner_used[loc] = True
    return loc

  # gives a fairly raw string version of the ABST
  def __str__(self):
    b_node, in_node = self.get_node_lookup_functions()
    
    output = ""
    # print the blocks
    block_strings = ["Blocks:"]
    for idx in range( len(self.block_nodes) ):
      node = b_node(idx)
      used = self.block_used[idx]
      block_strings.append( str(idx) + ": Used: " + str(used) + ", " + str(node) )
    output += "\n".join(block_strings)

    # print the inner nodes
    node_strings = ["Nodes:"]
    for ptr in sorted(self.inner_nodes, key=lambda s : int(s[1:])):
      node = in_node(ptr)
      used = self.inner_used[ptr]
      node_strings.append( ptr + ": Used: " + str(used) + ", " + str(node) )
    output += "\n\n" + "\n".join(node_strings)
    
    return output

  __repr__ = __str__


  # build a ABST from a list of blocks
  def __init__(self, block_list, procedure_info, special_labels, handwritten):
    self.var_count = 0
    self.block_nodes = []
    self.block_used = []
    self.inner_nodes = {}
    self.inner_used = {}
    self.procedure_info = procedure_info
    self.procedure_map = dict( (p.block_num, p.name) for p in procedure_info)
    self.procedure_pop_map = dict( (p.block_num, p.pops) for p in procedure_info)
    self.special_labels = special_labels
    self.special_blocks = set([])
    self.special_gotos = set([])

    # build the nodes for each block
    for blocknum, block in enumerate(block_list):
      block_stmts = []
      var_stack = []
      
      # we go through the block's statements in reverse so that 
      # we are able to know what we need before we create it
      for oper in reversed(block.operations):

        # handles pushing node pointers and popping sub-expressions
        def create_node(tag, vals, pushes, pops):
          loc = ""
          if pushes > 0:
            # this value is used by a future expression or statement
            # that node has a pointer on the stack, waiting to be filled in
            loc = var_stack.pop()
          else:
            # this is a statement that only uses past expressions
            # it will be referenced in the block's statement list,
            # so we need to give it a name and add it to the front of that list
            loc = self.fresh_var()
            block_stmts.insert(0, loc)
          # the number of pops determines how many children this node will need
          # create a new node name for each of them, and push them to the stack
          # to wait for a previous expression to fill it in
          fresh_vars = [ self.fresh_var() for _ in range(pops) ]
          for fvar in reversed(fresh_vars):
            var_stack.append(fvar)
          # create and store the actual node
          node = AST_Node( tag, vals, fresh_vars )
          self.inner_nodes[loc] = node
          self.inner_used[loc] = True

        # list of name lookup tables
        node_name_lookup = [
          litop_names,
          varop_names,
          binop_names,
          monop_names,
          {0x23 : "func"},   # FUNC
          {0x0B : "call"},   # CALL
          {0x09 : "return"}, # END
          assnop_names,
          {0x0D : "goto"},   # GOTO
          {0x25 : "if"},     # COND
          {0x24 : "send"},   # SEND
        ]

        # create the nodes for all of the operations
        found_name = False
        for lookup_entry in node_name_lookup:
          if oper.opcode in lookup_entry:
            name = lookup_entry[oper.opcode]
            create_node(name, oper.args, oper.pushes, oper.pops)
            found_name = True
  
        # if we see a PROC tag, we need to create variables for arguments if the procedure has them
        if oper.opcode == 0x07:   #PROC
          if blocknum in self.procedure_pop_map:
            for argnum in range(self.procedure_pop_map[blocknum]):
              create_node("var", [-1 - argnum], 1, 0)
          found_name = True

        # any other opcodes are errors or unhandled
        if not found_name:
          eprint("Operation " + str(oper) + " could not be added to the ABST")
        
      # create the block's node
      node = AST_Node( "seq", [], block_stmts )
      self.block_nodes.append( node )
      self.block_used.append( True )

    self.handle_special_labels()
    self.handle_directed_cycles()
    self.clear_single_gotos()
    if not handwritten:
      self.handle_undirected_cycles()

    self.clean_loops()
    self.clean_empty_blocks()

  # if there were actual gotos in the original code (special labels)
  # we should take care of them first because they can create difficult graph structures
  def handle_special_labels(self):
    b_node, in_node = self.get_node_lookup_functions()

    # given a new AST_Node, stores it and returns its fresh location
    def stmt_from_node(node):
      loc = self.fresh_var()
      self.inner_nodes[loc] = node
      self.inner_used[loc] = True
      return loc

    # handle each special label in turn
    for block_num in self.special_labels:
      # add a label statment to this block
      # or to the start of the end of its single goto chain
      chain_end = block_num
      special_block = b_node( chain_end )
      while True:
        if len(special_block.children) == 1:
          stmt = in_node( special_block.children[0] )
          if stmt.tag == "goto":
            self.block_used[chain_end] = False
            chain_end = stmt.vals[0]
            special_block = b_node( chain_end )
            continue
        break
      stmt_loc = stmt_from_node( AST_Node("label", [block_num], []) )
      special_block.children.insert(0, stmt_loc)
      self.special_blocks.add(chain_end)
      
      # collect blocks that go to this one
      if_reaches = []
      goto_reaches = []
      for idx, block in enumerate(self.block_nodes):
        last_stmt = in_node( block.children[-1] )
        # goto and if branch to specific blocks
        if last_stmt.tag == "goto" and block_num in last_stmt.vals:
          goto_reaches.append(idx)
        if last_stmt.tag == "if" and block_num in last_stmt.vals:
          if_reaches.append(idx)
      if len(if_reaches) > 1:
        eprint("2 or more if statements have branches to the same label")
      # change the gotos to really gotos
      # leaving an arbitrary one alone, or the if branch if there is one
      # this chosen branch must now point to chain end
      # however, if we took a chain, and there are other pointers to the new label block,
      # do not do this
      reaches = if_reaches + goto_reaches
      
      chain_has_preds = False
      for idx, block in enumerate(self.block_nodes):
        last_stmt = in_node( block.children[-1] )
        if last_stmt.tag in ["goto", "if"] and chain_end in last_stmt.vals:
          chain_has_preds = True
      
      if not (chain_has_preds and chain_end != block_num):
        first = reaches.pop(0)
        if if_reaches:
          if_stmt = in_node( b_node( first ).children[-1] )
          for idx in range(2):
            if if_stmt.vals[idx] == block_num:
              if_stmt.vals[idx] = chain_end
        else:
          goto_stmt = in_node( b_node( first ).children[-1] )
          goto_stmt.vals[0] = chain_end
      for idx in reaches:
        block = b_node(idx)
        block.children[-1] = stmt_from_node( AST_Node("reallygoto", [block_num], []) )
        self.special_gotos.add(idx)

  # handles directed cycles by introducing loop constructs
  def handle_directed_cycles(self):
    b_node, in_node = self.get_node_lookup_functions()

    # creates and stores a new tag stmt, and returns its pointer
    def new_single_stmt(tag):
      loc = self.fresh_var()
      stmt = AST_Node(tag, [], [])
      self.inner_nodes[loc] = stmt
      self.inner_used[loc] = True
      return loc

    # creates a new block that contains a single tag stmt
    # returns the new block's index
    def new_single_block(tag):
      tag_stmt = new_single_stmt(tag)
      node = AST_Node( "seq", [], [tag_stmt] )
      self.block_nodes.append( node )
      self.block_used.append( True )
      return len(self.block_nodes) - 1

    # completely anylyze the control flow graph
    cfg = Control_Flow_Graph(self)
    #print "\n".join([str(loop.__dict__) for loop in cfg.loops])
    
    # for each loop in the graph, add loop constructs
    # the loops have already been sorted so that nested loops come first
    for loop in cfg.loops:

      # first, replace the if branch at the end of the entry block with a loop
      entry_node = b_node( loop.entry_block )
      if_stmt = in_node( entry_node.children[-1] )
      # determine which branch contains the break block and which contains the inside of the loop
      inner_block = if_stmt.vals[0]
      break_block = if_stmt.vals[1]
      cond_exp = if_stmt.children[0]
      if break_block != loop.break_block:
        # we need to flip the branches and negate the condition
        inner_block = if_stmt.vals[1]
        break_block = if_stmt.vals[0]
        cond_exp = self.negate_bool(cond_exp)
      # loop stmts have 3 branches and one condition exp
      loop_stmt = AST_Node( "loop", [inner_block, break_block, loop.continue_block], [cond_exp] )
      # replace the if
      self.inner_nodes[ entry_node.children[-1] ] = loop_stmt

      # next, remove the jump at the end of the continue_block (this breaks the explicit cycle)
      continue_node = b_node( loop.continue_block )
      continue_node.children.pop()

      # finally, replace any jumps inside the loop to the break or continue nodes appropriately
      for block in loop.other_blocks:
        block_node = b_node( block )
        last_stmt = in_node( block_node.children[-1] )
        # gotos can just be replaced with a continue or break
        if last_stmt.tag == "goto":
          destination = last_stmt.vals[0]
          new_tag = ""
          if destination == loop.continue_block:
            new_tag = "continue"
          elif destination == loop.break_block:
            new_tag = "break"
          else:
            continue
          new_stmt = new_single_stmt(new_tag)
          self.inner_used[ block_node.children[-1] ] = False
          block_node.children[-1] = new_stmt
        # for ifs, create a new block with a single statement, and replace the branch
        elif last_stmt.tag == "if":
          for idx, destination in enumerate(last_stmt.vals):
            new_tag = ""
            if destination == loop.continue_block:
              new_tag = "continue"
            elif destination == loop.break_block:
              new_tag = "break"
            else:
              continue
            new_block = new_single_block(new_tag)
            last_stmt.vals[idx] = new_block

  # removes all blocks that contain a single statement that is a goto
  # and updates its predecessors accordingly
  def clear_single_gotos(self):
    b_node, in_node = self.get_node_lookup_functions()

    # remove blocks with only a single goto statement
    def remove_single_goto(comes_from, goes_to):
      for idx, block in enumerate(self.block_nodes):
        if self.block_used[idx] and block.children:
          ptr = block.children[-1]
          stmt = in_node(ptr)
          if stmt.tag in ["if", "goto", "loop"]:
            for branch_loc, b in enumerate(stmt.vals):
              if b == comes_from:
                stmt.vals[branch_loc] = goes_to
      self.block_used[comes_from] = False
    for idx, block in enumerate(self.block_nodes):
      if self.block_used[idx]:
        if len(block.children) == 1:
          stmt = in_node( block.children[0] )
          if stmt.tag == "goto":
            remove_single_goto(idx, stmt.vals[0])
      

  # handles cycles in the underlying undirected graph
  # this should be run before flattening conditionals
  # it will not handle directed cycles (that should be done first)
  def handle_undirected_cycles(self):
    b_node, in_node = self.get_node_lookup_functions()

    # compute the least common ancestor of 2 blocks
    # TODO: this seems to assume something more on the structure of the graph
    # than just no directed cycles
    def lca2(b1, b2):
      b1_path = [b1]
      cur_b = b1
      while cur_b not in self.procedure_map:
        # arbitrarily walk towards the root
        cur_b = predecesors[cur_b][0]
        b1_path.append(cur_b)
      # do the same for b2, until we have a match
      cur_b = b2
      while cur_b not in b1_path:
        cur_b = predecesors[cur_b][0]
      return cur_b

    # compute the least common ancestor of a list of blocks
    # do this by performing pairwise lca, in a binary tree fasion
    def lca(blocks):
      # base case
      if len(blocks) == 1:
        return blocks[0]
      # compute lca of pairs in the list
      lcas = list(map( lambda p : lca2(p[0],p[1]), zip(blocks[0::2], blocks[1::2]) ))
      # add in the odd element if there is one
      if len(blocks) % 2 == 1:
        lcas.append(blocks[-1])
      # recursively reduce the size of the list
      return lca(lcas)
    
    # compute each block's predecesors
    predecesors = [[] for _ in range( len(self.block_nodes) )]
    for idx, block in enumerate(self.block_nodes):
      if self.block_used[idx] and block.children:
        ptr = block.children[-1]
        stmt = in_node(ptr)
        if stmt.tag in ["if", "goto", "loop"]:
          for b in stmt.vals:
            predecesors[b].append(idx)

    # get a reverse topological sort of the block graph
    # using DFS algorithm here: https://en.wikipedia.org/wiki/Topological_sorting
    # note that this algorithm will get stuck in an infinite loop if cycles remain in the CFG
    # (this is easy to fix, but the crash will catch bad loop fixing if it happens...)
    rev_top_sort = []
    marked = []
    def visit(b):
      if b in marked:
        return
      for b_pred in predecesors[b]:
        visit(b_pred)
      marked.append(b)
      rev_top_sort.insert(0, b)
    for b in compress(range(len(self.block_nodes)), self.block_used):
      if b not in marked:
        visit(b)

    # merge a block into the lca of its predecesors
    def merge_into(inner, outer):
      # strip predecesors of their links to this node
      for pred in predecesors[inner]:
        node = b_node(pred)
        stmt = in_node( node.children[-1] )
        # simply remove the goto statment altogether
        if stmt.tag == "goto":
          node.children.pop()
        # we need to remove only one branch of the if
        if stmt.tag == "if":
          # false branch is easy
          if stmt.vals[1] == inner:
            stmt.vals.pop()
          # true branch needs to flip the condition, then remove the old true branch
          else:
            stmt.children[0] = self.negate_bool( stmt.children[0] )
            stmt.vals.pop(0)
      # add the statements of the inner block to the outer one
      b_node(outer).children += b_node(inner).children
      self.block_used[inner] = False
            
    # any block with multiple predecesors should be moved
    # this should be done in reverse topological order so we do not combine into blocks that have already been merged away
    for b in rev_top_sort:
      if len( predecesors[b] ) > 1:
        merge_into(b, lca( predecesors[b] ))
 
  # returns a string representing the code of an ABST
  # if a function formater is given, it it will be used in place of function display default behavior
  def display_decompilation(self, func_display=None):
    b_node, in_node = self.get_node_lookup_functions()

    def indent(s):
      ws = "    "
      return ws + s.replace("\n", "\n" + ws)

    def unindent_labels(s):
      lines = s.split('\n')
      lines2 = [line.lstrip() if line.find("--label:") > -1 else line for line in lines]
      return '\n'.join(lines2)

    def display_var_name(index):
      if index >= 0:
        return 'r' + str(index)
      else:
        return 'p' + str(-1 - index)

    def display_native_name(index):
      if index in native_functions:
        name = native_functions[index].name
        if name[0] == "_":
          name = name[1:]
        return name
      else:
        return "func_" + "{:#06x}".format(index)

    def display_func_or_send(node):
      function_params = list(map( compose(display_exp_node, in_node), node.children))
      if func_display is not None:
        formated_name = func_display(node.vals[0], list(map( in_node, node.children )), function_params )
        if formated_name[0]:
          return formated_name[1]
      function_name = display_native_name(node.vals[0])
      return function_name + "(" + ", ".join(function_params) + ")"
    
    def display_stmt_node(node):
      
      # seq stmt
      if node.tag == "seq":
        if not node.children:
          return "pass"
        return "\n".join( map(compose(display_stmt_node, in_node), node.children) )

      # assign stmt
      elif node.tag == "assign":
        return display_var_name(node.vals[0]) + " = " + display_exp_node( in_node(node.children[0]) )

      # return, break, continue stmt
      elif node.tag in ["return", "break", "continue"]:
        return node.tag

      # goto stmt
      elif node.tag == "goto":
        return display_stmt_node( b_node(node.vals[0]) )

      # label stmt
      elif node.tag == "label":
        label_name = self.special_labels[ node.vals[0] ]
        return "--label: " + label_name

      # actual goto stmt
      elif node.tag == "reallygoto":
        label_name = self.special_labels[ node.vals[0] ]
        return "goto " + label_name
      
      # call stmt
      elif node.tag in "call":
        function_name = self.procedure_map[ node.vals[0] ]
        function_params = ", ".join( map( compose(display_exp_node, in_node), node.children) )
        return function_name + "(" + function_params + ")"

      # send stmt
      elif node.tag == "send":
        return display_func_or_send(node)

      # if stmt
      elif node.tag == "if":
        cond_lines = []
        first = True
        for child in node.children:
          cond_name = "if" if first else "elif"
          cond = cond_name + " " + display_exp_node( in_node( child ) ) + ":"
          cond_lines.append(cond)
          first = False
        blocks = []
        for jump_loc in node.vals:
          block = display_stmt_node( b_node( jump_loc ) )
          # indent the blocks
          block = indent(block)
          blocks.append(block)
        # create full stmt
        if len(cond_lines) == len(blocks):
          interleaved = [val for pair in zip(cond_lines, blocks) for val in pair]
          return "\n".join(interleaved)
        else:
          interleaved = [val for pair in zip(cond_lines, blocks[:-1]) for val in pair]
          return "\n".join(interleaved) + "\nelse:\n" + blocks[-1]

      # loop stmt
      elif node.tag == "loop":
        cond_str = display_exp_node( in_node(node.children[0]) )
        branch_strs = list(map( compose(display_stmt_node, b_node), node.vals ))
        inner_str = indent( branch_strs[0] )
        top_line = ""
        if len(node.vals) == 3:
          update_str = branch_strs[2].replace("\n", ", ")
          top_line = "for(; " + cond_str + "; " + update_str + " ):"
        else:
          top_line = "while " + cond_str + ":"
        return "\n".join([ top_line, inner_str, branch_strs[1] ])

    def display_exp_node(node):
      
      # binary exp
      if node.tag in bin_symbols:
        lhs = display_exp_node( in_node(node.children[0]) )
        rhs = display_exp_node( in_node(node.children[1]) )
        sym = bin_symbols[node.tag]
        return "(" + lhs + " " + sym + " " + rhs + ")"

      # unary exp
      elif node.tag in mon_symbols:
        arg = display_exp_node( in_node(node.children[0]) )
        sym = mon_symbols[node.tag]
        return sym + arg

      # var exp
      elif node.tag == "var":
        return display_var_name( node.vals[0] )

      # literals
      elif node.tag == "lit":
        return str( node.vals[0] )

      # func exp
      elif node.tag == "func":
        return display_func_or_send(node)

    # display each procedure
    proc_strs = []
    for proc in self.procedure_info:
      args_strs = map(display_var_name, range(-1, -1 - proc.pops, -1))
      proc_str = proc.name + "(" + ",".join(args_strs) + "):\n"
      proc_str += indent(display_stmt_node( b_node(proc.block_num) ))
      proc_str = unindent_labels(proc_str)
      proc_strs.append(proc_str)
    return "\n\n".join(proc_strs)

  # cleaning up loops is done by moving continues out of conditionals when it's safe
  # removing code after continues in a sequence
  # and moving the update step to replace are remaining continues
  def clean_loops(self):
    b_node, in_node = self.get_node_lookup_functions()

    # creates and stores a new tag stmt, and returns its pointer
    def new_single_stmt(tag):
      loc = self.fresh_var()
      stmt = AST_Node(tag, [], [])
      self.inner_nodes[loc] = stmt
      self.inner_used[loc] = True
      return loc

    # creates and stores a new tag stmt, and returns its pointer
    def new_goto_stmt(block_num):
      loc = self.fresh_var()
      stmt = AST_Node("goto", [block_num], [])
      self.inner_nodes[loc] = stmt
      self.inner_used[loc] = True
      return loc
  
    # gets the block index of the end of a goto chain
    def chain_end(idx):
      end = idx
      chain = b_node(end)
      ended = False
      while not ended:
        if chain.children:
          last_stmt = in_node( chain.children[-1] )
          if last_stmt.tag == "goto":
            end = last_stmt.vals[0]
            chain = b_node(end)
          else:
            ended = True
        else:
          ended = True
      return end
      
    # moves continues down to outside an if statement
    def move_safe_continues(block):
      for idx, child in enumerate( map(in_node, block.children) ):
        if child.tag == "if":
          # recursively move out continues
          map( compose(move_safe_continues, b_node), child.vals)
          # find the blocks ending the goto chains of a branch
          chain_ends = []
          for val in child.vals:
            chain_ends.append( chain_end(val) )
          # check if both branches break normal control
          flow_broken_in_branch = []
          for branch in map(b_node, chain_ends):
            if branch.children:
              last_stmt = in_node(branch.children[-1])
              flow_broken_in_branch.append(last_stmt.tag in ["return", "break", "continue", "reallygoto"])
            else:
              flow_broken_in_branch.append(False)
          if all(flow_broken_in_branch):
            # remove the continues ending blocks
            for branch in map( compose(b_node, chain_end), child.vals):
              if branch.children:
                last_stmt = in_node(branch.children[-1])
                if last_stmt.tag == "continue":
                  self.inner_used[ branch.children[-1] ] = False
                  branch.children.pop()
            # place a continue after the conditional, and remove the rest of the sequence
            for ptr in block.children[idx+1:]:
              self.inner_used[ptr] = False
            continue_stmt = new_single_stmt("continue")
            block.children[idx+1:] = [continue_stmt]

    # move continues out for each loop
    for block in self.block_nodes:
      for stmt in map( in_node, block.children ):
        if stmt.tag == "loop":
          move_safe_continues( b_node(stmt.vals[0]) )

    # remove continues that end a loop
    for block in self.block_nodes:
      for stmt in map( in_node, block.children ):
        if stmt.tag == "loop":
          inner_block = b_node(stmt.vals[0])
          if inner_block.children:
            last_stmt = in_node( inner_block.children[-1] )
            if last_stmt.tag == "continue":
              inner_block.children.pop()

    # checks if a given loop contains any continues
    # should not count continues in a nested loop
    def block_has_continues(block):
      def stmt_has_continues(stmt):
        if stmt.tag == "continue":
          return True
        elif stmt.tag in ["goto", "if"]:
          return any( map( compose(block_has_continues, b_node), stmt.vals ) )
        else:
          return False
      return any( map( compose(stmt_has_continues, in_node), block.children ) )

    # if a loop does not have continues, move the update step (if there is one) to the bottom of the loop
    for block in self.block_nodes:
      for stmt in map( in_node, block.children ):
        if stmt.tag == "loop" and len(stmt.vals) == 3:
          inner_block = b_node( stmt.vals[0] )
          inner_block.children.append( new_goto_stmt(stmt.vals[2]) )
          stmt.vals.pop()
    
  # clean up empty blocks
  def clean_empty_blocks(self):
    b_node, in_node = self.get_node_lookup_functions()

    # check if the given block num points to an empty block
    def block_is_empty(block_num):
      block = b_node(block_num)
      return len(block.children) == 0

    # go through each block and remove statements as necessary
    has_changes = True
    while has_changes:
      has_changes = False
      for block in self.block_nodes:
        for idx, stmt in enumerate( map(in_node, block.children) ):
          # goto to empty block can just be removed
          if stmt.tag == "goto":
            dest = stmt.vals[0]
            if block_is_empty( dest ):
              del block.children[idx]
              has_changes = True
              self.block_used[dest] = False
          # there are a few cases for ifs depending on how many branches
          # there are, and how many/which are empty
          # this pass is run before elif blocks can be created, so there
          # are at most two branches
          elif stmt.tag == "if":
            # no else case
            if len(stmt.vals) == 1:
              dest = stmt.vals[0]
              if block_is_empty( dest ):
                del block.children[idx]
                has_changes = True
                self.block_used[dest] = False
            else:
              # note that if both blocks are empty, it is not necessarily safe to
              # remove the whole if stmt because the condition may have side-effects
              t_block = stmt.vals[0]
              f_block = stmt.vals[1]
              # if f_block is empty, just remove it
              if block_is_empty(f_block):
                stmt.vals.pop()
                self.block_used[f_block] = False
              # if t_block is empty, flip the condition and remove the now false block
              elif block_is_empty(t_block):
                stmt.children[0] = negate_bool( stmt.children[0] )
                stmt.vals.pop(0)
                self.block_used[t_block] = False
          # loops with empty updates can drop the update step
          elif stmt.tag == "loop" and len(stmt.vals) == 3:
            u_block = stmt.vals[2]
            if block_is_empty(u_block):
              stmt.vals.pop()
              self.block_used[u_block] = False
 
  # flatten the branch structure of the tree by converting
  # if ... else (if ... else ...)   to
  # if ... elif ... else ...
  # this can be done when the block in the last branch of an if or elif has a single statement, and it is an if
  def flatten_abst_conds(self):
    b_node, in_node = self.get_node_lookup_functions()

    def flatten_block(block):
      # check if the last block is an if
      change = False
      for stmt in map(in_node, block.children):
        if stmt.tag == "if":
          # we cannot flatten without an else block
          if len(stmt.vals) < 2:
            continue
          # keep flattening at this level until we cannot anymore
          timeout = 1000
          for _ in range(timeout):
            # check the block in the else block,
            # if it contains a single if statement, we can flatten
            else_block = b_node( stmt.vals[-1] )
            else_block_stmt = in_node( else_block.children[0] )
            if len(else_block.children) == 1 and else_block_stmt.tag == "if":
              # flatten by stealing the condition and branches
              self.block_used[ stmt.vals[-1] ] = False
              stmt.children += else_block_stmt.children
              stmt.vals = stmt.vals[:-1] + else_block_stmt.vals
              change = True
            else:
              break
      return change

    self.fixed_point_block_loop([flatten_block])

  # if every execution of an if block results in a return,
  # we can move the else's code up into the if block
  def eliminate_useless_elses(self):
    b_node, in_node = self.get_node_lookup_functions()
  
    # returns true if the given block never jumps outside
    def check_always_returns(node):
      last_stmt = in_node( node.children[-1] )
      if last_stmt.tag == "return":
        return True
      elif last_stmt.tag in ["if", "goto"]:
        # recursively check if the branches return at the end
        for block in map( b_node, last_stmt.vals ):
          if not check_always_returns:
            return False
        return True
      return False
    
    # run on every block
    def eliminate_block_elses(node):
      # find if's with elses
      for child_idx, child in enumerate( map(in_node, node.children) ):
        if child.tag == "if" and len(child.vals) > len(child.children):
          # check if the block before the else block always returns
          always_returns = check_always_returns( b_node(child.vals[-2]) )
          if always_returns:
            # move the block up
            else_block_idx = child.vals.pop()
            insert_pos = child_idx + 1
            node.children[insert_pos:insert_pos] = b_node(else_block_idx).children
            self.block_used[else_block_idx] = False
            # we've changed the block we are looping through, so break out
            return True
      return False

    self.fixed_point_block_loop([eliminate_block_elses])


  # perform constant folding on all of the blocks of the given tree
  def fold_constants(self):
    b_node, in_node = self.get_node_lookup_functions()

    # foldable expressions and their functions
    foldable = {
      "add" : (lambda v : v[0] + v[1]),
      "sub" : (lambda v : v[0] - v[1]),
      "mul" : (lambda v : v[0] * v[1]),
      "div" : (lambda v : v[0] if v[1] == 0 else v[0] / v[1]),
      "neg" : (lambda v : -1 * v[0]),
      "bitnot" : (lambda v : (~v[0]) ),
      "boolnot" : (lambda v : (0 if v[0] == 1 else 1) ),
      "or" : (lambda v : v[0] | v[1]),
      "and" : (lambda v : v[0] & v[1]),
      "eq" : (lambda v : 1 if v[0] == v[1] else 0),
      "neq" : (lambda v : 1 if v[0] != v[1] else 0),
      "lt" : (lambda v : 1 if v[0] < v[1] else 0),
      "gt" : (lambda v : 1 if v[0] > v[1] else 0),
      "lte" : (lambda v : 1 if v[0] <= v[1] else 0),
      "gte" : (lambda v : 1 if v[0] >= v[1] else 0),
    }
    
    # fold constants within a given node
    def fold_const_in_node(node):
      # recursively fold constants in all sub-children
      for child in node.children:
        fold_const_in_node( in_node(child) )
      # make sure this can be folded
      if node.tag not in foldable:
        return
      # check if children are literals
      vals = []
      for child in node.children:
        child_node = in_node( child )
        if child_node.tag != "lit":
          return
        vals.append( child_node.vals[0] )
      # make this a literal
      node.vals = [foldable[node.tag](vals)]
      node.tag = "lit"
      # the children are now unreachable
      for child in node.children:
        self.inner_used[child] = False
      node.children = []

    self.block_loop(fold_const_in_node)

          
  # infer the types of all nodes for which it is possible
  def infer_types(self):
    b_node, in_node = self.get_node_lookup_functions()
 
    # infer the type of a given node
    def infer_node_type(node):
      # recursively infer types of sub-expressions
      for child in node.children:
        infer_node_type( in_node(child) )
      # statements are just statements
      if node.tag in ["seq", "assign", "send", "return", "if", "goto"]:
        node.type = "stmt"
      # boolean expresions
      elif node.tag in ["eq", "neq", "lt", "gt", "lte", "gte", "boolnot"]:
        node.type = "bool"
      # int expressions
      elif node.tag in ["add", "sub", "mul", "div", "neg", "bitnot"]:
        node.type = "int"
      # possibly boolean if a subexpressions is
      elif node.tag in ["and", "or"]:
        children = map(in_node, node.children)
        are_bools = map(lambda c : c.type == "bool", children)
        if all(are_bools):
          node.type = "bool"
      # we know for sure a literal is an int if it's not 0 or 1
      elif node.tag in ["lit"]:
        if node.vals[0] not in [0, 1]:
          node.type = "int"
      # functions have their return type as their type
      elif node.tag in ["func"]:
        func_id = node.vals[0]
        if func_id in native_functions:
          node.type = native_functions[func_id].type

    self.block_loop(infer_node_type)


  # simplify boolean expressions where it is safe to do so
  def simplify_boolean_expressions(self):
    b_node, in_node = self.get_node_lookup_functions()

    # simplifies a boolean expression by replacing them with more compact versions
    def simplify_boolean_expression(node):
      changed = False
      # recursively infer types of sub-expressions
      for child in node.children:
        if child == 1:
          eprint (", ".join(map(str, [node.tag, node.vals, node.children, node.type])))
        changed |= simplify_boolean_expression( in_node(child) )
      def mark_unused(pointer):
        self.inner_used[pointer] = False
      if node.tag in ["and", "or"]:
        set_val = 0 if node.tag == "and" else 1
        other_val = 1 if set_val == 0 else 0
        [rhs, lhs] = map(in_node, node.children)
        if [rhs.tag, lhs.type] == ["lit", "bool"] or [rhs.type, lhs.tag] == ["bool", "lit"]:
          bool_side = rhs
          lit_side = lhs
          if rhs.tag == "lit":
            bool_side = lhs
            lit_side = rhs
          if lit_side.vals[0] == other_val:
            map(mark_unused, node.children)
            node.copy_node(bool_side)
            changed = True
          elif lit_side.vals[0] == set_val:
            map(mark_unused, node.children)
            node.update("lit", [set_val], [], "bool")
            changed = True
      
      elif node.tag in ["eq", "neq"]:
        [rhs, lhs] = map(in_node, node.children)
        if [rhs.tag, lhs.type] == ["lit", "bool"] or [rhs.type, lhs.tag] == ["bool", "lit"]:
          bool_side = rhs
          lit_side = lhs
          bool_idx = 0
          lit_idx = 1
          if rhs.tag == "lit":
            bool_side = lhs
            lit_side = rhs
            bool_idx = 1
            lit_idx = 0
          if lit_side.vals[0] == 1:
            map(mark_unused, node.children)
            node.copy_node(bool_side)
            changed = True
          elif lit_side.vals[0] == 0:
            mark_unused(node.children[lit_idx])
            node.update("boolnot", [], [node.children[bool_idx]], "bool")
            changed = True

      return changed

    # push down boolean nots when applicable
    # TODO: write this when it seems appropriate
    def simplify_not_expression(node):
      return False

    # fixed point operation; simplification could introduce nots that can be pushed down
    self.fixed_point_block_loop( [simplify_boolean_expression, simplify_not_expression] )

 
  # run all required optimization passes on the given ABST
  # there is a boolean flag for each optimization pass, which all default to True
  def optimize_abst(self, flatten_conditionals=True, flatten_elses=True, constant_folding=True, simplify_conditions=True):
    if flatten_conditionals:
      self.flatten_abst_conds()
    if flatten_elses:
      self.eliminate_useless_elses()
    if constant_folding:
      self.fold_constants()
    if simplify_conditions:
      self.infer_types()
      self.simplify_boolean_expressions()

# a list of instructions with exactly one entry and one exit
class Basic_Block():

  # display a basic block
  def display(self):
    output = ["-Block " + str(self.identifier)]
    output += map(str, self.operations)
    return "\n".join(output)
  
  # create the basic block from a list of operations
  def __init__(self, opers, index):
    self.operations = opers
    self.identifier = index

  __str__ = __repr__ = display

# transform an unpacked flow file into a list of basic blocks,
# with slightly more powerful instruction representation
def abstract_flow(orig_flow):

  flow = copy.deepcopy(orig_flow)
  proc_info = []
  special_labels = {}

  # rename all of the blocks
  new_id = 0
  for graph, proc in zip(flow.block_graphs, flow.flow_blocks):
    for block in proc:
      # skip unreachable
      if block.label_kind == "jump" and not graph.reachable[block.label_index]:
        continue
      old_id = block.label_index
      block.label_index = new_id
      # make sure jumps that used to jump to this block still do
      for new_proc, orig_proc in zip(flow.flow_blocks, orig_flow.flow_blocks):
        for new_block, orig_block in zip(new_proc, orig_proc):
          for new_instr, orig_instr in zip(new_block.instructions, orig_block.instructions):
            if block.label_kind in ["jump", "special"] and orig_instr.opcode in jumpers and orig_instr.operand == old_id:
              new_instr.operand = new_id
            elif block.label_kind == "proc" and orig_instr.opcode in callers and orig_instr.operand == old_id:
              new_instr.operand = new_id
      # create new procedure info if this is the start of a procedure
      if block.label_kind == "proc":
        proc_info.append( Procedure_Info(new_id, block.name) )
      # create a special label entry if this is a special label
      if block.label_kind == "special":
        special_labels[new_id] = block.name
      new_id += 1

  basic_blocks = new_id * [0]

  # construct the new basic blocks, replacing instructions with operations
  for graph, proc, orig_proc in zip(flow.block_graphs, flow.flow_blocks, orig_flow.flow_blocks):
    for block, orig_block in zip(proc, orig_proc):
      # skip unreachable
      if block.label_kind == "jump" and not graph.reachable[orig_block.label_index]:
        continue
      operations = []
      found_new_block = False
      need_skip = False
      for idx, instr in enumerate( block.instructions ):
        # if the previous instruction was a FUNC, skip this PUSHREG
        if need_skip:
          need_skip = False
          continue
        # we split the block, creating a basic block with what we have, and treating the remainder as a new flow block
        # the conditional jump at the end of the basic block goes to where it used to, and the new block
        # however, we should NOT split if this is the last instruction in the original block
        if instr.opcode == 0x1C:  # IF
          operations.append( Operation(0x25, [new_id, instr.operand]) )   # COND
          block_index = block.label_index
          if found_new_block:
            basic_blocks.append( Basic_Block(list(operations), block_index) )
          else:
            basic_blocks[block_index] = Basic_Block(list(operations), block_index)
            found_new_block = True
          if idx < len(block.instructions) - 1:
            operations = []
            block.label_index = new_id
            new_id += 1
          else:
            found_new_block = False
        # we transform a COMM based on whether or not it returns a value
        elif instr.opcode == 0x08:  # COMM
          next_instr = block.instructions[idx + 1]
          if next_instr.opcode == 0x04:  # PUSHREG
            need_skip = True
            operations.append( Operation(0x23, [instr.operand]) )  # FUNC
          else:
            operations.append( Operation(0x24, [instr.operand]) )  # SEND
        # we transform a JUMP into a CALL followed by an END
        elif instr.opcode == 0x0A:  # JUMP
          operations.append( Operation(0x0B, [instr.operand]) )  # CALL
          operations.append( Operation(0x09, []) )  # END
        # no operand instructions have an empty list of operands
        elif instr.opcode in no_operands:
          operations.append( Operation(instr.opcode, []) )
        # everything else is just transformed normally
        else:
          operations.append( Operation(instr.opcode, [instr.operand]) )
      # create a basic block with the remaining (or all of the) operations
      block_index = block.label_index
      if found_new_block:
        basic_blocks.append( Basic_Block(list(operations), block_index) )
      else:
        basic_blocks[block_index] = Basic_Block(list(operations), block_index)

  # guess the number of pops for the unknown native functions and procedures
  
  # TODO: assume a proc pops it's arguments immediately
  for proc in proc_info:
    block = basic_blocks[proc.block_num]
    proc.pops = 0
    for oper in block.operations:
      if oper.opcode in [0x05, 0x06, 0x20, 0x21, 0x1c] + assn_ops:  # POPs 1 thing
        proc.pops += 1
      elif oper.opcode == 0x07: #PROC
        pass
      elif oper.opcode in [0x23, 0x24]: #FUNC or SEND
        if oper.pops is not None:
          proc.pops += oper.pops
        else:
          eprint("An unknown native function begins a procedure. Cannot determine the number of arguments to the procedure.")
          break
      else:
        break
    # TODO: assume a proc cannot return anything for now
    proc.pushes = 0
    
  procedure_pop_map = dict( (p.block_num, p.pops) for p in proc_info)
  for block_num, block in enumerate(basic_blocks):
    def find_low_after(idx, height):
      lowest = height
      height += block.operations[idx].pushes
      for oper in block.operations[(idx+1):]:
        if oper.pops is not None:
          height -= oper.pops
        lowest = min(lowest, height)
        height += oper.pushes
      return lowest
    height = 0
    if block_num in procedure_pop_map:
      height = procedure_pop_map[block_num]
    for idx, oper in enumerate(block.operations):
      if oper.opcode == 0x0B:  # CALL
        for proc in proc_info:
          if proc.block_num == oper.args[0]:
            oper.pushes = proc.pushes
            oper.pops = proc.pops
      if oper.pops is None:
        oper.pops = find_low_after(idx, height)
      height -= oper.pops
      if height < 0:
        eprint("Stack underflowed in block " + str(block.identifier) + "!")
      height += oper.pushes

  return basic_blocks, proc_info, special_labels

# returns a special function formater for enemy ai
# formater returns a tuple, the first element if a boolean saying if the function could be formated
# if it is False the default formatting is used
# otherwise, the second element of the tuple is the format
def get_enemy_function_formater(tree, enemy_names, skill_names):
  
  def format_function(func_id, params, param_strs):
    # checks if a node is a literal, if so returns the tuple (True, lit)
    # otherwise returns (False, None)
    def check_lit(node):
      if node.tag == "lit":
        return (True, node.vals[0])
      return (False, None)

    if func_id not in native_functions:
      return (False, None)

    name = native_functions[func_id].name
    if name[0] == "_":
      name = name[1:]

    # individual formats for each function
    if name == "set_action_attack":
      return ( True, "Use a normal attack." )
    elif name == "set_action_skill":
      lit = check_lit( params[0] )
      if lit[0]:
        skill = skill_names[ lit[1] ]
        return ( True, "Use " + skill + " (skill " + str( lit[1] ) + ").")
    elif name == "set_action_flee":
      return ( True, "Attempt to escape." )
    elif name == "set_action_defend":
      return ( True, "Defend." )
    elif name == "set_action_leveled_skill":
      lits = list(map(check_lit, params ))
      if lits[0][0] and lits[1][0]:
        skill = skill_names[ lits[0][1] ]
        level = lits[1][1]
        return ( True, "Use level " + str(level) + " " + skill + " (skill " + str( lits[0][1] ) + ").")

    elif name == "set_targeting_standard":
      return ( True, "Use standard targeting." )
    elif name == "set_targeting_self":
      return ( True, "Targets itself." )

    elif name == "retrieve":
      lit = check_lit( params[0] )
      if lit[0]:
        return ( True, "v" + str( lit[1] ))
    elif name == "store":
      lit = check_lit( params[1] )
      if lit[0]:
        return ( True, "v" + str( lit[1] ) + " = " + param_strs[0] )
    elif name == "get_flag":
      lit = check_lit( params[0] )
      if lit[0]:
        return ( True, "flag" + str( lit[1] ))
    elif name == "set_flag":
      lit = check_lit( params[0] )
      if lit[0]:
        return ( True, "flag" + str( lit[1] ) + " = True")
    elif name == "unset_flag":
      lit = check_lit( params[0] )
      if lit[0]:
        return ( True, "flag" + str( lit[1] ) + " = False")

    elif name == "enemy_exists":
      lit = check_lit( params[0] )
      if lit[0]:
        enemy = enemy_names[ lit[1] ]
        return ( True, "there is a(n) " + enemy + " (enemy " + str( lit[1] ) + ") in the fight")

    elif name == "hp_check":
      return (True, "HP% <= " + param_strs[0])

    return (False, None)
   
  return format_function 

def decompile_ai_main():
  global show_alerts

  # Parse the arguments
  args = parseArguments()
  show_alerts = not args.hide_alerts

  set_game_specific_values(args.game)

  # disassemble the AI script file
  flow = Flow_File(args.input_file)

  output = ""
  # decompile the AI disassembly
  basic_blocks, proc_info, special_labels =  abstract_flow(flow)

  #output += "\n".join(map(str, proc_info)) + "\n\n"
  #output +=  "\n\n".join(map(str, basic_blocks))
  #print output
    
  tree = ABST(basic_blocks, proc_info, special_labels, args.handwritten)
  #print str( tree )

  if args.fully_optimize:
    tree.optimize_abst()
  else:
    tree.optimize_abst(args.flatten_conditionals, args.flatten_elses, args.constant_folding, args.simplify_conditions)

  output += tree.display_decompilation() + "\n\n"

  if args.show_output:
    print(output)

  # Write result to a file
  with open(args.output_file, "w") as f:
    f.write(output)

if __name__ == '__main__':
  decompile_ai_main()
