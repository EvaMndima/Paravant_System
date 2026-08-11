import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  User, Palette, Bell, Link, Shield, HelpCircle,
  Eye, EyeOff, Key, Wifi, CheckCircle, Save,
  Monitor, Sun, Moon,
} from 'lucide-react';
import { useDashboard } from '@/contexts/DashboardContext';
import { useTheme } from '@/contexts/ThemeContext';
import { useToast } from '@/contexts/ToastContext';
import { GlassCard, Badge, Button, Input, Toggle } from '@/components/ui';
import { staggerContainer, fadeInUp } from '@/lib/animations';

// ── Types ─────────────────────────────────────────────────────────────────────

type SettingsTab = 'profile' | 'appearance' | 'notifications' | 'connections' | 'security' | 'help';

const TABS: { id: SettingsTab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: 'profile',       label: 'Profile',       icon: User       },
  { id: 'appearance',    label: 'Appearance',    icon: Palette    },
  { id: 'notifications', label: 'Notifications', icon: Bell       },
  { id: 'connections',   label: 'Connections',   icon: Link       },
  { id: 'security',      label: 'Security',      icon: Shield     },
  { id: 'help',          label: 'Help',          icon: HelpCircle },
];

const KEYBOARD_SHORTCUTS = [
  { keys: ['G', 'C'],   action: 'Go to Cockpit'    },
  { keys: ['G', 'S'],   action: 'Go to Strategies' },
  { keys: ['G', 'P'],   action: 'Go to Portfolio'  },
  { keys: ['G', 'R'],   action: 'Go to Risk'       },
  { keys: ['G', 'A'],   action: 'Go to Alerts'     },
  { keys: ['Ctrl', 'E'], action: 'Emergency Stop'  },
  { keys: ['Ctrl', 'K'], action: 'Quick Search'    },
  { keys: ['Ctrl', '/'], action: 'Toggle Sidebar'  },
  { keys: ['Ctrl', 'D'], action: 'Toggle Dark Mode'},
  { keys: ['?'],         action: 'Show Shortcuts'  },
];

// ── Sub-components ────────────────────────────────────────────────────────────

function ProfileTab() {
  const { toast } = useToast();
  const [name, setName]   = useState('Eva Mndima');
  const [email, setEmail] = useState('enairuko@gmail.com');
  const [phone, setPhone] = useState('+27 000 000 0000');

  return (
    <div className="space-y-6">
      <GlassCard>
        <h3 className="text-sm font-medium text-paper-200 mb-4">Personal Information</h3>
        <div className="flex items-center gap-4 mb-6">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-turquoise to-info flex items-center justify-center text-2xl font-bold text-paper-100">
            E
          </div>
          <div>
            <div className="text-sm font-medium text-paper-100">{name}</div>
            <div className="text-xs text-paper-400">{email}</div>
            <Button variant="ghost" size="sm" className="mt-1 text-xs px-0 text-turquoise">Change avatar</Button>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-paper-400 mb-1 block">Full Name</label>
            <Input value={name} onChange={e => setName(e.target.value)} className="w-full" />
          </div>
          <div>
            <label className="text-xs text-paper-400 mb-1 block">Email</label>
            <Input value={email} onChange={e => setEmail(e.target.value)} type="email" className="w-full" />
          </div>
          <div>
            <label className="text-xs text-paper-400 mb-1 block">Phone</label>
            <Input value={phone} onChange={e => setPhone(e.target.value)} className="w-full" />
          </div>
          <div>
            <label className="text-xs text-paper-400 mb-1 block">Timezone</label>
            <Input value="Africa/Johannesburg (UTC+2)" readOnly className="w-full opacity-60" />
          </div>
        </div>
        <div className="flex justify-end mt-4">
          <Button variant="primary" size="sm" onClick={() => toast({ title: 'Profile saved', type: 'success' })}>
            <Save className="w-4 h-4 mr-1" /> Save Changes
          </Button>
        </div>
      </GlassCard>

      <GlassCard>
        <h3 className="text-sm font-medium text-paper-200 mb-4">Account Details</h3>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-paper-400">Member since</span>
            <span className="text-paper-200">February 8, 2026</span>
          </div>
          <div className="flex justify-between">
            <span className="text-paper-400">Trading mode</span>
            <Badge variant="warning" size="sm">Paper Trading</Badge>
          </div>
          <div className="flex justify-between">
            <span className="text-paper-400">Exchange</span>
            <span className="text-paper-200">Binance Spot</span>
          </div>
          <div className="flex justify-between">
            <span className="text-paper-400">Last login</span>
            <span className="text-paper-200">2026-04-30 09:00</span>
          </div>
        </div>
      </GlassCard>
    </div>
  );
}

