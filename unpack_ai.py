#!/usr/bin/python
# coding: utf-8

# Contains functionality for unpacking EO ai scripts
# if run from the command line, will take an ai script file
# and print the parsed file into the output file
#
# written by TheOnlyOne (@modest_ralts)
# with credit to https://amicitia.miraheze.org/wiki/BF for the file format
# and https://github.com/ThatOneStruggle/RMDEditor-master/blob/master/RMDEditor/FLW0/Flw0.cs for more details

import argparse
from struct import pack, unpack
from sys import stderr
from shared_helpers import *

def eprint(s):
    stderr.write(s + "\n")

def parseArguments():
    # Create argument parser
    parser = argparse.ArgumentParser(description="Parses an Etrian Odyssey AI file (.bf, or something with the FLW0 tag.)")

    # Positional mandatory arguments
    parser.add_argument("input_file", help="name of the file containing the raw flw0 data")
    parser.add_argument("output_file", help="name of the file in which to place the output") 

    # Optional arguments
    parser.add_argument("--show_output", action="store_true", help="output will be printed to console in addition to being saved to the output_file")
    parser.add_argument("--hide_alerts", action="store_true", help="warnings will not be printed to stderr if unexpected values are encountered")
    parser.add_argument("--no_dce", action="store_true", help="dead code elimination will not be performed")

    # Print version
    parser.add_argument("--version", action="version", version='%(prog)s - Version 1.0')

    # Parse arguments
    args = parser.parse_args()

    return args

show_alerts = True
dead_code_elimination = True

# class that contains the data in the flow file
class Flow_Header():

    # data should be 0x20 = 32 bytes
    def __init__(self, data):
        unpacked = unpack("<BBH4IH10B", data)
        self.file_type = unpacked[0]
        self.compresion_flag = unpacked[1]
        self.user_id = unpacked[2]
        self.size = unpacked[3]
        self.tag = unpacked[4]
        self.mem_size = unpacked[5]
        self.num_sections = unpacked[6]
        self.storage_space = unpacked[7]
        self.pad = []
        for idx in range(8, 18):
            self.pad.append(unpacked[idx])

        # test to see if there are any unexpected values
        if show_alerts:
            expected = {
                "file_type" : 0,
                "compresion_flag" : 0,
                "user_id" : 0,
                "tag" : 0x30574C46,
                "num_sections" : 5,
            }
            for name, val in expected.items():
                our_val = self.__dict__[name]
                if our_val != val:
                    eprint( name + " is not " + "{:#04x}".format(val) + "! It is: " + "{:#04x}".format(our_val) )
            for p in self.pad:
                if p != 0:
                    eprint( "found non-zero pading: " + "{:#04x}".format(p) )

# class that contains the data for a section's header in the flow file
class Flow_Section_Header():
    
    # data should be 0x10 = 16 bytes
    def __init__(self, data):
        unpacked = unpack("<4I", data)
        self.id = unpacked[0]
        self.entry_size = unpacked[1]
        self.num_entries = unpacked[2]
        self.offset = unpacked[3]

# class that contains the list of entries in a single flow section
class Flow_Section():
    
    # data should be the full flow file
    # header should be a Flow_Section_Header
    def __init__(self, data, header):
        self.header = header
        self.entries = []
        for idx in range(0, header.num_entries):
            base = header.offset + (header.entry_size * idx)
            self.entries.append( data[base : base + header.entry_size] )

# class that contains the data for a jump label
class Flow_Label():
    
    # data should be 0x20 = 32 bytes
    # index is the index used in a jump instruction
    def __init__(self, data, index, kind):
        unpacked = unpack("<24B2I", data)
        self.name = ""
        for idx in range(0, 24):
            if unpacked[idx] == 0:
                break
            self.name += chr(unpacked[idx])
        self.loc = unpacked[24]
        self.pad = unpacked[25]
        self.index = index
        self.kind = kind

