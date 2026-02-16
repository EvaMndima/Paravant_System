import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  User, Palette, Bell, Link2, Shield, Users, 
  Upload, Check, X, LogOut, Smartphone, Globe, 
  Key, RefreshCw, Plus, Trash2, Eye, EyeOff, Monitor, Moon, Sun, Laptop,
  Mail, Droplets, Gem, Zap, Hexagon, Calendar, Clock, MapPin, Fingerprint, 
  Usb, Lock, FileKey, HelpCircle, Command, LayoutDashboard, Bot, Wallet, History, Search
} from 'lucide-react';

import { PageHeader } from '../layout/PageHeader';
import { GlassCard } from '../ui/GlassCard';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../ui/Tabs';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Avatar } from '../ui/Avatar';
import { Toggle } from '../ui/Toggle';
import { Badge } from '../ui/Badge';
import { InviteUserModal, InviteData } from '../dashboard/InviteUserModal';
import { useToast } from '../../contexts/ToastContext';
import { useTheme } from '../../contexts/ThemeContext';
import { useDashboard } from '../../contexts/DashboardContext';
import { cn } from '../../lib/utils';
import { fadeInUp, staggerContainer } from '../../lib/animations';
import { ThemeMode, AppTheme } from '../../types';

// --- Types & Mock Data ---

interface Connection {
  id: string;
  name: string;
  status: 'connected' | 'disconnected' | 'error';
  lastSync: string;
  icon: string;
}

interface AuthorizedUser {
  id: string;
  name: string;
  email: string;
  role: 'Admin' | 'Viewer' | 'Limited' | 'Full';
  lastAccess: string;
  avatar?: string;
  status: 'active';
}

interface PendingInvite {
  id: string;
  email: string;
  name: string;
  role: 'Admin' | 'Viewer' | 'Limited' | 'Full';
  sentAt: string;
  status: 'pending';
}

interface Session {
  id: string;
  device: string;
  type: 'Desktop' | 'Mobile';
  location: string;
  lastActive: string;
  isCurrent: boolean;
  ip: string;
}

interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  created: string;
  lastUsed: string;
  permissions: 'Read-Only' | 'Trade' | 'Admin';
}

const mockConnections: Connection[] = [
  { id: '1', name: 'Interactive Brokers', status: 'connected', lastSync: '2 mins ago', icon: 'IB' },
  { id: '2', name: 'TD Ameritrade', status: 'disconnected', lastSync: '14 days ago', icon: 'TD' },
  { id: '3', name: 'Alpaca Markets', status: 'connected', lastSync: 'Real-time', icon: 'AM' },
  { id: '4', name: 'Coinbase Pro', status: 'connected', lastSync: 'Real-time', icon: 'CP' },
];

const initialUsers: AuthorizedUser[] = [
  { id: '1', name: 'Accounting Firm', email: 'audit@fin-partners.com', role: 'Viewer', lastAccess: '2 days ago', status: 'active' },
  { id: '2', name: 'Sarah V.', email: 'sarah.v@family.net', role: 'Limited', lastAccess: '5 hours ago', avatar: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?ixlib=rb-1.2.1&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80', status: 'active' },
];

const mockSessions: Session[] = [
  { id: '1', device: 'Chrome on macOS', type: 'Desktop', location: 'New York, USA', lastActive: 'Active now', isCurrent: true, ip: '192.168.1.1' },
  { id: '2', device: 'Safari on iPhone 15 Pro', type: 'Mobile', location: 'New York, USA', lastActive: '2 hours ago', isCurrent: false, ip: '10.0.0.42' },
  { id: '3', device: 'Firefox on Windows', type: 'Desktop', location: 'London, UK', lastActive: '3 days ago', isCurrent: false, ip: '172.16.0.23' },
];

const mockApiKeys: ApiKey[] = [
  { id: '1', name: 'Trading Bot Alpha', prefix: 'pk_live_8f92', created: 'Oct 12, 2023', lastUsed: '5 mins ago', permissions: 'Trade' },
  { id: '2', name: 'Portfolio Tracker', prefix: 'pk_read_2b4a', created: 'Sep 01, 2023', lastUsed: '1 hour ago', permissions: 'Read-Only' },
];

// --- Sub-Components ---

const SettingSection = ({ title, description, children, className }: { title: string, description?: string, children?: React.ReactNode, className?: string }) => (
  <div className={cn("space-y-4", className)}>
    <div className="border-b border-deep-teal-800/5 dark:border-white/5 pb-2 mb-4">
      <h3 className="text-lg font-display font-medium text-obsidian-400 dark:text-paper-100">{title}</h3>
      {description && <p className="text-sm text-obsidian-400/50 dark:text-paper-100/50">{description}</p>}
    </div>
    {children}
  </div>
);

const ShortcutKey: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <kbd className="inline-flex items-center justify-center min-w-[24px] h-6 px-1.5 text-[10px] font-mono font-bold text-obsidian-400 dark:text-paper-100 bg-paper-100 dark:bg-white/10 border border-deep-teal-800/20 dark:border-white/20 rounded shadow-sm">
    {children}
  </kbd>
);

