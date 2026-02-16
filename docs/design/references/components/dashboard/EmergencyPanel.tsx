
import React, { useState, useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  AlertTriangle, X, ShieldAlert, Power, Pause, Play, 
  Trash2, AlertOctagon, Check, Lock, ChevronDown, ChevronUp,
  Search, Zap, Hand, CheckSquare, Square, History, Terminal
} from 'lucide-react';
import { cn, formatCurrency } from '../../lib/utils';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { useToast } from '../../contexts/ToastContext';

interface EmergencyPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

// --- Mock Data ---

const mockOpenPositions = [
  { id: '1', symbol: 'NVDA', agent: 'Alpha Seeker', side: 'Long', qty: 450, entry: 840.20, mark: 890.25, pnl: 22522.50 },
  { id: '2', symbol: 'BTC', agent: 'Momentum Prime', side: 'Long', qty: 2.5, entry: 64200, mark: 67500, pnl: 8250.00 },
  { id: '3', symbol: 'TSLA', agent: 'Macro Sentinel', side: 'Short', qty: 300, entry: 185.00, mark: 175.40, pnl: 2880.00 },
  { id: '4', symbol: 'ETH', agent: 'Momentum Prime', side: 'Long', qty: 15, entry: 3950, mark: 3850, pnl: -1500.00 },
  { id: '5', symbol: 'AMD', agent: 'Alpha Seeker', side: 'Long', qty: 1000, entry: 195.50, mark: 180.40, pnl: -15100.00 },
  { id: '6', symbol: 'SPY', agent: 'Macro Sentinel', side: 'Long', qty: 200, entry: 505.00, mark: 512.30, pnl: 1460.00 },
  { id: '7', symbol: 'MSFT', agent: 'Alpha Seeker', side: 'Long', qty: 500, entry: 410.00, mark: 425.50, pnl: 7750.00 },
  { id: '8', symbol: 'COIN', agent: 'Momentum Prime', side: 'Short', qty: 200, entry: 260.00, mark: 245.00, pnl: 3000.00 },
  { id: '9', symbol: 'MSTR', agent: 'Alpha Seeker', side: 'Long', qty: 10, entry: 1200.00, mark: 1450.00, pnl: 2500.00 },
  { id: '10', symbol: 'GOOGL', agent: 'Macro Sentinel', side: 'Long', qty: 400, entry: 140.00, mark: 142.50, pnl: 1000.00 },
  { id: '11', symbol: 'AMZN', agent: 'Alpha Seeker', side: 'Short', qty: 300, entry: 180.00, mark: 178.00, pnl: 600.00 },
  { id: '12', symbol: 'PLTR', agent: 'Momentum Prime', side: 'Long', qty: 2000, entry: 22.50, mark: 24.00, pnl: 3000.00 },
];

const mockRecentActions = [
  { id: '1', time: '10:42:15', action: 'Closed NVDA x500', reason: 'Breaking News', user: 'Alexander V.' },
  { id: '2', time: '09:15:30', action: 'Paused Momentum Prime', reason: 'Risk Override', user: 'Alexander V.' },
  { id: '3', time: 'Yesterday', action: 'Halted Trading', reason: 'API Failure', user: 'System Admin' },
];