# map from opcode to instruction name
instruction_names = {
    0x00 : "PUSHI",
    0x01 : "PUSHF",
    0x02 : "PUSHIX",
    0x03 : "PUSHIF",
    0x04 : "PUSHREG",
    0x05 : "POPIX",
    0x06 : "POPFX",
    0x07 : "PROC",
    0x08 : "COMM",
    0x09 : "END",
    0x0A : "JUMP",
    0x0B : "CALL",
    0x0C : "RUN",
    0x0D : "GOTO",
    0x0E : "ADD",
    0x0F : "SUB",
    0x10 : "MUL",
    0x11 : "DIV",
    0x12 : "MINUS",
    0x13 : "NOT",
    0x14 : "OR",
    0x15 : "AND",
    0x16 : "EQ",
    0x17 : "NEQ",
    0x18 : "LT",
    0x19 : "GT",
    0x1A : "LTE",
    0x1B : "GTE",
    0x1C : "IF",
    0x1D : "PUSHIS",
    0x1E : "PUSHLIX",
    0x1F : "PUSHLFX",
    0x20 : "POPLIX",
    0x21 : "POPLFX",
    0x22 : "PUSHSTR", 
}

# list of instructions that use up 8 total bytes instead of 4
wide_instrs = [0x00, 0x01, 0x02, 0x03]

# list of instructions that use a float for the operand
float_operands = [0x01, 0x03]

# list of opcodes that can jump, and thus should have their operand replaced with a label
jumpers = [0x0D, 0x1C]

# list of opcodes that can call a procedure, and thus should have their operand replaced with a label
callers = [0x0A, 0x0B]

# list of opcodes that have use no operands, and thus should have it ommited from display
no_operands = [0x04, 0x05, 0x06, 0x09, 0x0C, 0x0E, 0x0F, 0x10, 0x11, 0x12, 0x13, 0x14,
               0x15, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x1B]

# class that contains an instruction entry in the script 
class Flow_Instruction():

    # return a string displaying the instruction
    def display(self, proc_labels, jump_labels):
        loc_str = str(self.loc)

        raw_instr_str = ""
        opcode_name = instruction_names[self.opcode]
        operand_name = ""
        if not self.wide:
            opcode_str = "{:04x}".format(self.opcode)
            opcode_str = opcode_str[2:4] + opcode_str[0:2]
            operand_str = "{:04x}".format(self.operand)
            operand_str = operand_str[2:4] + operand_str[0:2]
            raw_inst_str = opcode_str + " " + operand_str
            operand_name = "{:#06x}".format(self.operand)
        else:
            opcode_str = "{:08x}".format(self.opcode)
            opcode_str = opcode_str[6:8] + opcode_str[4:6] + " " + opcode_str[2:4] + opcode_str[0:2]
            operand_str = ""
            if self.floating:
                f_str = pack("<f", self.operand)
                operand_str = "{:08x}".format( unpack("<i", f_str)[0] )
                operand_name = str(self.operand)
            else:
                operand_str = "{:08x}".format(self.operand)
                operand_name = "{:#010x}".format(self.operand)
            operand_str = operand_str[6:8] + operand_str[4:6] + " " + operand_str[2:4] + operand_str[0:2]
            raw_inst_str = opcode_str + "\n\t" + operand_str

        # if it's a caller, replace the operand with the appropriate label
        if self.opcode in callers:
            label = proc_labels[self.operand]
            operand_name = label.name + " (loc " + str(label.loc) + ")"
        # if it's a jumper, replace the operand with the appropriate label
        if self.opcode in jumpers:
            label = jump_labels[self.operand]
            operand_name = label.name + " (loc " + str(label.loc) + ")"
        # if it does not use an operand, ommit it
        if self.opcode in no_operands:
            if show_alerts and self.operand != 0:
                eprint( "Found a " + opcode_name + " with a non-zero operand: " + operand_name )
            operand_name = ""
        readable_inst = " ".join( ["#", opcode_name, operand_name] )

        return "\t".join( [loc_str, raw_inst_str, readable_inst] )

    # data should be 0x04 = 4 bytes
    # loc is the index of this instruction in the instruction list
    # wide instructions are 8 bytes
    def __init__(self, data, loc, wide=False, floating=False):
        formater = "<2h"
        if wide:
            if floating:
                formater = "<If"
            else:
                formater = "<2I"
        self.opcode, self.operand = unpack(formater, data)
        self.loc = loc
        self.wide = wide
        self.floating = floating