const ShortcutRow = ({ label, keys, icon: Icon }: { label: string, keys: React.ReactNode[], icon?: React.ElementType }) => (
  <div className="flex items-center justify-between py-3 border-b border-deep-teal-800/5 dark:border-white/5 last:border-0 hover:bg-deep-teal-800/5 dark:hover:bg-white/5 px-2 rounded-lg transition-colors">
    <div className="flex items-center gap-3">
      {Icon && <div className="p-1.5 bg-paper-200 dark:bg-white/5 rounded-md"><Icon className="w-4 h-4 text-obsidian-400/70 dark:text-paper-100/70" /></div>}
      <span className="text-sm font-medium text-obsidian-400 dark:text-paper-100">{label}</span>
    </div>
    <div className="flex items-center gap-1">
      {keys.map((k, i) => (
        <React.Fragment key={i}>
          {i > 0 && <span className="text-xs text-obsidian-400/30 dark:text-paper-100/30 mx-0.5">+</span>}
          <ShortcutKey>{k}</ShortcutKey>
        </React.Fragment>
      ))}
    </div>
  </div>
);

const ThemeCard = ({ 
  id, 
  name, 
  primary, 
  accent, 
  selected, 
  onClick,
  icon: Icon
}: { 
  id: AppTheme, 
  name: string, 
  primary: string, 
  accent: string, 
  selected: boolean, 
  onClick: () => void,
  icon: React.ElementType
}) => (
  <button 
    onClick={onClick}
    className={cn(
      "relative overflow-hidden rounded-xl border-2 transition-all duration-300 flex flex-col text-left group",
      selected 
        ? "border-turquoise-mist ring-2 ring-turquoise-mist/20 scale-[1.02]" 
        : "border-transparent hover:border-deep-teal-800/20 dark:hover:border-white/20"
    )}
  >
    {/* Preview Background */}
    <div className="h-24 w-full relative" style={{ backgroundColor: primary }}>
       <div className="absolute top-3 left-3 text-white/90">
          <Icon className="w-5 h-5" />
       </div>
       {/* Accent Splash */}
       <div 
         className="absolute bottom-3 right-3 w-8 h-8 rounded-full shadow-lg flex items-center justify-center"
         style={{ backgroundColor: accent }}
       >
         {selected && <Check className="w-4 h-4 text-white" />}
       </div>
       {/* Mock UI Elements */}
       <div className="absolute bottom-3 left-3 w-16 h-2 rounded-full bg-white/20" />
       <div className="absolute bottom-7 left-3 w-10 h-2 rounded-full bg-white/20" />
    </div>
    
    {/* Label */}
    <div className="p-3 bg-paper-100 dark:bg-obsidian-300 w-full">
       <span className={cn(
         "text-sm font-medium transition-colors",
         selected ? "text-deep-teal-800 dark:text-turquoise-mist" : "text-obsidian-400 dark:text-paper-100"
       )}>{name}</span>
    </div>
  </button>
);

