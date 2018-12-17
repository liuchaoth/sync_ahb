#!/usr/bin/python

import os

class sync_bus():
    masters = ['cm3_ins',
               'cm3_data',
               'cm3_system',
    ]
    slaves = [['sram','0x20000000','0x21000000',],
              ['spic','0x01000000','0x02000000',],
              ['apb_bridge','0x40000000','0x41000000',],
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
        ['hsel'        ,'1'  ,'out'],
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
    
    def __init__(self):
        self.slave_grant_width = len(self.masters)
        self.master_grant_width = len(self.slaves)
    def do_gen_bus(self):
        f = open("bus.v","w")
        f.write("module bus(/*AUTOARG*/);\n")
        
        # add inouts
        f.write(self.add_ports())
        # add reg and wire
        f.write(self.add_wires_and_regs())
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
        ret = '\n// MASTER buffers\n'
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
                ret += "assign arbiter_%d_request[%d] = %s_request;\n"%(i,j,self.masters[j])
            ret += "\n"
        for j in range(len(self.masters)):
            tmp = []
            for k in range(len(self.slaves)):
                tmp.append("arbiter_%d_grant[%d]"%(len(self.slaves) - k - 1,j))
            ret += "assign %s_grant = {%s};\n"%(self.masters[j],",".join(tmp))
                
        for j in range(len(self.slaves)):
            ret += "assign %s_grant = {arbiter_%d_grant[%d:0]};\n"%(self.slaves[j][0],j,len(self.masters) - 1)
            
            
            
          
        
            

            
        return ret
    
        
    
if __name__ == '__main__':

    bus = sync_bus()
    bus.do_gen_bus()
    
    batch = 'emacs -Q --batch bus.v --script auto.el'
    os.system(batch)