# a flow block contains a label and list of instructions
class Flow_Block():

    # return a string displaying the full flow block
    def display(self, proc_labels, jump_labels):
        instr_strs = []
        for instr in self.instructions:
            instr_strs.append( instr.display(proc_labels, jump_labels) )
        return "\n".join( ["label: " + self.name] + instr_strs )

    # eliminate dead instructions (those after an END or unconditional jump)
    def eliminate_dead_instructions(self):
        block_enders = [0x09, 0x0A, 0x0D]  # END, JUMP, GOTO
        live_instrs = []
        for instr in self.instructions:
            live_instrs.append(instr)
            if instr.opcode in block_enders:
                break
        self.instructions = live_instrs
    
    # label is the label that starts this block
    # instructions should be a slice of the full instruction list
    def __init__(self, label, instructions, procedure_id, next_label):
        self.name = label.name
        self.start = label.loc
        self.label_index = label.index
        self.label_kind = label.kind
        self.instructions = list(filter(lambda i : i is not None, instructions))
        self.procedure_id = procedure_id

        # guess special labels based on their name
        # (this is risky, but seems to be okay so far)
        if label.kind == "jump" and label.name[0] != "_":
          self.label_kind = "special"

        empty_block = len(self.instructions) == 0
        no_fallthrough = empty_block
        if not empty_block:
          no_fallthrough = not (self.instructions[-1].opcode in (jumpers + [0x09, 0x0A]))

        # make falling through to the next block explicit
        if no_fallthrough:
            if next_label is None:
                if show_alerts:
                    eprint("Final block does not end in an IF, JUMP, GOTO, or END, or is empty.")
            instr_data = '\x0d\x00' + pack("<H", next_label.index)
            goto_instr = Flow_Instruction(instr_data, -1)
            self.instructions.append(goto_instr)

# block flow graph for a single procedure
class Flow_Block_Graph():
    
    # construct the graph as a list of out edges
    # uses a flow file's flow block list
    def __init__(self, flow_blocks, labels):
        self.has_cycles = False

        # get the out edges for a single block and return it
        def get_out_edges(block):
            outs = []
            for instr in block.instructions:
                if instr.opcode in jumpers:
                    if instr.operand not in outs:
                        outs.append(instr.operand)
            return set(outs)

        # having only one block is an easy special case
        if len(flow_blocks) == 1:
            self.start_outs = set([])
            self.other_outs = {}
            self.reachable = {}
            return
        # set the edges for the procedure start block
        self.start_outs = get_out_edges( flow_blocks[0] )
        # set the edges for the remaining blocks
        self.other_outs = {}
        for block in flow_blocks[1:]:
            self.other_outs[block.label_index] = get_out_edges(block)

        # compute the reachable blocks, and detect any directed cycles
        self.reachable = dict((i, False) for (i, _) in self.other_outs.items())
        reachable_queue = []
        preds = dict((i, []) for (i, _) in self.other_outs.items()) 
        # pushes new reachable blocks to the stack and marks them as reachable
        # returns True if no new blocks were pushed
        def push_new_reachables(outs, pre):
            for block_index in outs:
                if self.reachable[block_index]:
                    if block_index in pre:
                        labels_in_cycle = []
                        for idx in (pre + [block_index]):
                            labels_in_cycle.append( labels[idx].name )
                        #eprint("Cycle detected in block flow graph! " + "->".join(labels_in_cycle) )
                        labels_in_cycle.append( labels_in_cycle[0] )
                        self.has_cycles = True
                else:
                    self.reachable[block_index] = True
                    preds[block_index] = pre + [block_index]
                    reachable_queue.append( block_index )
        depth = 0
        push_new_reachables(self.start_outs, [])
        while reachable_queue:
            cur_block = reachable_queue.pop(0)
            push_new_reachables( self.other_outs[ cur_block ], preds[cur_block] )
            

        

