(function() {
    function applySettings() {
        const darkMode = localStorage.getItem('darkMode') === 'true';
        if (darkMode) {
            document.documentElement.classList.add('dark-mode');
        } else {
            document.documentElement.classList.remove('dark-mode');
        }
        
        const fontSize = localStorage.getItem('fontSize') || '16';
        const multiplier = fontSize / 16;
        document.documentElement.style.setProperty('--font-size-multiplier', multiplier, 'important');
        
        document.body.style.setProperty('--font-size-multiplier', multiplier, 'important');
        
        const lineSpacing = localStorage.getItem('lineSpacing') || '1.5';
        document.documentElement.style.setProperty('--line-spacing', lineSpacing, 'important');
        document.body.style.setProperty('--line-spacing', lineSpacing, 'important');
    }
    
    applySettings();
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', applySettings);
    }
    
    window.addEventListener('load', applySettings);
    window.addEventListener('storage', applySettings);
})();