export const EmergencyPanel: React.FC<EmergencyPanelProps> = ({ isOpen, onClose }) => {
  const { toast } = useToast();
  const [mounted, setMounted] = useState(false);
  const [currentTime, setCurrentTime] = useState(new Date());
  
  // Confirm Modal State
  const [confirmationAction, setConfirmationAction] = useState<{ id: string, label: string, type: 'danger' | 'warning' | 'neutral' } | null>(null);
  const [confirmationInput, setConfirmationInput] = useState('');

  // Position Selection
  const [selectedPositionIds, setSelectedPositionIds] = useState<Set<string>>(new Set());
  
  // Override Form
  const [overrideCollapsed, setOverrideCollapsed] = useState(true);
  const [overrideForm, setOverrideForm] = useState({
    symbol: '',
    side: 'BUY',
    qty: '',
    reason: 'Risk Override'
  });

  // Timer
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  // -- Calculated --
  const totalExposure = mockOpenPositions.reduce((acc, p) => acc + (p.mark * p.qty), 0);
  const allSelected = selectedPositionIds.size === mockOpenPositions.length;

  // -- Handlers --

  const handleSelectAll = () => {
    if (allSelected) {
      setSelectedPositionIds(new Set());
    } else {
      setSelectedPositionIds(new Set(mockOpenPositions.map(p => p.id)));
    }
  };

  const toggleSelection = (id: string) => {
    const newSet = new Set(selectedPositionIds);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setSelectedPositionIds(newSet);
  };

  const initiateAction = (id: string, label: string, type: 'danger' | 'warning' | 'neutral') => {
    setConfirmationAction({ id, label, type });
    setConfirmationInput('');
  };

  const executeConfirmedAction = () => {
    if (!confirmationAction) return;
    
    // Simulate Action Execution
    toast({
      title: 'Emergency Action Executed',
      description: `${confirmationAction.label} was successfully processed.`,
      type: confirmationAction.type === 'danger' ? 'error' : confirmationAction.type === 'warning' ? 'warning' : 'success'
    });

    setConfirmationAction(null);
    setConfirmationInput('');
  };

  const handleOverrideSubmit = () => {
    if (!overrideForm.symbol || !overrideForm.qty) return;
    initiateAction(
      'MANUAL_OVERRIDE', 
      `EXECUTE ${overrideForm.side} ${overrideForm.qty} ${overrideForm.symbol}`, 
      'warning'
    );
  };

  if (!mounted) return null;

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex justify-end font-sans text-white">
          
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/90 backdrop-blur-sm"
          />

          {/* Drawer Panel */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            className="relative w-full max-w-[600px] h-full bg-[#09090b] border-l border-red-500/20 shadow-[0_0_100px_rgba(220,38,38,0.15)] flex flex-col"
          >
            {/* Top Border */}
            <div className="h-1.5 w-full bg-gradient-to-r from-red-600 via-orange-500 to-red-600 animate-pulse" />

            {/* Header */}
            <div className="flex items-center justify-between px-6 py-5 border-b border-white/10 bg-[#09090b]">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded bg-red-500/10 text-red-500">
                  <ShieldAlert className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-3">
                    EMERGENCY CONTROLS
                  </h2>
                  <div className="flex items-center gap-2 mt-1">
                     <span className="relative flex h-2.5 w-2.5">
                       <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-500 opacity-75"></span>
                       <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
                     </span>
                     <span className="text-xs font-bold text-red-500 tracking-wider">LIVE TRADING ACTIVE</span>
                  </div>
                </div>
              </div>
              <button 
                onClick={onClose} 
                className="p-2 hover:bg-white/10 rounded-full transition-colors text-white/50 hover:text-white"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto custom-scrollbar">
              <div className="p-6 space-y-8">
              
                {/* SECTION 1: QUICK ACTIONS */}
                <div className="grid grid-cols-2 gap-4">
                   <button
                     onClick={() => initiateAction('HALT', 'HALT ALL TRADING', 'danger')}
                     className="group relative h-28 rounded-xl bg-red-950/30 border border-red-900/50 hover:bg-red-900/20 hover:border-red-500 transition-all flex flex-col items-center justify-center gap-2"
                   >
                      <AlertOctagon className="w-8 h-8 text-red-500 group-hover:scale-110 transition-transform" />
                      <span className="text-sm font-bold text-red-500 tracking-wider">HALT TRADING</span>
                      <div className="absolute inset-0 bg-red-500/5 opacity-0 group-hover:opacity-100 transition-opacity rounded-xl" />
                   </button>

                   <button
                     onClick={() => initiateAction('CLOSE_ALL', 'CLOSE ALL POSITIONS', 'danger')}
                     className="group relative h-28 rounded-xl bg-orange-950/30 border border-orange-900/50 hover:bg-orange-900/20 hover:border-orange-500 transition-all flex flex-col items-center justify-center gap-2"
                   >
                      <Trash2 className="w-8 h-8 text-orange-500 group-hover:scale-110 transition-transform" />
                      <span className="text-sm font-bold text-orange-500 tracking-wider">CLOSE ALL</span>
                   </button>

                   <button
                     onClick={() => initiateAction('PAUSE_AGENTS', 'PAUSE ALL AGENTS', 'warning')}
                     className="group relative h-24 rounded-xl bg-yellow-950/30 border border-yellow-900/50 hover:bg-yellow-900/20 hover:border-yellow-500 transition-all flex flex-col items-center justify-center gap-2"
                   >
                      <Pause className="w-6 h-6 text-yellow-500" />
                      <span className="text-xs font-bold text-yellow-500 tracking-wider">PAUSE AGENTS</span>
                   </button>

                   <button
                     onClick={() => initiateAction('RESUME', 'RESUME NORMAL OPS', 'neutral')}
                     className="group relative h-24 rounded-xl bg-green-950/30 border border-green-900/50 hover:bg-green-900/20 hover:border-green-500 transition-all flex flex-col items-center justify-center gap-2"
                   >
                      <Play className="w-6 h-6 text-green-500" />
                      <span className="text-xs font-bold text-green-500 tracking-wider">RESUME NORMAL</span>
                   </button>
                </div>

                {/* SECTION 2: OPEN POSITIONS */}
                <div className="space-y-3">
                   <div className="flex items-center justify-between pb-2 border-b border-white/10">
                      <div>
                         <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                            <Zap className="w-4 h-4 text-yellow-500" /> 
                            Open Positions ({mockOpenPositions.length})
                         </h3>
                         <div className="text-[10px] text-white/40 font-mono mt-1">Total Exposure: {formatCurrency(totalExposure)}</div>
                      </div>
                      <div className="flex gap-2">
                         <button 
                           onClick={handleSelectAll}
                           className="px-3 py-1.5 rounded text-[10px] font-bold uppercase tracking-wider bg-white/5 hover:bg-white/10 text-white/70 transition-colors"
                         >
                           {allSelected ? "Deselect All" : "Select All"}
                         </button>
                         <button 
                           disabled={selectedPositionIds.size === 0}
                           onClick={() => initiateAction('CLOSE_SELECTED', `CLOSE ${selectedPositionIds.size} POSITIONS`, 'warning')}
                           className="px-3 py-1.5 rounded text-[10px] font-bold uppercase tracking-wider bg-red-500/10 text-red-500 hover:bg-red-500/20 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                         >
                           Close Selected ({selectedPositionIds.size})
                         </button>
                      </div>
                   </div>

                   <div className="max-h-[300px] overflow-y-auto custom-scrollbar space-y-1 pr-1">
                      {mockOpenPositions.map(pos => {
                         const isSelected = selectedPositionIds.has(pos.id);
                         return (
                           <div 
                             key={pos.id}
                             onClick={() => toggleSelection(pos.id)} 
                             className={cn(
                               "flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-all",
                               isSelected 
                                 ? "bg-white/10 border-white/20" 
                                 : "bg-white/5 border-transparent hover:bg-white/[0.07]"
                             )}
                           >
                              <div className="flex items-center gap-3">
                                 <div className={cn("text-white/50", isSelected && "text-blue-400")}>
                                    {isSelected ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
                                 </div>
                                 <div>
                                    <div className="flex items-center gap-2">
                                       <span className="font-bold text-sm text-white">{pos.symbol}</span>
                                       <Badge variant={pos.side === 'Long' ? 'success' : 'danger'} size="sm" className="h-4 px-1 text-[9px] bg-opacity-20 border-opacity-20">{pos.side}</Badge>
                                    </div>
                                    <div className="text-[10px] text-white/40">{pos.agent}</div>
                                 </div>
                              </div>
                              
                              <div className="flex items-center gap-6">
                                 <div className="text-right hidden sm:block">
                                    <div className="text-[10px] text-white/40 font-mono">QTY: {pos.qty}</div>
                                    <div className="text-[10px] text-white/40 font-mono">{pos.entry} → {pos.mark}</div>
                                 </div>
                                 <div className="text-right w-20">
                                    <div className={cn("text-sm font-mono font-bold", pos.pnl >= 0 ? "text-green-400" : "text-red-400")}>
                                       {pos.pnl >= 0 ? '+' : ''}{formatCurrency(pos.pnl)}
                                    </div>
                                 </div>
                                 <button 
                                   onClick={(e) => { e.stopPropagation(); initiateAction('CLOSE_ONE', `CLOSE ${pos.symbol}`, 'warning'); }}
                                   className="p-1.5 hover:bg-white/10 rounded text-white/30 hover:text-red-400 transition-colors"
                                 >
                                    <X className="w-4 h-4" />
                                 </button>
                              </div>
                           </div>
                         );
                      })}
                   </div>
                </div>

                {/* SECTION 3: MANUAL OVERRIDE */}
                <div className="border border-white/10 rounded-xl bg-white/[0.02] overflow-hidden">
                   <button 
                     onClick={() => setOverrideCollapsed(!overrideCollapsed)}
                     className="w-full flex items-center justify-between p-4 bg-white/5 hover:bg-white/10 transition-colors"
                   >
                      <div className="flex items-center gap-2">
                         <Hand className="w-4 h-4 text-yellow-500" />
                         <h3 className="text-sm font-bold text-white uppercase tracking-wider">Manual Override Order</h3>
                      </div>
                      {overrideCollapsed ? <ChevronDown className="w-4 h-4 text-white/50" /> : <ChevronUp className="w-4 h-4 text-white/50" />}
                   </button>
                   
                   <AnimatePresence>
                      {!overrideCollapsed && (
                         <motion.div 
                           initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }}
                           className="overflow-hidden"
                         >
                            <div className="p-4 border-t border-white/10 space-y-4">
                               <div className="flex items-center gap-2 text-xs font-bold text-red-400 bg-red-500/10 p-2 rounded border border-red-500/20">
                                  <AlertTriangle className="w-4 h-4" />
                                  WARNING: This bypasses all AI risk controls and limits.
                               </div>
                               
                               <div className="grid grid-cols-2 gap-4">
                                  <div className="space-y-1">
                                     <label className="text-[10px] uppercase text-white/40 font-bold">Symbol</label>
                                     <div className="relative">
                                        <Search className="absolute left-3 top-2.5 w-4 h-4 text-white/30" />
                                        <input 
                                          value={overrideForm.symbol}
                                          onChange={e => setOverrideForm({...overrideForm, symbol: e.target.value.toUpperCase()})}
                                          className="w-full bg-black border border-white/10 rounded-lg py-2 pl-9 pr-3 text-sm text-white focus:outline-none focus:border-yellow-500 uppercase placeholder:text-white/20"
                                          placeholder="TICKER"
                                        />
                                     </div>
                                  </div>
                                  <div className="space-y-1">
                                     <label className="text-[10px] uppercase text-white/40 font-bold">Quantity</label>
                                     <input 
                                        type="number"
                                        value={overrideForm.qty}
                                        onChange={e => setOverrideForm({...overrideForm, qty: e.target.value})}
                                        className="w-full bg-black border border-white/10 rounded-lg py-2 px-3 text-sm text-white focus:outline-none focus:border-yellow-500 placeholder:text-white/20"
                                        placeholder="0.00"
                                     />
                                  </div>
                               </div>

                               <div className="grid grid-cols-2 gap-4">
                                  <div className="flex bg-black rounded-lg p-1 border border-white/10">
                                     <button 
                                       onClick={() => setOverrideForm({...overrideForm, side: 'BUY'})}
                                       className={cn("flex-1 py-1.5 rounded text-xs font-bold transition-colors", overrideForm.side === 'BUY' ? "bg-green-600 text-white" : "text-white/40 hover:text-white")}
                                     >
                                       BUY
                                     </button>
                                     <button 
                                       onClick={() => setOverrideForm({...overrideForm, side: 'SELL'})}
                                       className={cn("flex-1 py-1.5 rounded text-xs font-bold transition-colors", overrideForm.side === 'SELL' ? "bg-red-600 text-white" : "text-white/40 hover:text-white")}
                                     >
                                       SELL
                                     </button>
                                  </div>
                                  
                                  <select 
                                    value={overrideForm.reason}
                                    onChange={e => setOverrideForm({...overrideForm, reason: e.target.value})}
                                    className="bg-black border border-white/10 rounded-lg px-3 text-xs text-white focus:outline-none focus:border-yellow-500"
                                  >
                                     <option>Risk Override</option>
                                     <option>API Failure</option>
                                     <option>Agent Malfunction</option>
                                     <option>Breaking News</option>
                                  </select>
                               </div>

                               <button 
                                 onClick={handleOverrideSubmit}
                                 disabled={!overrideForm.symbol || !overrideForm.qty}
                                 className="w-full py-3 bg-yellow-600 hover:bg-yellow-500 text-black font-bold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm uppercase tracking-wide"
                               >
                                  Execute Override
                               </button>
                            </div>
                         </motion.div>
                      )}
                   </AnimatePresence>
                </div>

                {/* SECTION 4: RECENT ACTIONS */}
                <div className="space-y-3 pt-2">
                   <h3 className="text-xs font-bold text-white/50 uppercase tracking-widest flex items-center gap-2">
                      <History className="w-3 h-3" /> Recent Manual Actions
                   </h3>
                   <div className="space-y-2">
                      {mockRecentActions.map((action, i) => (
                         <div key={i} className="flex justify-between items-center p-3 rounded-lg bg-white/5 border border-white/5 text-xs">
                            <div>
                               <div className="font-medium text-white">{action.action}</div>
                               <div className="text-white/40 mt-0.5">{action.reason} • <span className="text-white/30">{action.user}</span></div>
                            </div>
                            <div className="font-mono text-white/30">{action.time}</div>
                         </div>
                      ))}
                   </div>
                </div>

              </div>
            </div>

            {/* CONFIRMATION OVERLAY */}
            <AnimatePresence>
               {confirmationAction && (
                  <motion.div 
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    className="absolute inset-0 z-50 bg-[#09090b]/95 flex flex-col items-center justify-center p-8 text-center"
                  >
                     <div className={cn("p-4 rounded-full mb-4 animate-pulse", confirmationAction.type === 'danger' ? "bg-red-500/20 text-red-500" : "bg-yellow-500/20 text-yellow-500")}>
                        <AlertTriangle className="w-10 h-10" />
                     </div>
                     <h3 className="text-xl font-bold text-white mb-2">Confirm Action</h3>
                     <p className="text-white/60 text-sm mb-6 max-w-xs">
                        Are you sure you want to 
                        <span className={cn("font-bold mx-1", confirmationAction.type === 'danger' ? "text-red-400" : "text-yellow-400")}>
                           {confirmationAction.label}
                        </span>?
                        This action cannot be undone.
                     </p>
                     
                     <div className="w-full max-w-xs space-y-4">
                        <div className="space-y-1 text-left">
                           <label className="text-[10px] uppercase font-bold text-white/30">Type "CONFIRM" to proceed</label>
                           <input 
                             value={confirmationInput}
                             onChange={e => setConfirmationInput(e.target.value)}
                             className="w-full bg-white/5 border border-white/20 rounded-lg py-3 px-4 text-center font-bold tracking-widest text-white focus:outline-none focus:border-white/50"
                             placeholder="CONFIRM"
                             autoFocus
                           />
                        </div>
                        
                        <div className="grid grid-cols-2 gap-3">
                           <button 
                             onClick={() => setConfirmationAction(null)}
                             className="py-3 rounded-lg border border-white/10 hover:bg-white/5 text-white/60 font-bold text-sm transition-colors"
                           >
                              CANCEL
                           </button>
                           <button 
                             onClick={executeConfirmedAction}
                             disabled={confirmationInput !== 'CONFIRM'}
                             className={cn(
                               "py-3 rounded-lg font-bold text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed",
                               confirmationAction.type === 'danger' ? "bg-red-600 hover:bg-red-500 text-white" : "bg-yellow-600 hover:bg-yellow-500 text-black"
                             )}
                           >
                              EXECUTE
                           </button>
                        </div>
                     </div>
                  </motion.div>
               )}
            </AnimatePresence>

          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body
  );
};
