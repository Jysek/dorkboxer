/**
 * DorkForge v4.0 - Frontend Application
 * ========================================
 * Handles UI interactions, API communication, panel resizing,
 * and result rendering for multi-engine dork generation.
 */

(function () {
    'use strict';

    // ── State ──
    let currentEngine = 'google';
    let allDorks = [];
    let filteredDorks = [];
    let selectedRows = new Set();
    let engineConfig = null;

    // ── DOM Helpers ──
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    // ── Cached DOM References ──
    const els = {};

    function cacheElements() {
        const ids = [
            'engineSelector', 'keywordsInput', 'keywordFileUpload', 'clearKeywords',
            'operatorGrid', 'filetypeGrid', 'siteInput', 'exclusionsInput',
            'useQuotes', 'maxResults', 'generateBtn', 'searchInput', 'searchClear',
            'sortBtn', 'shuffleBtn', 'resultsEmpty', 'resultsList', 'resultCount',
            'warningsContainer', 'copyAllBtn', 'copySelectedBtn',
            'exportTxtBtn', 'exportCsvBtn', 'exportJsonBtn',
            'loadingOverlay', 'statPossibleVal', 'statGeneratedVal',
            'keywordCount', 'operatorCount', 'filetypeCount',
            'selectAllOps', 'deselectAllOps', 'selectAllFt', 'deselectAllFt',
            'configPanel', 'resultsPanel', 'resizeHandle',
        ];
        ids.forEach((id) => {
            els[id] = $('#' + id);
        });
    }

    // ── Initialize ──
    async function init() {
        cacheElements();

        try {
            const resp = await fetch('/api/config');
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            engineConfig = await resp.json();
        } catch (e) {
            console.error('Failed to load config:', e);
            toast('Failed to load configuration. Please refresh.', 'error');
            return;
        }

        setupEngineSelector();
        renderOperators();
        renderFiletypes();
        bindEvents();
        setupPanelResize();
        updateCounts();
    }

    // ── Engine Selector ──
    function setupEngineSelector() {
        const options = $$('.engine-option');
        options.forEach((opt) => {
            opt.addEventListener('click', () => {
                options.forEach((o) => o.classList.remove('engine-option--active'));
                opt.classList.add('engine-option--active');
                currentEngine = opt.dataset.engine;
                opt.querySelector('input').checked = true;
                renderOperators();
                renderFiletypes();
                updateCounts();
            });
        });
    }

    // ── Render Operators ──
    function renderOperators() {
        const eng = engineConfig?.engines?.[currentEngine];
        if (!eng || !els.operatorGrid) return;

        els.operatorGrid.innerHTML = '';
        const ops = eng.operators;

        Object.keys(ops).forEach((key) => {
            const op = ops[key];
            const chip = document.createElement('button');
            chip.type = 'button';
            chip.className = 'chip';
            chip.dataset.operator = key;
            chip.textContent = key + ':';
            chip.title = op.description || key;
            chip.setAttribute('role', 'checkbox');
            chip.setAttribute('aria-checked', 'false');
            chip.addEventListener('click', () => {
                chip.classList.toggle('chip--active');
                chip.setAttribute('aria-checked', chip.classList.contains('chip--active'));
                updateCounts();
            });
            els.operatorGrid.appendChild(chip);
        });
    }

    // ── Render Filetypes ──
    function renderFiletypes() {
        const eng = engineConfig?.engines?.[currentEngine];
        if (!eng || !els.filetypeGrid) return;

        els.filetypeGrid.innerHTML = '';
        const fts = eng.filetypes || [];

        fts.forEach((ft) => {
            const chip = document.createElement('button');
            chip.type = 'button';
            chip.className = 'chip';
            chip.dataset.filetype = ft;
            chip.textContent = '.' + ft;
            chip.setAttribute('role', 'checkbox');
            chip.setAttribute('aria-checked', 'false');
            chip.addEventListener('click', () => {
                chip.classList.toggle('chip--active');
                chip.setAttribute('aria-checked', chip.classList.contains('chip--active'));
                updateCounts();
            });
            els.filetypeGrid.appendChild(chip);
        });
    }

    // ── Event Bindings ──
    function bindEvents() {
        // Generate
        els.generateBtn?.addEventListener('click', generate);

        // Keyword input count
        els.keywordsInput?.addEventListener('input', updateCounts);

        // File upload
        els.keywordFileUpload?.addEventListener('change', handleFileUpload);

        // Clear keywords
        els.clearKeywords?.addEventListener('click', () => {
            if (els.keywordsInput) els.keywordsInput.value = '';
            updateCounts();
        });

        // Preset keywords
        $$('.preset-btn').forEach((btn) => {
            btn.addEventListener('click', () => {
                const kws = btn.dataset.keywords.split('||');
                if (!els.keywordsInput) return;
                const current = els.keywordsInput.value.trim();
                els.keywordsInput.value = current
                    ? current + '\n' + kws.join('\n')
                    : kws.join('\n');
                updateCounts();
                toast(`Added ${kws.length} keywords from preset`);
            });
        });

        // Select/Deselect All
        els.selectAllOps?.addEventListener('click', () => toggleAll(els.operatorGrid, true));
        els.deselectAllOps?.addEventListener('click', () => toggleAll(els.operatorGrid, false));
        els.selectAllFt?.addEventListener('click', () => toggleAll(els.filetypeGrid, true));
        els.deselectAllFt?.addEventListener('click', () => toggleAll(els.filetypeGrid, false));

        // Search
        els.searchInput?.addEventListener('input', () => {
            applyFilter();
            // Show/hide clear button
            if (els.searchClear) {
                els.searchClear.style.display = els.searchInput.value ? 'block' : 'none';
            }
        });

        // Search clear
        els.searchClear?.addEventListener('click', () => {
            if (els.searchInput) els.searchInput.value = '';
            els.searchClear.style.display = 'none';
            applyFilter();
        });

        // Sort / Shuffle
        els.sortBtn?.addEventListener('click', sortResults);
        els.shuffleBtn?.addEventListener('click', shuffleResults);

        // Copy
        els.copyAllBtn?.addEventListener('click', copyAll);
        els.copySelectedBtn?.addEventListener('click', copySelected);

        // Export
        els.exportTxtBtn?.addEventListener('click', () => exportDorks('txt'));
        els.exportCsvBtn?.addEventListener('click', () => exportDorks('csv'));
        els.exportJsonBtn?.addEventListener('click', () => exportDorks('json'));

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl+Enter -> Generate
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                generate();
            }
            // Escape -> Clear search
            if (e.key === 'Escape' && document.activeElement === els.searchInput) {
                els.searchInput.value = '';
                if (els.searchClear) els.searchClear.style.display = 'none';
                applyFilter();
                els.searchInput.blur();
            }
        });
    }

    // ── Panel Resize ──
    function setupPanelResize() {
        const handle = els.resizeHandle;
        const panel = els.configPanel;
        if (!handle || !panel) return;

        let isResizing = false;
        let startX = 0;
        let startWidth = 0;

        handle.addEventListener('mousedown', (e) => {
            isResizing = true;
            startX = e.clientX;
            startWidth = panel.offsetWidth;
            handle.classList.add('resize-handle--active');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            const diff = e.clientX - startX;
            const newWidth = Math.max(300, Math.min(520, startWidth + diff));
            panel.style.width = newWidth + 'px';
        });

        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                handle.classList.remove('resize-handle--active');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
            }
        });
    }

    // ── File Upload ──
    function handleFileUpload(e) {
        const file = e.target.files?.[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (ev) => {
            const text = ev.target.result;
            const lines = text.split('\n').filter((l) => l.trim());
            if (!els.keywordsInput) return;
            const current = els.keywordsInput.value.trim();
            els.keywordsInput.value = current
                ? current + '\n' + lines.join('\n')
                : lines.join('\n');
            updateCounts();
            toast(`Loaded ${lines.length} keywords from file`);
        };
        reader.onerror = () => {
            toast('Failed to read file', 'error');
        };
        reader.readAsText(file);
        e.target.value = '';
    }

    // ── Toggle All Chips ──
    function toggleAll(grid, active) {
        if (!grid) return;
        grid.querySelectorAll('.chip').forEach((c) => {
            if (active) {
                c.classList.add('chip--active');
                c.setAttribute('aria-checked', 'true');
            } else {
                c.classList.remove('chip--active');
                c.setAttribute('aria-checked', 'false');
            }
        });
        updateCounts();
    }

    // ── Update Counts ──
    function updateCounts() {
        const keywords = getKeywords();
        if (els.keywordCount) els.keywordCount.textContent = keywords.length;

        const ops = getSelectedOperators();
        if (els.operatorCount) els.operatorCount.textContent = ops.length;

        const fts = getSelectedFiletypes();
        if (els.filetypeCount) els.filetypeCount.textContent = fts.length;

        // Estimate possible combinations
        const kLen = keywords.length;
        const oLen = ops.length;
        const fLen = fts.length;
        let possible = 0;

        if (oLen > 0 && fLen > 0) {
            // (ops * keywords * filetypes) + (keywords * filetypes) for plain keyword+ft combos
            const nonFtOps = ops.filter(o => o !== 'filetype' && o !== 'ext').length;
            possible = (nonFtOps * kLen * fLen) + (kLen * fLen);
        } else if (oLen > 0) {
            possible = oLen * kLen;
        } else if (fLen > 0) {
            possible = kLen * fLen;
        } else {
            possible = kLen;
        }

        if (els.statPossibleVal) els.statPossibleVal.textContent = possible.toLocaleString();
    }

    // ── Data Extractors ──
    function getKeywords() {
        if (!els.keywordsInput) return [];
        return els.keywordsInput.value
            .split('\n')
            .map((l) => l.trim())
            .filter((l) => l.length > 0);
    }

    function getSelectedOperators() {
        if (!els.operatorGrid) return [];
        return Array.from(els.operatorGrid.querySelectorAll('.chip--active'))
            .map((c) => c.dataset.operator);
    }

    function getSelectedFiletypes() {
        if (!els.filetypeGrid) return [];
        return Array.from(els.filetypeGrid.querySelectorAll('.chip--active'))
            .map((c) => c.dataset.filetype);
    }

    // ── Generate ──
    async function generate() {
        const keywords = getKeywords();
        if (keywords.length === 0) {
            toast('Please enter at least one keyword', 'warning');
            els.keywordsInput?.focus();
            return;
        }

        const maxResultsVal = parseInt(els.maxResults?.value) || 100;

        const payload = {
            engine: currentEngine,
            keywords: keywords,
            operators: getSelectedOperators(),
            filetypes: getSelectedFiletypes(),
            site: els.siteInput?.value.trim() || '',
            use_quotes: els.useQuotes?.checked || false,
            exclusions: (els.exclusionsInput?.value || '')
                .split('\n')
                .map((l) => l.trim())
                .filter((l) => l),
            max_results: maxResultsVal,
        };

        if (els.loadingOverlay) els.loadingOverlay.style.display = 'flex';
        if (els.generateBtn) els.generateBtn.disabled = true;

        try {
            const resp = await fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!resp.ok) {
                throw new Error(`Server error (HTTP ${resp.status})`);
            }

            const result = await resp.json();

            if (result.error) {
                toast(result.error, 'error');
                return;
            }

            allDorks = result.dorks || [];
            filteredDorks = [...allDorks];
            selectedRows.clear();

            // Update stats
            if (els.statGeneratedVal) {
                els.statGeneratedVal.textContent = result.total_generated.toLocaleString();
            }
            if (els.statPossibleVal) {
                els.statPossibleVal.textContent = result.total_possible.toLocaleString();
            }

            // Warnings
            if (result.warnings?.length > 0) {
                if (els.warningsContainer) {
                    els.warningsContainer.style.display = 'block';
                    els.warningsContainer.innerHTML = result.warnings
                        .map((w) => `<div class="warning-item">${escapeHtml(w)}</div>`)
                        .join('');
                }
            } else {
                if (els.warningsContainer) els.warningsContainer.style.display = 'none';
            }

            renderResults();
            updateButtons();

            if (allDorks.length > 0) {
                toast(`Generated ${allDorks.length.toLocaleString()} dorks for ${result.engine_name}`);
            } else {
                toast('No dorks generated. Try different options.', 'warning');
            }
        } catch (e) {
            toast('Generation failed: ' + e.message, 'error');
        } finally {
            if (els.loadingOverlay) els.loadingOverlay.style.display = 'none';
            if (els.generateBtn) els.generateBtn.disabled = false;
        }
    }

    // ── Render Results ──
    function renderResults() {
        if (els.searchInput) els.searchInput.value = '';
        if (els.searchClear) els.searchClear.style.display = 'none';

        if (filteredDorks.length === 0) {
            if (els.resultsEmpty) els.resultsEmpty.style.display = 'flex';
            if (els.resultsList) els.resultsList.style.display = 'none';
            if (els.resultCount) els.resultCount.textContent = '0 dorks';
            return;
        }

        if (els.resultsEmpty) els.resultsEmpty.style.display = 'none';
        if (els.resultsList) els.resultsList.style.display = 'block';

        // Use DocumentFragment for performance
        const frag = document.createDocumentFragment();

        filteredDorks.forEach((dork, idx) => {
            frag.appendChild(createDorkRow(dork, idx + 1));
        });

        if (els.resultsList) {
            els.resultsList.innerHTML = '';
            els.resultsList.appendChild(frag);
        }

        if (els.resultCount) {
            els.resultCount.textContent = `${filteredDorks.length.toLocaleString()} dorks`;
        }
    }

    // ── Create Dork Row ──
    function createDorkRow(dork, num) {
        const row = document.createElement('div');
        row.className = 'dork-row';
        row.dataset.index = num - 1;
        row.setAttribute('role', 'row');

        // Line number
        const numEl = document.createElement('div');
        numEl.className = 'dork-row__num';
        numEl.textContent = num;

        // Dork text with syntax highlighting
        const textEl = document.createElement('div');
        textEl.className = 'dork-row__text';
        textEl.innerHTML = highlightDork(dork);

        // Copy button
        const copyEl = document.createElement('button');
        copyEl.type = 'button';
        copyEl.className = 'dork-row__copy';
        copyEl.innerHTML = '\u{1F4CB}';
        copyEl.title = 'Copy this dork';
        copyEl.setAttribute('aria-label', 'Copy dork to clipboard');
        copyEl.addEventListener('click', (e) => {
            e.stopPropagation();
            copyToClipboard(dork);
            toast('Copied to clipboard');
        });

        // Row click for selection
        row.addEventListener('click', () => {
            const idx = parseInt(row.dataset.index);
            if (selectedRows.has(idx)) {
                selectedRows.delete(idx);
                row.classList.remove('dork-row--selected');
            } else {
                selectedRows.add(idx);
                row.classList.add('dork-row--selected');
            }
            updateButtons();
        });

        row.appendChild(numEl);
        row.appendChild(textEl);
        row.appendChild(copyEl);

        return row;
    }

    // ── Syntax Highlighting ──
    function highlightDork(dork) {
        let html = escapeHtml(dork);

        // Highlight operators (word:value)
        html = html.replace(
            /\b(site|intitle|allintitle|inurl|allinurl|intext|allintext|inbody|filetype|ext|cache|link|related|info|define|inanchor|feed|hasfeed|contains|ip|language|location|prefer|hostname):(\S+)/gi,
            (match, op, val) => {
                const opLower = op.toLowerCase();
                if (opLower === 'filetype' || opLower === 'ext') {
                    return `<span class="op">${op}:</span><span class="ft">${val}</span>`;
                }
                return `<span class="op">${op}:</span><span class="kw">${val}</span>`;
            }
        );

        // Highlight quoted strings
        html = html.replace(
            /&quot;([^&]*)&quot;/g,
            '<span class="qt">&quot;$1&quot;</span>'
        );

        // Highlight negations
        html = html.replace(
            /(^|\s)(-\S+)/g,
            '$1<span class="neg">$2</span>'
        );

        // Highlight NOT keyword (for Bing/Yahoo)
        html = html.replace(
            /(^|\s)(NOT\s+\S+)/g,
            '$1<span class="neg">$2</span>'
        );

        return html.trim();
    }

    // ── Filter ──
    function applyFilter() {
        const term = els.searchInput?.value.trim().toLowerCase() || '';

        if (!term) {
            filteredDorks = [...allDorks];
        } else {
            filteredDorks = allDorks.filter((d) => d.toLowerCase().includes(term));
        }

        selectedRows.clear();
        renderResults();
        updateButtons();

        // Highlight search term in rendered results
        if (term && els.resultsList) {
            const escapedTerm = escapeRegex(escapeHtml(term));
            els.resultsList.querySelectorAll('.dork-row__text').forEach((el) => {
                el.innerHTML = el.innerHTML.replace(
                    new RegExp(`(${escapedTerm})`, 'gi'),
                    '<span class="highlight">$1</span>'
                );
            });
        }
    }

    // ── Sort / Shuffle ──
    function sortResults() {
        filteredDorks.sort((a, b) => a.localeCompare(b));
        selectedRows.clear();
        renderResults();
        updateButtons();
    }

    function shuffleResults() {
        for (let i = filteredDorks.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [filteredDorks[i], filteredDorks[j]] = [filteredDorks[j], filteredDorks[i]];
        }
        selectedRows.clear();
        renderResults();
        updateButtons();
    }

    // ── Copy ──
    function copyAll() {
        if (filteredDorks.length === 0) return;
        copyToClipboard(filteredDorks.join('\n'));
        toast(`Copied ${filteredDorks.length.toLocaleString()} dorks`);
    }

    function copySelected() {
        if (selectedRows.size === 0) return;
        const selected = [...selectedRows]
            .sort((a, b) => a - b)
            .map((idx) => filteredDorks[idx])
            .filter(Boolean);
        copyToClipboard(selected.join('\n'));
        toast(`Copied ${selected.length} selected dorks`);
    }

    async function copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
        } catch {
            // Fallback for non-secure contexts
            const ta = document.createElement('textarea');
            ta.value = text;
            ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px;';
            document.body.appendChild(ta);
            ta.select();
            try { document.execCommand('copy'); } catch { /* ignore */ }
            document.body.removeChild(ta);
        }
    }

    // ── Export ──
    async function exportDorks(format) {
        if (filteredDorks.length === 0) return;

        const eng = engineConfig?.engines?.[currentEngine];
        const engineName = eng?.name || currentEngine;

        try {
            const resp = await fetch('/api/export', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    dorks: filteredDorks,
                    format: format,
                    engine_name: engineName,
                }),
            });

            if (!resp.ok) throw new Error(`Export failed (HTTP ${resp.status})`);

            const blob = await resp.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `dorkforge_export.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            toast(`Exported ${filteredDorks.length.toLocaleString()} dorks as ${format.toUpperCase()}`);
        } catch (e) {
            toast('Export failed: ' + e.message, 'error');
        }
    }

    // ── Update Buttons ──
    function updateButtons() {
        const hasDorks = filteredDorks.length > 0;
        const hasSelected = selectedRows.size > 0;

        if (els.copyAllBtn) els.copyAllBtn.disabled = !hasDorks;
        if (els.copySelectedBtn) els.copySelectedBtn.disabled = !hasSelected;
        if (els.exportTxtBtn) els.exportTxtBtn.disabled = !hasDorks;
        if (els.exportCsvBtn) els.exportCsvBtn.disabled = !hasDorks;
        if (els.exportJsonBtn) els.exportJsonBtn.disabled = !hasDorks;
    }

    // ── Toast ──
    function toast(message, type = 'success') {
        const existing = document.querySelector('.toast');
        if (existing) existing.remove();

        const el = document.createElement('div');
        el.className = 'toast';
        el.setAttribute('role', 'alert');
        el.textContent = message;

        if (type === 'warning') el.style.background = 'var(--warning)';
        else if (type === 'error') el.style.background = 'var(--error)';

        document.body.appendChild(el);
        setTimeout(() => {
            if (el.parentNode) el.remove();
        }, 2700);
    }

    // ── Utilities ──
    function escapeHtml(str) {
        const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
        return str.replace(/[&<>"']/g, (m) => map[m]);
    }

    function escapeRegex(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    // ── Boot ──
    document.addEventListener('DOMContentLoaded', init);
})();
