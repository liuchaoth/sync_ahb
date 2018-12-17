(message "emacs script for verilog-indent")
;;(find-file "d:/verilog/1.v")
(find-file (nth 3 command-line-args))
;; (mark-whole-buffer) ;;emacs script use command 'mark',is meanless 
;; (electric-verilog-tab)
(verilog-auto)
(verilog-indent-buffer)
(save-buffer)