# a full flow file
class Flow_File():

    # displays the disassembled instructions
    def display_disassembly(self):
        output = "Number of allocated storage spaces: " + str(self.header.storage_space) + "\n\n"
        displayed_blocks = []
        for block in flatten(self.flow_blocks):
            if block.label_kind == "proc" or not dead_code_elimination or self.block_graphs[block.procedure_id].reachable[block.label_index]:
                displayed_blocks.append( block.display(self.proc_labels, self.jump_labels) )
            first = False
        return output + "\n\n".join(displayed_blocks)
            

    # data will contain the full file
    def __init__(self, filename):
        #read the file
        data = ""
        with open(filename, "rb") as f:
            data = f.read()
        
        # get the file's header
        self.header = Flow_Header( data[0x00 : 0x20] )

        # get the file's sections
        self.sections = []
        for idx in range(0, self.header.num_sections):
            base = 0x20 + 0x10 * idx
            section_header = Flow_Section_Header( data[base : base + 0x10] )
            self.sections.append( Flow_Section(data, section_header) )

        # handle the individual sections

        # returns a list of parsed Flow_Labels assuming a section is a list of them
        def parse_label_section(sec_idx, kind):
            sec = self.sections[sec_idx]
            labels = []
            for idx in range(0, sec.header.num_entries):
                labels.append( Flow_Label(sec.entries[idx], idx, kind) )
            return labels

        # Section 0: Procedure Labels
        self.proc_labels = parse_label_section(0, "proc")
        
        # Section 1: Jump Labels
        self.jump_labels = parse_label_section(1, "jump")

        # Section 2: Instructions
        sec = self.sections[2]
        instrs = []
        skip = False
        for idx in range(0, sec.header.num_entries):
            if skip:
                skip = False
                # Pad
                instrs.append( None )
                continue
            oper = unpack("<I", sec.entries[idx])[0]
            if oper in wide_instrs:
                skip = True
                floating = oper in float_operands
                instrs.append( Flow_Instruction(sec.entries[idx] + sec.entries[idx+1], idx, True, floating) )
            else:
                instrs.append( Flow_Instruction(sec.entries[idx], idx) )
        self.instructions = instrs
        #print "\n".join(map( lambda i : i.display(self.proc_labels, self.jump_labels), filter(lambda i : i is not None, instrs)))

        if show_alerts:
            # Section 3: Expected to be empty
            if self.sections[3].header.num_entries > 0:
                eprint("Section 3 is not empty!")
            
            # Section 4: Expected to be 0 padding
            sec = self.sections[4]
            for pad in sec.entries:
                if pad != b'\x00':
                    eprint("Section 4 has non-zero padding: " + str(pad))

        
        # break the instructions up into flow blocks using the given labels
        all_labels = self.proc_labels + self.jump_labels
        def get_loc(label):
            return label.loc
        all_labels.sort(key=get_loc)
        end_points = ( list(map(get_loc, all_labels[1:])) + [len(self.instructions)] )
        self.flow_blocks = [[] for _ in self.proc_labels]
        cur_procedure = -1
        next_labels = all_labels[1:] + [None]
        for label, end, next_l in zip(all_labels, end_points, next_labels):
            if label.kind == "proc":
                cur_procedure += 1
            block = Flow_Block( label, self.instructions[label.loc : end], cur_procedure, next_l )
            self.flow_blocks[cur_procedure].append(block)

        # dead instruction elimination pass for each block (flattened flow_blocks list)
        if dead_code_elimination:
            for block in flatten(self.flow_blocks):
                block.eliminate_dead_instructions()

        # construct a flow graph for the flow blocks of each procedure
        self.block_graphs = []
        for proc_blocks in self.flow_blocks:
            self.block_graphs.append( Flow_Block_Graph(proc_blocks, self.jump_labels) )

def unpack_ai_main():
    global show_alerts
    global dead_code_elimination

    # Parse the arguments
    args = parseArguments()
    show_alerts = not args.hide_alerts
    dead_code_elimination = not args.no_dce

    # Build the table from the given file
    # tbl = EO_name_table()
    # tbl.build_from_file(args.input_file, args.index_width, not args.hide_alerts)

    # parse the AI script file
    flow = Flow_File(args.input_file)

    output = ""
    output += flow.display_disassembly()

    if args.show_output:
        print(output)

    # Write result to a file
    with open(args.output_file, "w") as f:
        f.write(output)

if __name__ == '__main__':
    unpack_ai_main()
