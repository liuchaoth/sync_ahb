#!/usr/bin/python

import os

class sync_bus():
    simple_arbiter = 0
    
    masters = ['cm3_ins',
               'cm3_data',
               'cm3_system',
    ]
    slaves = [['sram','0x20000000','0x40000000',"001"],
              ['spic','0x00000000','0x20000000',"000"],
              ['apb' ,'0x40000000','0x60000000',"010"],
              
    ]
    master_signals = [
        ['haddr'       ,'32' ,'in' ,"buff"],
        ['hburst'      ,'3'  ,'in' ,"buff"],
        ['hmasterlock' ,'1'  ,'in' ,"buff"],
        ['hprot'       ,'4'  ,'in' ,"buff"],
        ['hsize'       ,'3'  ,'in' ,"buff"],
        ['htrans'      ,'2'  ,'in' ,"buff"],
        ['hwdata'      ,'32' ,'in' ,""],
        ['hwrite'      ,'1'  ,'in' ,"buff"],
        ['hrdata'      ,'32' ,'out',""],
        ['hready'      ,'1'  ,'out',""],
        ['hresp'       ,'2'  ,'out',""],
                             ]
    slave_signals = [
        ['haddr'       ,'32' ,'out'],
        ['hburst'      ,'3'  ,'out'],
        ['hmasterlock' ,'1'  ,'out'],
        ['hprot'       ,'4'  ,'out'],
        ['hsize'       ,'3'  ,'out'],
        ['htrans'      ,'2'  ,'out'],
        ['hwdata'      ,'32' ,'out'],
        ['hwrite'      ,'1'  ,'out'],
        ['hrdata'      ,'32' ,'in'],
        ['hready'      ,'1'  ,'in'],
        ['hresp'       ,'2'  ,'in'],
    ]
    mux_template = '''
    always@*
    begin:b_%s_%s
    case(%s_grant)
    %s
    endcase
    end
    '''
    cnt_template = '''
    always@(posedge clk or negedge rst_n)
    if(!rst_n)
    M0_cnt <= 4'hf;
    else if((M0_htrans == TRANS_NONSEQ) & M0_hready)
    M0_cnt <= (M0_hburst == BURST_INCR4) ? 4'd3 :
              (M0_hburst == BURST_INCR8) ? 4'd7 :
              (M0_hburst == BURST_INCR16) ? 4'd15 :
               4'd0;
    else if ((M0_htrans == TRANS_SEQ) & M0_hready)
       M0_cnt <= M0_cnt - 1'b1;
    '''
    last_template = '''assign M0_last = (M0_cnt == 'd1) | ((M0_htrans == TRANS_NONSEQ) & M0_hready & (M0_hburst == BURST_SINGLE));
   '''
    buf_template = '''
    always@(posedge clk or negedge rst_n)
    if(!rst_n)
    M0_signal_d <= 'b0;
    else if((M0_htrans != IDLE) & ~M0_grant)
    M0_signal_d <= M0_signal;
    else if(M0_last)

    '''
    
    def __init__(self):
        self.slave_grant_width = len(self.masters)
        self.master_grant_width = len(self.slaves)
    def do_gen_bus(self):
        f = open("bus.v","w")
        f.write("module bus(/*AUTOARG*/);\n")
        f.write('''input clk;
        input rst_n;
        ''')
        # add inouts
        f.write(self.add_ports())
        # add parameters
        f.write('''parameter                  TRANS_IDLE   = 2'b00;
        parameter                  TRANS_BUSY   = 2'b01;
        parameter                  TRANS_NONSEQ = 2'b10;
        parameter                  TRANS_SEQ    = 2'b11;
        
        parameter                  BURST_SINGLE = 3'b000;
        parameter                  BURST_INCR4  = 3'b011;
        parameter                  BURST_INCR8  = 3'b101;
        parameter                  BURST_INCR16 = 3'b111;
        '''
        )
        # add reg and wire
        f.write(self.add_wires_and_regs())
        f.write(self.add_cnt_logic())
        # add master mux
        for m in self.masters:
            for s in self.master_signals:
                if s[2] == 'out':
                    f.write(self.add_master_mux(m,s[0]))
        # add slave mux
        for s in self.slaves:
            for m in self.slave_signals:
                if m[2] == 'out':
                    f.write(self.add_slave_mux(s[0],m[0]))
        # add arbiter
        f.write(self.add_arbiter())
                    
        f.write("endmodule")
        f.close()
        
    def add_master_mux(self,master_name,signal):
        ret = ''
        tmp = ''
        cnt = 1
        
        
        for s in self.slaves:
            tmp += "%d'd%d: %s_%s = %s_%s;\n"%(self.master_grant_width,cnt,
                                               master_name,signal,
                                               s[0],signal)
            cnt = cnt << 1
        tmp += "default:%s_%s = 'b0;"%(master_name,signal)
        ret += self.mux_template%(master_name,signal,master_name,tmp)
        return ret
    def add_slave_mux(self,slave_name,signal):
        ret = ''
        tmp = ''
        cnt = 1
        
        
        for m in self.masters:
            tmp += "%d'd%d: %s_%s = %s_%s;\n"%(self.slave_grant_width,cnt,
                                               slave_name,signal,
                                               m,signal)
            cnt = cnt << 1
        tmp += "default:%s_%s = 'b0;"%(slave_name,signal)
        ret += self.mux_template%(slave_name,signal,slave_name,tmp)
        return ret

    
    def add_ports(self):
        ret = ''
        for m in self.masters:
            ret += "\n// MASTER %s interface\n"%m
            for s in self.master_signals:
                if s[1] == '1':
                    ret += "%sput %s_%s;\n"%(s[2],m,s[0])
                else:
                    ret += "%sput [%d:0] %s_%s;\n"%(s[2],int(s[1]) - 1, m,s[0])
        for m in self.slaves:
            ret += "\n// SLAVE %s interface\n"%m[0]
            for s in self.slave_signals:
                if s[1] == '1':
                    ret += "%sput %s_%s;\n"%(s[2],m[0],s[0])
                else:
                    ret += "%sput [%d:0] %s_%s;\n"%(s[2],int(s[1]) - 1, m[0],s[0])
        
        return ret

    def add_wires_and_regs(self):
        ret = ''
        # sel
        ret += "\n// sel\n"
        for m in self.masters:
            for s in self.slaves:
                ret += "wire  %s_%s_sel = (%s_haddr_d[31:29] == 3'b%s);\n"%(m,s[0],m,s[3])

        ret += "\n// master requests\n"
        for m in self.masters:
            ret += "wire %s_request;\n"%m
        for m in self.masters:
            ret += "\n// MASTER %s interface\n"%m
            for s in self.master_signals:
                if s[2] == "out":
                    if s[1] == '1':
                        ret += "reg %s_%s;\n"%(m,s[0])
                    else:
                        ret += "reg [%d:0] %s_%s;\n"%(int(s[1]) - 1, m,s[0])
        for m in self.slaves:
            ret += "\n// SLAVE %s interface\n"%m[0]
            for s in self.slave_signals:
                if s[2] == "out":
                    if s[1] == '1':
                        ret += "reg %s_%s;\n"%(m[0],s[0])
                    else:
                        ret += "reg [%d:0] %s_%s;\n"%(int(s[1]) - 1, m[0],s[0])
                    
        ret += '\n// MASTER buffers\n'
        for m in self.masters:
            ret += '\n// %s\n'%m
            for s in self.master_signals:
                if s[3] == "buff":
                    if s[1] != "1":
                        ret += "reg [%d:0] "%int(s[1])
                    else:
                        ret += "reg "
                    ret += "_".join((m,s[0],"d"))
                    ret += ";\n"
                    
        ret += '\n// REQ and GRANT WIRES\n'
        for m in self.masters:
            ret += "wire [%d:0] %s_grant;\n"%(len(self.slaves),m)
        for s in self.slaves:
            ret += "wire [%d:0] %s_grant;\n"%(len(self.masters),s[0])
            
        ret += '\n'
        for i in range(len(self.slaves)):
            ret += "wire [7:0] arbiter_%d_request;\n"%i
            ret += "wire [7:0] arbiter_%d_grant;\n"%i
            ret += "assign arbiter_%d_request[7:%d] = 'b0;\n"%(i,len(self.masters))
            for j in range(len(self.masters)):
                ret += "assign arbiter_%d_request[%d] = %s_request & %s_%s_sel;\n"%(i,j,self.masters[j],self.masters[j],self.slaves[i][0])
            ret += "\n"
        for j in range(len(self.masters)):
            tmp = []
            for k in range(len(self.slaves)):
                tmp.append("arbiter_%d_grant[%d]"%(len(self.slaves) - k - 1,j))
            ret += "assign %s_grant = {%s};\n"%(self.masters[j],",".join(tmp))
                
        for j in range(len(self.slaves)):
            ret += "assign %s_grant = {arbiter_%d_grant[%d:0]};\n"%(self.slaves[j][0],j,len(self.masters) - 1)
            
            
        # cnt
        ret += '\n// count and last\n'
        for m in self.masters:
            ret += "reg [3:0] %s_cnt;\n"%(m)
        
        # last
        
        for m in self.masters:
            ret += "wire  %s_last;\n"%(m)
        
          
        

            
        return ret


    def add_cnt_logic(self):
        ret = ''
        ret += '\n// count and last\n'
        for m in self.masters:
            ret += self.cnt_template.replace("M0",m)
        for m in self.masters:
            ret += self.last_template.replace("M0",m)

            
        return ret

    def add_arbiter(self):
        ret = ''
        ret += '\n// add arbiter\n'
        if self.simple_arbiter:
            ret += '''
            
            '''
            
        else:
            for i in range(len(self.slaves)):
                ret += '''
                arbiter arbiter_N(
                .clk       (clk),
                .rst_n     (rst_n),
                .grant     (arbiter_N_grant),
                .request   (arbiter_N_request),
                .trans_done(arbiter_N_trans_done)
                );
                '''.replace("N",str(i))
        return ret
if __name__ == '__main__':

    bus = sync_bus()
    bus.do_gen_bus()
    
    batch = 'emacs -Q --batch bus.v --script auto.el'
    os.system(batch)