function AppearanceTab() {
  const { appTheme, setAppTheme, mode, setMode, compactMode, setCompactMode, reducedMotion, setReducedMotion } = useTheme();
  const { toast } = useToast();

  const themes = [
    { id: 'ocean',     label: 'Ocean',    desc: 'Deep teal & turquoise', color: '#14b8a6' },
    { id: 'sapphire',  label: 'Sapphire', desc: 'Blue & indigo',         color: '#6366f1' },
    { id: 'emerald',   label: 'Emerald',  desc: 'Green & mint',          color: '#10b981' },
    { id: 'onyx',      label: 'Onyx',     desc: 'Monochrome slate',      color: '#94a3b8' },
  ] as const;

  return (
    <div className="space-y-6">
      <GlassCard>
        <h3 className="text-sm font-medium text-paper-200 mb-4">Color Theme</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {themes.map(t => (
            <button
              key={t.id}
              onClick={() => { setAppTheme(t.id); toast({ title: `${t.label} theme applied`, type: 'info' }); }}
              className={`p-3 rounded-xl border transition-colors text-left ${
                appTheme === t.id
                  ? 'border-turquoise bg-turquoise/5'
                  : 'border-obsidian-200 hover:border-obsidian-100'
              }`}
            >
              <div className="w-8 h-8 rounded-full mb-2" style={{ backgroundColor: t.color }} />
              <div className="text-sm font-medium text-paper-100">{t.label}</div>
              <div className="text-xs text-paper-400">{t.desc}</div>
              {appTheme === t.id && <CheckCircle className="w-3 h-3 text-turquoise mt-1" />}
            </button>
          ))}
        </div>
      </GlassCard>

      <GlassCard>
        <h3 className="text-sm font-medium text-paper-200 mb-4">Display Mode</h3>
        <div className="flex gap-3">
          {([
            { value: 'light',  label: 'Light',  icon: Sun     },
            { value: 'dark',   label: 'Dark',   icon: Moon    },
            { value: 'system', label: 'System', icon: Monitor },
          ] as const).map(m => (
            <button
              key={m.value}
              onClick={() => setMode(m.value)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border transition-colors ${
                mode === m.value
                  ? 'border-turquoise bg-turquoise/5 text-turquoise'
                  : 'border-obsidian-200 text-paper-400 hover:text-paper-200'
              }`}
            >
              <m.icon className="w-4 h-4" />
              <span className="text-sm">{m.label}</span>
            </button>
          ))}
        </div>
      </GlassCard>

      <GlassCard>
        <h3 className="text-sm font-medium text-paper-200 mb-4">Interface Options</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-paper-200">Compact Mode</div>
              <div className="text-xs text-paper-400">Reduce spacing and card padding</div>
            </div>
            <Toggle checked={compactMode} onCheckedChange={setCompactMode} />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-paper-200">Reduced Motion</div>
              <div className="text-xs text-paper-400">Disable animations for accessibility</div>
            </div>
            <Toggle checked={reducedMotion} onCheckedChange={setReducedMotion} />
          </div>
        </div>
      </GlassCard>
    </div>
  );
}

function NotificationsTab() {
  const [push, setPush]   = useState(true);
  const [email, setEmail] = useState(true);
  const [sound, setSound] = useState(false);

  const notifGroups = [
    {
      title: 'Trading Events',
      items: [
        { label: 'Trade executed',       desc: 'Paper trade opened or closed',     checked: true },
        { label: 'Signal generated',      desc: 'Strategy identifies entry signal', checked: true },
        { label: 'Strategy status change',desc: 'Active/paused/stopped updates',    checked: true },
      ],
    },
    {
      title: 'Risk Alerts',
      items: [
        { label: 'Daily loss limit',     desc: 'Approaching or breaching limit',    checked: true },
        { label: 'Drawdown alert',       desc: 'Portfolio drawdown threshold',      checked: true },
        { label: 'Regime change',        desc: 'Market regime classification shift',checked: false },
      ],
    },
    {
      title: 'System',
      items: [
        { label: 'Binance connectivity', desc: 'API connection drops or restores',  checked: true },
        { label: 'Rate limit warnings',  desc: 'API usage approaching limits',      checked: false },
      ],
    },
  ];

  return (
    <div className="space-y-6">
      <GlassCard>
        <h3 className="text-sm font-medium text-paper-200 mb-4">Notification Channels</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-paper-200">Push Notifications</div>
              <div className="text-xs text-paper-400">In-app toast notifications</div>
            </div>
            <Toggle checked={push} onCheckedChange={setPush} />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-paper-200">Email Notifications</div>
              <div className="text-xs text-paper-400">Daily digest to {'{'}your email{'}'}</div>
            </div>
            <Toggle checked={email} onCheckedChange={setEmail} />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-paper-200">Sound Alerts</div>
              <div className="text-xs text-paper-400">Audio for critical events</div>
            </div>
            <Toggle checked={sound} onCheckedChange={setSound} />
          </div>
        </div>
      </GlassCard>

      {notifGroups.map(group => (
        <GlassCard key={group.title}>
          <h3 className="text-sm font-medium text-paper-200 mb-4">{group.title}</h3>
          <div className="space-y-4">
            {group.items.map(item => (
              <div key={item.label} className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-paper-200">{item.label}</div>
                  <div className="text-xs text-paper-400">{item.desc}</div>
                </div>
                <Toggle checked={item.checked} onCheckedChange={() => {}} />
              </div>
            ))}
          </div>
        </GlassCard>
      ))}
    </div>
  );
}

function ConnectionsTab() {
  const { toast } = useToast();
  const [showKey, setShowKey] = useState(false);
  const [apiKey] = useState('vX9k••••••••••••••••••••••••••••••••••••••8mQz');

  return (
    <div className="space-y-6">
      {/* Binance Connection */}
      <GlassCard>
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-[#f3ba2f]/10 flex items-center justify-center">
              <span className="text-sm font-bold text-[#f3ba2f]">B</span>
            </div>
            <div>
              <div className="text-sm font-semibold text-paper-100">Binance Spot</div>
              <div className="text-xs text-paper-400">Crypto exchange &mdash; paper trading mode</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-gain" />
            <Badge variant="success" size="sm" dot pulsing>Connected</Badge>
          </div>
        </div>

        <div className="space-y-3">
          <div>
            <label className="text-xs text-paper-400 mb-1 block">API Key</label>
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                readOnly
                value={apiKey}
                className="w-full bg-obsidian-300 border border-obsidian-200 text-paper-200 text-sm rounded-lg px-3 py-2 pr-10 font-mono focus:outline-none"
              />
              <button
                onClick={() => setShowKey(!showKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-paper-400 hover:text-paper-200"
              >
                {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-paper-400">
            <Wifi className="w-3.5 h-3.5 text-gain" />
            <span>Spot API active &bull; WebSocket streaming &bull; Read + Trade permissions</span>
          </div>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => toast({ title: 'Connection tested', description: 'Binance API responding normally.', type: 'success' })}
            >
              Test Connection
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => toast({ title: 'API key regenerated', description: 'New key has been applied.', type: 'info' })}
            >
              <Key className="w-4 h-4 mr-1" /> Rotate Key
            </Button>
          </div>
        </div>
      </GlassCard>

      {/* Unavailable connections */}
      <GlassCard>
        <h3 className="text-sm font-medium text-paper-400 mb-3">Other Exchanges (V1 Roadmap)</h3>
        <div className="space-y-3 opacity-50">
          {['Binance Futures', 'Bybit', 'OKX', 'Kraken'].map(ex => (
            <div key={ex} className="flex items-center justify-between py-2 border-b border-obsidian-200/50 last:border-0">
              <div className="text-sm text-paper-400">{ex}</div>
              <Badge variant="neutral" size="sm">Not available in MVP</Badge>
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
}

function SecurityTab() {
  const { toast } = useToast();
  const [twoFa, setTwoFa]         = useState(false);
  const [biometric, setBiometric] = useState(false);
  const [showPin, setShowPin]     = useState(false);
  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw]         = useState('');
  const [confirmPw, setConfirmPw] = useState('');

  return (
    <div className="space-y-6">
      <GlassCard>
        <h3 className="text-sm font-medium text-paper-200 mb-4">Change Password</h3>
        <div className="space-y-3 max-w-sm">
          <div>
            <label className="text-xs text-paper-400 mb-1 block">Current Password</label>
            <Input type="password" value={currentPw} onChange={e => setCurrentPw(e.target.value)} className="w-full" />
          </div>
          <div>
            <label className="text-xs text-paper-400 mb-1 block">New Password</label>
            <Input type="password" value={newPw} onChange={e => setNewPw(e.target.value)} className="w-full" />
          </div>
          <div>
            <label className="text-xs text-paper-400 mb-1 block">Confirm New Password</label>
            <Input type="password" value={confirmPw} onChange={e => setConfirmPw(e.target.value)} className="w-full" />
          </div>
          <Button
            variant="primary"
            size="sm"
            onClick={() => toast({ title: 'Password updated', type: 'success' })}
          >
            Update Password
          </Button>
        </div>
      </GlassCard>

      <GlassCard>
        <h3 className="text-sm font-medium text-paper-200 mb-4">Two-Factor Authentication</h3>
        <div className="flex items-center justify-between mb-3">
          <div>
            <div className="text-sm text-paper-200">TOTP Authenticator</div>
            <div className="text-xs text-paper-400">Google Authenticator / Authy</div>
          </div>
          <Toggle checked={twoFa} onCheckedChange={setTwoFa} />
        </div>
        {twoFa && (
          <div className="p-3 rounded-lg bg-info/5 border border-info/20 text-xs text-info">
            Scan QR code with your authenticator app to complete 2FA setup.
          </div>
        )}
      </GlassCard>

      <GlassCard>
        <h3 className="text-sm font-medium text-paper-200 mb-4">Additional Security</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-paper-200">Biometric Unlock</div>
              <div className="text-xs text-paper-400">Use fingerprint or face ID</div>
            </div>
            <Toggle checked={biometric} onCheckedChange={setBiometric} />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-paper-200">Trading PIN</div>
              <div className="text-xs text-paper-400">Required before executing trades</div>
            </div>
            <Toggle checked={showPin} onCheckedChange={setShowPin} />
          </div>
        </div>
      </GlassCard>

      <GlassCard>
        <h3 className="text-sm font-medium text-paper-200 mb-4">API Key Management</h3>
        <p className="text-xs text-paper-400 mb-3">
          Generate read-only API keys for external monitoring tools.
          Trading keys are managed in the Connections tab.
        </p>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => toast({ title: 'API key generated', type: 'info' })}
        >
          <Key className="w-4 h-4 mr-1" /> Generate Read-Only Key
        </Button>
      </GlassCard>
    </div>
  );
}

function HelpTab() {
  return (
    <div className="space-y-6">
      <GlassCard>
        <h3 className="text-sm font-medium text-paper-200 mb-4">Keyboard Shortcuts</h3>
        <div className="space-y-1">
          <div className="grid grid-cols-2 text-xs text-paper-500 pb-2 border-b border-obsidian-200">
            <span>Keys</span>
            <span>Action</span>
          </div>
          {KEYBOARD_SHORTCUTS.map(s => (
            <div key={s.action} className="grid grid-cols-2 py-1.5 hover:bg-obsidian-300/30 rounded px-1 transition-colors">
              <div className="flex gap-1">
                {s.keys.map(k => (
                  <kbd key={k} className="px-1.5 py-0.5 rounded bg-obsidian-200 text-paper-200 text-xs font-mono">{k}</kbd>
                ))}
              </div>
              <span className="text-xs text-paper-300">{s.action}</span>
            </div>
          ))}
        </div>
      </GlassCard>

      <GlassCard>
        <h3 className="text-sm font-medium text-paper-200 mb-4">Resources</h3>
        <div className="space-y-2">
          {[
            { label: 'Documentation', desc: 'PARAVANT system docs and strategy guides' },
            { label: 'Backtest Guide', desc: 'How to run and interpret backtest results' },
            { label: 'Risk Management', desc: 'Understanding position sizing and limits' },
            { label: 'Strategy Library', desc: 'Reference guide for all 9 strategies' },
          ].map(r => (
            <div key={r.label} className="flex items-center justify-between p-3 rounded-lg hover:bg-obsidian-300/30 transition-colors cursor-pointer">
              <div>
                <div className="text-sm text-paper-200">{r.label}</div>
                <div className="text-xs text-paper-400">{r.desc}</div>
              </div>
              <span className="text-xs text-turquoise">Open</span>
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const { activeSettingsTab, navigateToSettingsTab } = useDashboard();
  const activeTab = (activeSettingsTab || 'profile') as SettingsTab;

  const TAB_CONTENT: Record<SettingsTab, React.ReactNode> = {
    profile:       <ProfileTab />,
    appearance:    <AppearanceTab />,
    notifications: <NotificationsTab />,
    connections:   <ConnectionsTab />,
    security:      <SecurityTab />,
    help:          <HelpTab />,
  };

  return (
    <motion.div
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      className="space-y-4"
    >
      <motion.div variants={fadeInUp}>
        <h1 className="text-2xl font-semibold text-paper-100">Settings</h1>
        <p className="text-sm text-paper-400 mt-1">Account, appearance, connections, and security</p>
      </motion.div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar Nav */}
        <motion.div variants={fadeInUp} className="lg:w-48 flex-shrink-0">
          <GlassCard className="p-2">
            <nav className="space-y-1">
              {TABS.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => navigateToSettingsTab(tab.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors text-left ${
                    activeTab === tab.id
                      ? 'bg-turquoise/10 text-turquoise font-medium'
                      : 'text-paper-400 hover:text-paper-200 hover:bg-obsidian-300/50'
                  }`}
                >
                  <tab.icon className="w-4 h-4 flex-shrink-0" />
                  {tab.label}
                </button>
              ))}
            </nav>
          </GlassCard>
        </motion.div>

        {/* Content */}
        <motion.div variants={fadeInUp} className="flex-1 min-w-0">
          {TAB_CONTENT[activeTab]}
        </motion.div>
      </div>
    </motion.div>
  );
}
