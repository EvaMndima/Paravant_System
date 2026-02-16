
import React, { useState } from 'react';
import { FileText, FileJson, Table, Calendar, Download, Check } from 'lucide-react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { cn } from '../../lib/utils';

export type ExportFormat = 'csv' | 'pdf' | 'json';

export interface ExportConfig {
  format: ExportFormat;
  startDate: string;
  endDate: string;
  includeMetadata: boolean;
}

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onExport: (config: ExportConfig) => void;
  title?: string;
}

export const ExportModal: React.FC<ExportModalProps> = ({
  isOpen,
  onClose,
  onExport,
  title = "Export Data"
}) => {
  const [format, setFormat] = useState<ExportFormat>('csv');
  const [startDate, setStartDate] = useState(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = async () => {
    setIsExporting(true);
    // Simulate processing delay
    await new Promise(resolve => setTimeout(resolve, 800));
    
    onExport({
      format,
      startDate,
      endDate,
      includeMetadata: true
    });
    
    setIsExporting(false);
    onClose();
  };

  const formats = [
    { id: 'csv', label: 'CSV', icon: Table, desc: 'Spreadsheet compatible' },
    { id: 'pdf', label: 'PDF', icon: FileText, desc: 'Document format' },
    { id: 'json', label: 'JSON', icon: FileJson, desc: 'Raw data structure' },
  ];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      description="Choose format and date range for your report."
      size="md"
    >
      <div className="space-y-6">
        
        {/* Format Selection */}
        <div className="space-y-3">
          <label className="text-xs font-medium text-obsidian-400/70 dark:text-paper-100/70 ml-1 uppercase tracking-wider">Format</label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {formats.map((f) => (
              <button
                key={f.id}
                onClick={() => setFormat(f.id as ExportFormat)}
                className={cn(
                  "relative flex flex-col items-center justify-center gap-2 p-4 rounded-xl border transition-all duration-200 text-center",
                  format === f.id
                    ? "bg-deep-teal-800/5 dark:bg-white/10 border-deep-teal-800 dark:border-turquoise-mist text-deep-teal-800 dark:text-turquoise-mist shadow-inner"
                    : "bg-paper-50 dark:bg-white/5 border-transparent hover:bg-deep-teal-800/5 dark:hover:bg-white/10 text-obsidian-400/60 dark:text-paper-100/60"
                )}
              >
                {format === f.id && (
                  <div className="absolute top-2 right-2">
                    <Check className="w-3 h-3" />
                  </div>
                )}
                <f.icon className="w-6 h-6" strokeWidth={1.5} />
                <div>
                  <div className="text-sm font-bold">{f.label}</div>
                  <div className="text-[10px] opacity-60">{f.desc}</div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Date Range */}
        <div className="space-y-3">
           <label className="text-xs font-medium text-obsidian-400/70 dark:text-paper-100/70 ml-1 uppercase tracking-wider">Date Range</label>
           <div className="grid grid-cols-2 gap-4">
              <Input 
                type="date" 
                label="Start Date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="font-mono text-sm"
              />
              <Input 
                type="date" 
                label="End Date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="font-mono text-sm"
              />
           </div>
        </div>

        {/* Info */}
        <div className="p-3 rounded-lg bg-deep-teal-800/5 dark:bg-white/5 border border-deep-teal-800/10 dark:border-white/10 flex gap-3 items-start">
           <Calendar className="w-4 h-4 text-obsidian-400/50 dark:text-paper-100/50 mt-0.5" />
           <div className="text-xs text-obsidian-400/70 dark:text-paper-100/70">
              Generating report for <span className="font-semibold">{format.toUpperCase()}</span> from <span className="font-mono">{startDate}</span> to <span className="font-mono">{endDate}</span>.
           </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 pt-4 border-t border-deep-teal-800/5 dark:border-white/5">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button 
            variant="primary" 
            onClick={handleExport} 
            isLoading={isExporting}
            leftIcon={<Download className="w-4 h-4" />}
          >
            Export Report
          </Button>
        </div>

      </div>
    </Modal>
  );
};