export const SettingsPage = () => {
  const { toast } = useToast();
  const { activeSettingsTab, navigateToSettingsTab } = useDashboard();
  const [activeTab, setActiveTab] = useState(activeSettingsTab || 'profile');
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Update local state when context changes (e.g. navigation from header)
  useEffect(() => {
    setActiveTab(activeSettingsTab);
  }, [activeSettingsTab]);

  // Update context when local state changes (manual click)
  const handleTabChange = (val: string) => {
    setActiveTab(val);
    navigateToSettingsTab(val);
  };
  
  // Theme Context
  const { 
    mode, setMode, 
    appTheme, setAppTheme,
    compactMode, setCompactMode,
    reducedMotion, setReducedMotion
  } = useTheme();
  
  // State
  const [users, setUsers] = useState<AuthorizedUser[]>(initialUsers);
  const [invites, setInvites] = useState<PendingInvite[]>([]);
  const [sessions, setSessions] = useState<Session[]>(mockSessions);
  const [apiKeys, setApiKeys] = useState<ApiKey[]>(mockApiKeys);
  const [avatarSrc, setAvatarSrc] = useState('https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-1.2.1&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80');

  // Security Toggles
  const [securitySettings, setSecuritySettings] = useState({
    twoFactor: true,
    biometrics: false,
    tradingPin: true,
    hardwareKey: false
  });

  // Notification Toggles
  const [notifSettings, setNotifSettings] = useState({
    emailNotifs: true,
    pushNotifs: true,
  });

  const handleSecurityToggle = (key: keyof typeof securitySettings, value: boolean) => {
    setSecuritySettings(prev => ({ ...prev, [key]: value }));
    toast({ 
      title: 'Security Updated', 
      description: `${key === 'twoFactor' ? '2FA' : key === 'biometrics' ? 'Biometric login' : key === 'tradingPin' ? 'Trading PIN' : 'Hardware Key'} has been ${value ? 'enabled' : 'disabled'}.`, 
      type: 'info' 
    });
  };

  const handleNotifToggle = (key: keyof typeof notifSettings) => {
    setNotifSettings(prev => ({ ...prev, [key]: !prev[key] }));
  };

  // --- Avatar Handler ---
  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const objectUrl = URL.createObjectURL(file);
      setAvatarSrc(objectUrl);
      toast({
        title: 'Profile Updated',
        description: 'New profile picture uploaded successfully.',
        type: 'success'
      });
    }
  };

  // --- Session Handlers ---
  const handleRevokeSession = (sessionId: string) => {
    setSessions(prev => prev.filter(s => s.id !== sessionId));
    toast({ title: 'Session Revoked', description: 'Device has been logged out.', type: 'info' });
  };

  // --- API Key Handlers ---
  const handleRevokeApiKey = (id: string) => {
    setApiKeys(prev => prev.filter(k => k.id !== id));
    toast({ title: 'API Key Revoked', description: 'Access token invalidated immediately.', type: 'info' });
  };

  // --- User Handlers ---
  const handleSendInvite = (data: InviteData) => {
    const newInvite: PendingInvite = {
      id: Math.random().toString(36).substr(2, 9),
      email: data.email,
      name: data.name,
      role: data.role,
      sentAt: 'Just now',
      status: 'pending'
    };
    setInvites([...invites, newInvite]);
    toast({
      title: 'Invitation Sent',
      description: `Access invitation sent to ${data.email}`,
      type: 'success'
    });
  };

  const handleRevokeUser = (id: string) => {
    setUsers(prev => prev.filter(u => u.id !== id));
    toast({ title: 'Access Revoked', type: 'info' });
  };

  const handleRevokeInvite = (id: string) => {
    setInvites(prev => prev.filter(i => i.id !== id));
    toast({ title: 'Invitation Cancelled', type: 'info' });
  };

  return (
    <motion.div
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      className="space-y-6 pt-2 pb-10"
    >
      <PageHeader 
        title="System Settings" 
        description="Manage your account preferences, security, and integrations." 
      />

      <GlassCard className="min-h-[600px] flex flex-col md:flex-row overflow-hidden" padding="none">
        
        {/* Sidebar Navigation */}
        <Tabs 
          value={activeTab} 
          onValueChange={handleTabChange} 
          className="flex flex-col md:flex-row w-full h-full"
        >
          {/* Sidebar Container */}
          <div className="w-full md:w-64 border-b md:border-b-0 md:border-r border-deep-teal-800/5 dark:border-white/5 bg-deep-teal-800/5 dark:bg-white/5 flex-shrink-0">
             <TabsList 
                variant="underline" 
                className="flex flex-row md:flex-col items-start justify-start p-2 md:p-4 gap-1 md:gap-2 overflow-x-auto md:overflow-visible border-none h-full"
             >
                {[
                  { id: 'profile', label: 'Profile & Account', icon: User },
                  { id: 'appearance', label: 'Appearance', icon: Palette },
                  { id: 'notifications', label: 'Notifications', icon: Bell },
                  { id: 'connections', label: 'Connections', icon: Link2 },
                  { id: 'security', label: 'Security', icon: Shield },
                  { id: 'access', label: 'Access & Sharing', icon: Users },
                  { id: 'help', label: 'Help & Shortcuts', icon: HelpCircle },
                ].map(tab => (
                  <TabsTrigger 
                    key={tab.id} 
                    value={tab.id}
                    className={cn(
                      "w-full justify-start gap-3 px-4 py-3 rounded-xl transition-all",
                      activeTab === tab.id 
                        ? "bg-paper-100 dark:bg-white/10 shadow-sm text-deep-teal-800 dark:text-paper-100 font-medium" 
                        : "text-obsidian-400/60 dark:text-paper-100/60 hover:bg-deep-teal-800/5 dark:hover:bg-white/5 hover:text-obsidian-400 dark:hover:text-paper-100"
                    )}
                  >
                    <tab.icon className="w-4 h-4" />
                    <span className="whitespace-nowrap">{tab.label}</span>
                  </TabsTrigger>
                ))}
             </TabsList>
          </div>

          {/* Content Area */}
          <div className="flex-1 p-6 md:p-8 overflow-y-auto">
            
            {/* ... EXISTING CONTENT ... */}
            
            {/* --- TAB: PROFILE --- */}
            <TabsContent value="profile" className="mt-0 space-y-8 animate-fade-in">
              <SettingSection title="Personal Information">
                <div className="flex flex-col md:flex-row items-start gap-8">
                  {/* Editable Avatar */}
                  <div className="relative group cursor-pointer" onClick={handleAvatarClick}>
                    <input 
                      type="file" 
                      ref={fileInputRef} 
                      className="hidden" 
                      accept="image/*" 
                      onChange={handleFileChange}
                    />
                    <Avatar 
                      src={avatarSrc} 
                      size="xl" 
                      className="w-28 h-28 border-4 border-paper-100 dark:border-obsidian-300 shadow-xl"
                    />
                    {/* Hover Overlay */}
                    <div className="absolute inset-0 bg-black/40 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity backdrop-blur-[1px]">
                       <Upload className="w-6 h-6 text-white" />
                    </div>
                    {/* Badge */}
                    <div className="absolute bottom-1 right-1 p-1.5 bg-paper-100 dark:bg-obsidian-400 rounded-full border border-deep-teal-800/10 dark:border-white/10 shadow-sm text-turquoise-mist">
                      <Palette className="w-3.5 h-3.5" />
                    </div>
                  </div>
                  
                  <div className="flex-1 w-full grid grid-cols-1 md:grid-cols-2 gap-5">
                    <Input label="Display Name" defaultValue="Alexander V." />
                    <Input label="Role / Title" defaultValue="Director of Alpha" />
                    <Input label="Email Address" defaultValue="alexander@paravant.ai" type="email" />
                    <Input label="Phone Number" defaultValue="+1 (555) 019-2834" type="tel" />
                  </div>
                </div>
              </SettingSection>

              <div className="h-px bg-deep-teal-800/5 dark:bg-white/5" />

              {/* Account Metadata - Read Only */}
              <SettingSection title="Account Statistics">
                 <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <Input 
                      label="Member Since" 
                      defaultValue="October 24, 2023" 
                      readOnly 
                      leftIcon={<Calendar className="w-4 h-4" />} 
                      className="bg-deep-teal-800/5 dark:bg-white/5 border-transparent cursor-default text-obsidian-400/80 dark:text-paper-100/80"
                    />
                    <Input 
                      label="Last Login" 
                      defaultValue="Today, 09:41 AM" 
                      readOnly 
                      leftIcon={<Clock className="w-4 h-4" />} 
                      className="bg-deep-teal-800/5 dark:bg-white/5 border-transparent cursor-default text-obsidian-400/80 dark:text-paper-100/80"
                    />
                 </div>
              </SettingSection>

              <div className="h-px bg-deep-teal-800/5 dark:bg-white/5" />

              {/* Active Sessions */}
              <SettingSection title="Active Sessions" description="Manage devices currently logged into your account.">
                 <div className="space-y-3">
                    {sessions.map(session => (
                       <div key={session.id} className="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-xl border border-deep-teal-800/5 dark:border-white/5 bg-paper-50 dark:bg-white/5 gap-4">
                          <div className="flex items-center gap-4">
                             <div className={cn(
                                "w-10 h-10 rounded-full flex items-center justify-center",
                                session.isCurrent ? "bg-turquoise-mist/10 text-deep-teal-800 dark:text-turquoise-mist" : "bg-obsidian-400/5 dark:bg-white/10 text-obsidian-400/60 dark:text-paper-100/60"
                             )}>
                                {session.type === 'Desktop' ? <Laptop className="w-5 h-5" /> : <Smartphone className="w-5 h-5" />}
                             </div>
                             <div>
                                <div className="flex items-center gap-2">
                                   <span className="text-sm font-medium text-obsidian-400 dark:text-paper-100">{session.device}</span>
                                   {session.isCurrent && <Badge variant="success" size="sm" className="h-5 text-[10px] px-1.5">Current</Badge>}
                                </div>
                                <div className="text-xs text-obsidian-400/50 dark:text-paper-100/50 flex items-center gap-2 mt-0.5">
                                   <MapPin className="w-3 h-3" /> {session.location} • {session.ip} • {session.lastActive}
                                </div>
                             </div>
                          </div>
                          {!session.isCurrent && (
                             <Button 
                               variant="ghost" 
                               size="sm" 
                               onClick={() => handleRevokeSession(session.id)}
                               className="text-xs text-obsidian-400/60 hover:text-loss hover:bg-loss/10"
                             >
                                Revoke
                             </Button>
                          )}
                       </div>
                    ))}
                 </div>
              </SettingSection>

              <div className="flex justify-end pt-4">
                 <Button>Save Profile Changes</Button>
              </div>
            </TabsContent>

            {/* --- TAB: APPEARANCE --- */}
            <TabsContent value="appearance" className="mt-0 space-y-8 animate-fade-in">
              <SettingSection title="Color Theme" description="Select a harmonious color palette for the workspace.">
                 <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    <ThemeCard 
                      id="ocean" 
                      name="Ocean" 
                      primary="#0F3D3E" 
                      accent="#2A9D8F" 
                      icon={Droplets}
                      selected={appTheme === 'ocean'} 
                      onClick={() => setAppTheme('ocean')} 
                    />
                    <ThemeCard 
                      id="sapphire" 
                      name="Sapphire" 
                      primary="#1E3A8A" 
                      accent="#3B82F6" 
                      icon={Gem}
                      selected={appTheme === 'sapphire'} 
                      onClick={() => setAppTheme('sapphire')} 
                    />
                    <ThemeCard 
                      id="emerald" 
                      name="Emerald" 
                      primary="#064E3B" 
                      accent="#10B981" 
                      icon={Zap}
                      selected={appTheme === 'emerald'} 
                      onClick={() => setAppTheme('emerald')} 
                    />
                    <ThemeCard 
                      id="onyx" 
                      name="Onyx" 
                      primary="#18181B" 
                      accent="#D4AF37" 
                      icon={Hexagon}
                      selected={appTheme === 'onyx'} 
                      onClick={() => setAppTheme('onyx')} 
                    />
                 </div>
              </SettingSection>

              <SettingSection title="Display Mode" description="Choose how the application adapts to light.">
                 <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    {[
                      { id: 'light', label: 'Light', icon: Sun },
                      { id: 'dark', label: 'Dark', icon: Moon },
                      { id: 'system', label: 'System', icon: Laptop },
                    ].map((m) => (
                      <button
                        key={m.id}
                        onClick={() => setMode(m.id as ThemeMode)}
                        className={cn(
                          "flex flex-col items-center justify-center gap-3 p-4 rounded-xl border-2 transition-all",
                          mode === m.id 
                            ? "border-turquoise-mist bg-turquoise-mist/5" 
                            : "border-deep-teal-800/5 dark:border-white/5 hover:border-deep-teal-800/20 dark:hover:border-white/20"
                        )}
                      >
                         <m.icon className={cn("w-6 h-6", mode === m.id ? "text-turquoise-mist" : "text-obsidian-400/60 dark:text-paper-100/60")} />
                         <span className="text-sm font-medium">{m.label}</span>
                      </button>
                    ))}
                 </div>
              </SettingSection>

              <SettingSection title="Interface Density">
                <div className="space-y-6">
                   <div className="flex items-center justify-between">
                      <div>
                         <div className="text-sm font-medium">Compact Mode</div>
                         <div className="text-xs text-obsidian-400/50 dark:text-paper-100/50">Decrease padding and density for data-heavy views.</div>
                      </div>
                      <Toggle checked={compactMode} onCheckedChange={(v) => setCompactMode(v)} />
                   </div>

                   <div className="flex items-center justify-between">
                      <div>
                         <div className="text-sm font-medium">Reduced Motion</div>
                         <div className="text-xs text-obsidian-400/50 dark:text-paper-100/50">Minimize animations for a faster feel.</div>
                      </div>
                      <Toggle checked={reducedMotion} onCheckedChange={(v) => setReducedMotion(v)} />
                   </div>
                </div>
              </SettingSection>
            </TabsContent>

            {/* --- TAB: NOTIFICATIONS --- */}
            <TabsContent value="notifications" className="mt-0 space-y-8 animate-fade-in">
               <SettingSection title="Delivery Channels">
                  <div className="flex flex-col gap-4">
                    <div className="flex items-center justify-between p-4 rounded-xl bg-deep-teal-800/5 dark:bg-white/5">
                       <div className="flex items-center gap-3">
                          <div className="p-2 bg-paper-100 dark:bg-obsidian-400 rounded-lg">
                             <Bell className="w-5 h-5 text-deep-teal-800 dark:text-paper-100" />
                          </div>
                          <div>
                             <div className="text-sm font-medium">Push Notifications</div>
                             <div className="text-xs opacity-60">Real-time alerts to your device</div>
                          </div>
                       </div>
                       <Toggle checked={notifSettings.pushNotifs} onCheckedChange={() => handleNotifToggle('pushNotifs')} />
                    </div>
                  </div>
               </SettingSection>
            </TabsContent>

            {/* --- TAB: CONNECTIONS --- */}
            <TabsContent value="connections" className="mt-0 space-y-8 animate-fade-in">
               <SettingSection title="Brokerage Integrations">
                  <div className="space-y-4">
                     {mockConnections.map(conn => (
                       <div key={conn.id} className="flex items-center justify-between p-4 rounded-xl border border-deep-teal-800/5 dark:border-white/5 bg-paper-100 dark:bg-obsidian-300">
                          <div className="flex items-center gap-4">
                             <div className="w-10 h-10 rounded-full bg-deep-teal-800/5 dark:bg-white/10 flex items-center justify-center font-bold text-xs">
                                {conn.icon}
                             </div>
                             <div>
                                <h4 className="font-medium text-sm">{conn.name}</h4>
                                <div className="flex items-center gap-2 mt-0.5">
                                   <Badge variant={conn.status === 'connected' ? 'success' : 'neutral'} size="sm" dot>
                                      {conn.status === 'connected' ? 'Connected' : 'Disconnected'}
                                   </Badge>
                                </div>
                             </div>
                          </div>
                          <div className="flex items-center gap-2">
                             {conn.status === 'connected' ? (
                                <Button variant="secondary" size="sm">Configure</Button>
                             ) : (
                                <Button variant="primary" size="sm">Connect</Button>
                             )}
                          </div>
                       </div>
                     ))}
                  </div>
               </SettingSection>
            </TabsContent>

            {/* --- TAB: SECURITY (ENHANCED) --- */}
            <TabsContent value="security" className="mt-0 space-y-8 animate-fade-in">
               {/* 1. Authentication Methods */}
               <SettingSection title="Sign-in & Authentication">
                  <div className="space-y-4">
                     {/* Password Update */}
                     <div className="flex items-center justify-between p-4 rounded-xl border border-deep-teal-800/5 dark:border-white/5 bg-paper-50 dark:bg-white/5">
                        <div className="flex items-center gap-4">
                           <div className="p-2 bg-deep-teal-800/5 dark:bg-white/10 rounded-lg text-deep-teal-800 dark:text-turquoise-mist">
                              <Key className="w-5 h-5" />
                           </div>
                           <div>
                              <div className="text-sm font-medium text-obsidian-400 dark:text-paper-100">Password</div>
                              <div className="text-xs text-obsidian-400/50 dark:text-paper-100/50">Last changed 90 days ago</div>
                           </div>
                        </div>
                        <Button variant="secondary" size="sm">Change Password</Button>
                     </div>

                     {/* 2FA Toggle */}
                     <div className="flex items-center justify-between p-4 rounded-xl border border-deep-teal-800/5 dark:border-white/5 bg-paper-50 dark:bg-white/5">
                        <div className="flex items-center gap-4">
                           <div className="p-2 bg-deep-teal-800/5 dark:bg-white/10 rounded-lg text-deep-teal-800 dark:text-turquoise-mist">
                              <Shield className="w-5 h-5" />
                           </div>
                           <div>
                              <div className="text-sm font-medium text-obsidian-400 dark:text-paper-100">Two-Factor Authentication</div>
                              <div className="text-xs text-obsidian-400/50 dark:text-paper-100/50">Secure your account with an authenticator app.</div>
                           </div>
                        </div>
                        <Toggle checked={securitySettings.twoFactor} onCheckedChange={(v) => handleSecurityToggle('twoFactor', v)} />
                     </div>

                     {/* Hardware Key */}
                     <div className="flex items-center justify-between p-4 rounded-xl border border-deep-teal-800/5 dark:border-white/5 bg-paper-50 dark:bg-white/5">
                        <div className="flex items-center gap-4">
                           <div className="p-2 bg-deep-teal-800/5 dark:bg-white/10 rounded-lg text-deep-teal-800 dark:text-turquoise-mist">
                              <Usb className="w-5 h-5" />
                           </div>
                           <div>
                              <div className="text-sm font-medium text-obsidian-400 dark:text-paper-100">Hardware Security Keys</div>
                              <div className="text-xs text-obsidian-400/50 dark:text-paper-100/50">YubiKey, Titan, or compliant devices.</div>
                           </div>
                        </div>
                        <div className="flex items-center gap-3">
                           {securitySettings.hardwareKey ? <Badge variant="success" size="sm">Active</Badge> : <Badge variant="neutral" size="sm">None</Badge>}
                           <Button variant="ghost" size="sm" className="text-xs">Manage</Button>
                        </div>
                     </div>
                  </div>
               </SettingSection>

               {/* 2. Application Security */}
               <SettingSection title="Application Security">
                  <div className="space-y-4">
                     {/* Biometrics */}
                     <div className="flex items-center justify-between p-4 rounded-xl border border-deep-teal-800/5 dark:border-white/5 bg-paper-50 dark:bg-white/5">
                        <div className="flex items-center gap-4">
                           <div className="p-2 bg-deep-teal-800/5 dark:bg-white/10 rounded-lg text-deep-teal-800 dark:text-turquoise-mist">
                              <Fingerprint className="w-5 h-5" /> 
                           </div>
                           <div>
                              <div className="text-sm font-medium text-obsidian-400 dark:text-paper-100">Biometric Unlock</div>
                              <div className="text-xs text-obsidian-400/50 dark:text-paper-100/50">Use FaceID or TouchID to access dashboard.</div>
                           </div>
                        </div>
                        <Toggle checked={securitySettings.biometrics} onCheckedChange={(v) => handleSecurityToggle('biometrics', v)} />
                     </div>

                     {/* Trading PIN */}
                     <div className="flex items-center justify-between p-4 rounded-xl border border-deep-teal-800/5 dark:border-white/5 bg-paper-50 dark:bg-white/5">
                        <div className="flex items-center gap-4">
                           <div className="p-2 bg-deep-teal-800/5 dark:bg-white/10 rounded-lg text-deep-teal-800 dark:text-turquoise-mist">
                              <Lock className="w-5 h-5" />
                           </div>
                           <div>
                              <div className="text-sm font-medium text-obsidian-400 dark:text-paper-100">Trading PIN</div>
                              <div className="text-xs text-obsidian-400/50 dark:text-paper-100/50">Require additional authentication for order execution.</div>
                           </div>
                        </div>
                        <Toggle checked={securitySettings.tradingPin} onCheckedChange={(v) => handleSecurityToggle('tradingPin', v)} />
                     </div>
                  </div>
               </SettingSection>

               {/* 3. API Management */}
               <SettingSection title="API Management" description="Manage access keys for external trading bots and analytics tools.">
                  <div className="space-y-3">
                      {apiKeys.map(key => (
                          <GlassCard key={key.id} variant="subtle" className="flex flex-col sm:flex-row sm:items-center justify-between p-4 gap-4" padding="none">
                              <div className="flex items-center gap-4">
                                  <div className="w-10 h-10 rounded-full bg-deep-teal-800/5 dark:bg-white/10 flex items-center justify-center font-mono text-xs text-deep-teal-800 dark:text-turquoise-mist">
                                      <FileKey className="w-5 h-5" />
                                  </div>
                                  <div>
                                      <div className="flex items-center gap-2">
                                         <h4 className="font-medium text-sm text-obsidian-400 dark:text-paper-100">{key.name}</h4>
                                         <Badge variant="neutral" size="sm" className="text-[9px] h-4 px-1">{key.permissions}</Badge>
                                      </div>
                                      <div className="flex items-center gap-3 mt-1">
                                          <code className="text-[10px] font-mono bg-black/5 dark:bg-white/10 px-1.5 py-0.5 rounded text-obsidian-400/70 dark:text-paper-100/70">{key.prefix}••••••••</code>
                                          <span className="text-[10px] text-obsidian-400/40 dark:text-paper-100/40">• Created {key.created}</span>
                                      </div>
                                  </div>
                              </div>
                              <div className="flex items-center justify-between sm:justify-end gap-4 w-full sm:w-auto border-t sm:border-t-0 border-deep-teal-800/5 dark:border-white/5 pt-3 sm:pt-0">
                                  <span className="text-[10px] text-obsidian-400/40 dark:text-paper-100/40">Last used: {key.lastUsed}</span>
                                  <Button 
                                    variant="ghost" 
                                    size="sm" 
                                    className="text-loss hover:text-loss hover:bg-loss/10 h-8 text-xs" 
                                    onClick={() => handleRevokeApiKey(key.id)}
                                  >
                                    Revoke
                                  </Button>
                              </div>
                          </GlassCard>
                      ))}
                      <Button variant="secondary" className="w-full mt-2 border-dashed" leftIcon={<Plus className="w-4 h-4"/>}>
                        Generate New API Key
                      </Button>
                  </div>
               </SettingSection>
            </TabsContent>

            {/* --- TAB: ACCESS --- */}
            <TabsContent value="access" className="mt-0 space-y-8 animate-fade-in">
               <div className="flex items-center justify-between">
                  <div>
                     <h3 className="text-lg font-display font-medium text-obsidian-400 dark:text-paper-100">Access & Sharing</h3>
                     <p className="text-sm text-obsidian-400/50 dark:text-paper-100/50">Manage access levels for your team and advisors.</p>
                  </div>
                  <Button variant="primary" size="sm" leftIcon={<Plus className="w-4 h-4" />} onClick={() => setInviteModalOpen(true)}>
                     Invite User
                  </Button>
               </div>
               
               {/* Pending Invites */}
               {invites.length > 0 && (
                  <div className="space-y-2">
                     <h4 className="text-xs font-mono uppercase tracking-widest opacity-60 ml-1">Pending Invites</h4>
                     {invites.map(invite => (
                        <GlassCard key={invite.id} variant="subtle" className="flex items-center justify-between p-4 bg-warning/5 border-warning/10" padding="none">
                           <div className="flex items-center gap-4">
                              <div className="w-10 h-10 rounded-full bg-warning/10 flex items-center justify-center text-warning">
                                <Mail className="w-5 h-5" />
                              </div>
                              <div>
                                 <div className="font-medium text-sm flex items-center gap-2">
                                    {invite.name}
                                    <Badge variant="warning" size="sm" className="text-[10px] h-5 px-1.5">Pending</Badge>
                                 </div>
                                 <div className="text-xs opacity-60">{invite.email} • {invite.role}</div>
                              </div>
                           </div>
                           <div className="flex items-center gap-3">
                              <Button variant="ghost" size="sm" className="text-obsidian-400/40 hover:text-loss hover:bg-loss/10" onClick={() => handleRevokeInvite(invite.id)}>
                                 <X className="w-4 h-4" />
                              </Button>
                           </div>
                        </GlassCard>
                     ))}
                  </div>
               )}

               {/* Active Users */}
               <div className="space-y-2">
                  <h4 className="text-xs font-mono uppercase tracking-widest opacity-60 ml-1">Active Users</h4>
                  {users.length === 0 ? (
                     <div className="text-sm opacity-50 p-4 italic">No active users.</div>
                  ) : (
                     users.map(user => (
                        <GlassCard key={user.id} variant="subtle" className="flex items-center justify-between p-4" padding="none">
                           <div className="flex items-center gap-4">
                              <Avatar src={user.avatar} name={user.name} size="md" />
                              <div>
                                 <div className="font-medium text-sm flex items-center gap-2">
                                    {user.name}
                                    <Badge variant="neutral" size="sm" className="text-[10px] h-5 px-1.5">{user.role}</Badge>
                                 </div>
                                 <div className="text-xs opacity-60">{user.email}</div>
                              </div>
                           </div>
                           <div className="flex items-center gap-4">
                              <Button variant="ghost" size="sm" className="text-obsidian-400/40 hover:text-loss hover:bg-loss/10" onClick={() => handleRevokeUser(user.id)}>
                                 <Trash2 className="w-4 h-4" />
                              </Button>
                           </div>
                        </GlassCard>
                     ))
                  )}
               </div>
            </TabsContent>

            {/* --- TAB: HELP & SHORTCUTS --- */}
            <TabsContent value="help" className="mt-0 space-y-8 animate-fade-in">
               <SettingSection title="Keyboard Shortcuts" description="Boost your productivity with these global hotkeys.">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
                     <div className="space-y-2">
                        <h4 className="text-xs font-mono uppercase tracking-widest opacity-60 mb-2">Navigation</h4>
                        <ShortcutRow label="Go to Cockpit" keys={['G', 'C']} icon={LayoutDashboard} />
                        <ShortcutRow label="Go to Agents" keys={['G', 'A']} icon={Bot} />
                        <ShortcutRow label="Go to Portfolio" keys={['G', 'P']} icon={Wallet} />
                        <ShortcutRow label="Go to History" keys={['G', 'T']} icon={History} />
                     </div>
                     <div className="space-y-2">
                        <h4 className="text-xs font-mono uppercase tracking-widest opacity-60 mb-2">Global Actions</h4>
                        <ShortcutRow label="Global Search" keys={['Ctrl', 'K']} icon={Search} />
                        <ShortcutRow label="Emergency Panel" keys={['Ctrl', 'Shift', 'K']} icon={Shield} />
                        <ShortcutRow label="Show Shortcuts" keys={['?']} icon={Command} />
                        <ShortcutRow label="Close Panel" keys={['Esc']} icon={X} />
                     </div>
                  </div>
               </SettingSection>
               
               <div className="h-px bg-deep-teal-800/5 dark:bg-white/5" />

               <SettingSection title="Support">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                     <GlassCard variant="subtle" className="flex items-center justify-between p-4" padding="none">
                        <div>
                           <h4 className="font-medium text-sm">Documentation</h4>
                           <p className="text-xs opacity-60">Guides and API references.</p>
                        </div>
                        <Button variant="ghost" size="sm">Open</Button>
                     </GlassCard>
                     <GlassCard variant="subtle" className="flex items-center justify-between p-4" padding="none">
                        <div>
                           <h4 className="font-medium text-sm">Contact Support</h4>
                           <p className="text-xs opacity-60">24/7 dedicated assistance.</p>
                        </div>
                        <Button variant="ghost" size="sm">Email</Button>
                     </GlassCard>
                  </div>
               </SettingSection>
            </TabsContent>

          </div>
        </Tabs>
      </GlassCard>

      {/* Invite User Modal */}
      <InviteUserModal 
        isOpen={inviteModalOpen} 
        onClose={() => setInviteModalOpen(false)} 
        onSendInvite={handleSendInvite}
      />

    </motion.div>
  );
};