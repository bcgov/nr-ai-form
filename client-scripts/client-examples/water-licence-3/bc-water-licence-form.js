// Tab switching logic: simple accessible behaviour
(function () {
    const tabButtons = document.querySelectorAll('.tab-button');
    const panels = document.querySelectorAll('.tab-panel');

    function activate(targetId, button) {
        panels.forEach(p => p.classList.toggle('active', p.id === targetId));
        tabButtons.forEach(b => b.classList.toggle('active', b === button));
        // set focus to first input in panel for convenience
        const panel = document.getElementById(targetId);
        if (panel) {
            const focusable = panel.querySelector('input, select, textarea, button');
            if (focusable) focusable.focus();
        }
    }

    tabButtons.forEach(btn => {
        btn.addEventListener('click', function () {
            activate(this.getAttribute('data-target'), this);
        });
    });
})();