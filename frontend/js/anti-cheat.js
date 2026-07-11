/**
 * Anti-Cheat System for Mock AI Interview
 * 
 * Features:
 * 1. Detects when the user switches tabs/windows during an active interview
 * 2. Prevents copy/paste operations during recording
 * 3. Monitors focus changes
 * 4. Warns and flags suspicious activity
 */

const antiCheat = {
    state: {
        isInterviewActive: false,
        tabSwitchCount: 0,
        maxAllowedSwitches: 3,
        warnings: [],
        isLocked: false,
        startTime: null
    },

    /**
     * Initialize the anti-cheat system
     */
    init() {
        this.setupVisibilityDetection();
        this.setupCopyPastePrevention();
        this.setupFocusDetection();
        console.log('Anti-cheat system initialized');
    },

    /**
     * Start monitoring for the interview session
     */
    startMonitoring() {
        this.state.isInterviewActive = true;
        this.state.tabSwitchCount = 0;
        this.state.warnings = [];
        this.state.isLocked = false;
        this.state.startTime = Date.now();
        
        // Show anti-cheat indicator in the UI
        this.showAntiCheatIndicator();
        
        console.log('Anti-cheat monitoring started');
    },

    /**
     * Stop monitoring when interview ends
     */
    stopMonitoring() {
        this.state.isInterviewActive = false;
        this.hideAntiCheatIndicator();
        console.log('Anti-cheat monitoring stopped');
    },

    /**
     * Detect when user switches tabs or the window loses focus
     */
    setupVisibilityDetection() {
        document.addEventListener('visibilitychange', () => {
            if (this.state.isInterviewActive && !this.state.isLocked) {
                if (document.hidden) {
                    this.handleTabSwitch('Tab/window was hidden (user switched away)');
                }
            }
        });

        // Also detect via window blur for better coverage
        window.addEventListener('blur', () => {
            if (this.state.isInterviewActive && !this.state.isLocked) {
                this.handleTabSwitch('Window lost focus');
            }
        });
    },

    /**
     * Handle a tab switch or focus loss event
     */
    handleTabSwitch(reason) {
        this.state.tabSwitchCount++;
        
        const warning = {
            count: this.state.tabSwitchCount,
            reason: reason,
            timestamp: new Date().toISOString(),
            timeSinceStart: Math.floor((Date.now() - this.state.startTime) / 1000)
        };
        
        this.state.warnings.push(warning);
        
        // Show warning to user
        this.showTabSwitchWarning(warning);
        
        // If exceeded max allowed switches, flag the interview
        if (this.state.tabSwitchCount >= this.state.maxAllowedSwitches) {
            this.flagSuspiciousActivity();
        }
    },

    /**
     * Show a warning overlay when tab switch is detected
     */
    showTabSwitchWarning(warning) {
        const remaining = this.state.maxAllowedSwitches - this.state.tabSwitchCount;
        const warningEl = document.createElement('div');
        warningEl.className = 'anti-cheat-warning';
        warningEl.id = `ac-warning-${warning.count}`;
        warningEl.innerHTML = `
            <div class="ac-warning-content">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                    <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
                <div class="ac-warning-text">
                    <strong>⚠️ Tab Switch Detected!</strong>
                    <p>You switched away from the interview window. 
                    ${remaining > 0 ? `You have ${remaining} more warning(s) before your session is flagged.` : 'Your session integrity has been compromised.'}</p>
                </div>
                <button class="btn btn-secondary ac-dismiss-btn" onclick="this.parentElement.parentElement.remove()">Dismiss</button>
            </div>
        `;
        
        // Insert at the top of the interview view
        const interviewView = document.getElementById('interview-view');
        if (interviewView) {
            interviewView.prepend(warningEl);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                const el = document.getElementById(`ac-warning-${warning.count}`);
                if (el) el.remove();
            }, 5000);
        }
    },

    /**
     * Flag the session as suspicious if too many tab switches
     */
    flagSuspiciousActivity() {
        this.state.isLocked = true;
        
        // Show a locked overlay
        const overlay = document.createElement('div');
        overlay.className = 'anti-cheat-overlay';
        overlay.id = 'ac-locked-overlay';
        overlay.innerHTML = `
            <div class="ac-overlay-content">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="1.5">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                </svg>
                <h2>Session Flagged</h2>
                <p>Multiple tab switches detected. This interview session has been flagged for integrity review.</p>
                <p class="ac-detail">You may continue, but your scores will include a note about potential integrity concerns.</p>
                <button class="btn btn-primary" onclick="antiCheat.dismissLock()">Continue Anyway</button>
            </div>
        `;
        
        document.body.appendChild(overlay);
        
        // Log the flags in the interview results
        this.saveCheatFlags();
    },

    /**
     * Dismiss the lock overlay
     */
    dismissLock() {
        const overlay = document.getElementById('ac-locked-overlay');
        if (overlay) overlay.remove();
        this.state.isLocked = false;
    },

    /**
     * Save cheat flags to be sent with interview submission
     */
    saveCheatFlags() {
        // These will be retrieved when submitting the interview
        const flags = {
            tab_switches: this.state.tabSwitchCount,
            warnings: this.state.warnings,
            total_time_seconds: Math.floor((Date.now() - this.state.startTime) / 1000)
        };
        
        // Store on interview state for submission
        if (window.interview && window.interview.state) {
            window.interview.state.antiCheatFlags = flags;
        }
    },

    /**
     * Prevent copy/paste during recording
     */
    setupCopyPastePrevention() {
        document.addEventListener('copy', (e) => {
            if (this.state.isInterviewActive) {
                e.preventDefault();
                this.showMiniToast('Copying is disabled during the interview');
            }
        });

        document.addEventListener('paste', (e) => {
            if (this.state.isInterviewActive) {
                e.preventDefault();
                this.showMiniToast('Pasting is disabled during the interview');
            }
        });

        document.addEventListener('cut', (e) => {
            if (this.state.isInterviewActive) {
                e.preventDefault();
            }
        });

        // Also disable right-click context menu
        document.addEventListener('contextmenu', (e) => {
            if (this.state.isInterviewActive) {
                e.preventDefault();
            }
        });
    },

    /**
     * Detect when the window focus is regained
     */
    setupFocusDetection() {
        window.addEventListener('focus', () => {
            if (this.state.isInterviewActive && this.state.tabSwitchCount > 0) {
                // Log that user returned to the interview
                console.log(`User returned to interview after ${this.state.tabSwitchCount} tab switch(es)`);
            }
        });
    },

    /**
     * Show anti-cheat badge indicator
     */
    showAntiCheatIndicator() {
        // Remove existing indicator if any
        this.hideAntiCheatIndicator();
        
        const indicator = document.createElement('div');
        indicator.className = 'anti-cheat-badge';
        indicator.id = 'ac-indicator';
        indicator.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
            <span>Anti-Cheat Active</span>
        `;
        
        const topbar = document.querySelector('.topbar');
        if (topbar) {
            topbar.appendChild(indicator);
        }
    },

    /**
     * Hide anti-cheat badge indicator
     */
    hideAntiCheatIndicator() {
        const indicator = document.getElementById('ac-indicator');
        if (indicator) indicator.remove();
    },

    /**
     * Show a small toast notification
     */
    showMiniToast(message) {
        const toast = document.createElement('div');
        toast.className = 'ac-toast';
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed; bottom: 20px; right: 20px; 
            background: rgba(239, 68, 68, 0.9); color: white; 
            padding: 10px 20px; border-radius: 8px; 
            font-size: 0.85rem; z-index: 9999;
            animation: fadeSlideIn 0.3s ease;
        `;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    },

    /**
     * Get integrity report for interview submission
     */
    getIntegrityReport() {
        return {
            tab_switches: this.state.tabSwitchCount,
            warnings: this.state.warnings,
            is_flagged: this.state.tabSwitchCount >= this.state.maxAllowedSwitches,
            session_duration_seconds: Math.floor((Date.now() - this.state.startTime) / 1000)
        };
    }
};

// Initialize anti-cheat on page load
document.addEventListener('DOMContentLoaded', () => {
    antiCheat.init();
});