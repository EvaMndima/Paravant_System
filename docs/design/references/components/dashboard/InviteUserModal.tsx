import React, { useState, useEffect } from 'react';
import { Mail, Shield, Check, X, Info } from 'lucide-react';
import { Modal } from '../ui/Modal';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { cn } from '../../lib/utils';

export type UserRole = 'Viewer' | 'Limited' | 'Full';

export interface InviteData {
  email: string;
  name: string;
  role: UserRole;
  permissions: string[];
}

interface InviteUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSendInvite: (data: InviteData) => void;
}

const PERMISSIONS = [
  { id: 'view_portfolio', label: 'View Portfolio', description: 'See holdings and performance' },
  { id: 'view_reports', label: 'View Reports', description: 'Access tax and performance docs' },
  { id: 'manage_alerts', label: 'Manage Alerts', description: 'Create and edit price alerts' },
  { id: 'export_data', label: 'Export Data', description: 'Download CSV/PDF reports' },
  { id: 'execute_trades', label: 'Execute Trades', description: 'Place market and limit orders' },
  { id: 'manage_settings', label: 'Manage Settings', description: 'Update profile and connections' },
];

const ROLE_PRESETS: Record<UserRole, string[]> = {
  Viewer: ['view_portfolio', 'view_reports'],
  Limited: ['view_portfolio', 'view_reports', 'manage_alerts', 'export_data'],
  Full: ['view_portfolio', 'view_reports', 'manage_alerts', 'export_data', 'execute_trades', 'manage_settings'],
};

export const InviteUserModal: React.FC<InviteUserModalProps> = ({
  isOpen,
  onClose,
  onSendInvite
}) => {
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState<UserRole>('Viewer');
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>(ROLE_PRESETS.Viewer);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Update permissions when role changes
  useEffect(() => {
    setSelectedPermissions(ROLE_PRESETS[role]);
  }, [role]);

  const togglePermission = (id: string) => {
    setSelectedPermissions(prev => 
      prev.includes(id) 
        ? prev.filter(p => p !== id)
        : [...prev, id]
    );
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    onSendInvite({
      email,
      name,
      role,
      permissions: selectedPermissions
    });
    
    setIsSubmitting(false);
    onClose();
    // Reset form
    setEmail('');
    setName('');
    setRole('Viewer');
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Invite New User"
      description="Grant access to your portfolio cockpit."
      size="lg"
    >
      <div className="space-y-6">
        
        {/* User Details */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Input 
            label="Full Name" 
            placeholder="e.g. John Doe" 
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <Input 
            label="Email Address" 
            placeholder="john@example.com" 
            type="email" 
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            leftIcon={<Mail className="w-4 h-4" />}
          />
        </div>

        <div className="h-px bg-deep-teal-800/5 dark:bg-white/5" />

        {/* Role Selection */}
        <div className="space-y-3">
          <label className="text-xs font-sans font-medium text-obsidian-400/70 dark:text-paper-100/70 ml-1">Access Role</label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {(['Viewer', 'Limited', 'Full'] as UserRole[]).map((r) => (
              <button
                key={r}
                onClick={() => setRole(r)}
                className={cn(
                  "relative flex flex-col items-start p-3 rounded-xl border transition-all duration-200 text-left",
                  role === r
                    ? "bg-turquoise-mist/10 border-turquoise-mist text-deep-teal-800 dark:text-turquoise-mist"
                    : "bg-paper-50 dark:bg-white/5 border-transparent hover:bg-deep-teal-800/5 dark:hover:bg-white/10 text-obsidian-400/60 dark:text-paper-100/60"
                )}
              >
                <div className="flex items-center gap-2 mb-1">
                  <Shield className={cn("w-4 h-4", role === r ? "fill-current" : "")} />
                  <span className="font-medium text-sm">{r}</span>
                </div>
                <span className="text-[10px] opacity-80 leading-tight">
                  {r === 'Viewer' ? 'Read-only access to dashboard.' : 
                   r === 'Limited' ? 'No trading capabilities.' : 
                   'Full admin & trading access.'}
                </span>
                {role === r && (
                  <div className="absolute top-3 right-3 text-turquoise-mist">
                    <Check className="w-4 h-4" />
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Permissions Grid */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
             <label className="text-xs font-sans font-medium text-obsidian-400/70 dark:text-paper-100/70 ml-1"> granular Permissions</label>
             <span className="text-[10px] text-obsidian-400/40 dark:text-paper-100/40">
               {selectedPermissions.length} selected
             </span>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {PERMISSIONS.map((perm) => {
              const isSelected = selectedPermissions.includes(perm.id);
              return (
                <button
                  key={perm.id}
                  onClick={() => togglePermission(perm.id)}
                  className={cn(
                    "flex items-center gap-3 p-3 rounded-lg border text-left transition-all",
                    isSelected
                      ? "bg-deep-teal-800/5 dark:bg-white/10 border-deep-teal-800/10 dark:border-white/10"
                      : "bg-transparent border-transparent opacity-60 hover:opacity-100 hover:bg-deep-teal-800/5 dark:hover:bg-white/5"
                  )}
                >
                  <div className={cn(
                    "w-5 h-5 rounded flex items-center justify-center border transition-colors",
                    isSelected
                      ? "bg-deep-teal-800 dark:bg-turquoise-mist border-transparent text-white dark:text-deep-teal-900"
                      : "border-obsidian-400/30 dark:border-paper-100/30"
                  )}>
                    {isSelected && <Check className="w-3 h-3" strokeWidth={3} />}
                  </div>
                  <div>
                    <div className="text-sm font-medium text-obsidian-400 dark:text-paper-100">{perm.label}</div>
                    <div className="text-[10px] text-obsidian-400/50 dark:text-paper-100/50">{perm.description}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-obsidian-400/50 dark:text-paper-100/50 bg-info/5 p-3 rounded-lg">
          <Info className="w-4 h-4 text-info" />
          <p>User will receive an email invitation to set up their password.</p>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 pt-4 border-t border-deep-teal-800/5 dark:border-white/5">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button 
            variant="primary" 
            onClick={handleSubmit} 
            isLoading={isSubmitting}
            disabled={!email || !name}
          >
            Send Invitation
          </Button>
        </div>

      </div>
    </Modal>
  );
};
