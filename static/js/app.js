/**
 * DorkForge - Frontend Application
 * ==================================
 * Handles UI interactions, API communication, and result rendering
 * for multi-engine dork generation.
 */

(function () {
    'use strict';

    // ── State ──
    let currentEngine = 'google';
    let allDorks = [];
    let filteredDorks = [];
    let selectedRows = new Set();
    let engineConfig = null;

    // ── DOM References ──
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const els = {
        engineSelector: $('#engineSelector'),
        keywordsInput: $('#keywordsInput'),
        keywordFileUpload: $('#keywordFileUpload'),
        clearKeywords: $('#clearKeywords'),
        operatorGrid: $('#operatorGrid'),
        filetypeGrid: $('#filetypeGrid'),
        siteInput: $('#siteInput'),
        exclusionsInput: $('#exclusionsInput'),
        useQuotes: $('#useQuotes'),
        maxResults: $('#maxResults'),
        generateBtn: $('#generateBtn'),
        searchInput: $('#searchInput'),
        sortBtn: $('#sortBtn'),
        shuffleBtn: $('#shuffleBtn'),
        resultsEmpty: $('#resultsEmpty'),
        resultsList: $('#resultsList'),
        resultCount: $('#resultCount'),
        warningsContainer: $('#warningsContainer'),
        copyAllBtn: $('#copyAllBtn'),
        copySelectedBtn: $('#copySelectedBtn'),
        exportTxtBtn: $('#exportTxtBtn'),
        exportCsvBtn: $('#exportCsvBtn'),
        exportJsonBtn: $('#exportJsonBtn'),
        loadingOverlay: $('#loadingOverlay'),
        statPossibleVal: $('#statPossibleVal'),
        statGeneratedVal: $('#statGeneratedVal'),
        keywordCount: $('#keywordCount'),
        operatorCount: $('#operatorCount'),
        filetypeCount: $('#filetypeCount'),
        selectAllOps: $('#selectAllOps'),
        deselectAllOps: $('#deselectAllOps'),
        selectAllFt: $('#selectAllFt'),
        deselectAllFt: $('#deselectAllFt'),
    };

    // ── Initialize ──
    async function init() {
        try {
            const resp = await fetch('/api/config');
            engineConfig = await resp.json();
        } catch (e) {
            console.error('Failed to load config:', e);
            return;
        }

        setupEngineSelector();
        renderOperators();
        renderFiletypes();
        bindEvents();
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
        const eng = engineConfig.engines[currentEngine];
        if (!eng) return;

        els.operatorGrid.innerHTML = '';
        const ops = eng.operators;

        Object.keys(ops).forEach((key) => {
            const op = ops[key];
            const chip = document.createElement('div');
            chip.className = 'chip';
            chip.dataset.operator = key;
            chip.textContent = key + ':';
            chip.title = op.description;
            chip.addEventListener('click', () => {
                chip.classList.toggle('chip--active');
                updateCounts();
            });
            els.operatorGrid.appendChild(chip);
        });
    }

    // ── Render Filetypes ──
    function renderFiletypes() {
        const eng = engineConfig.engines[currentEngine];
        if (!eng) return;

        els.filetypeGrid.innerHTML = '';
        const fts = eng.filetypes || [];

        fts.forEach((ft) => {
            const chip = document.createElement('div');
            chip.className = 'chip';
            chip.dataset.filetype = ft;
            chip.textContent = '.' + ft;
            chip.addEventListener('click', () => {
                chip.classList.toggle('chip--active');
                updateCounts();
            });
            els.filetypeGrid.appendChild(chip);
        });
    }

    // ── Event Bindings ──
    function bindEvents() {
        // Generate
        els.generateBtn.addEventListener('click', generate);

        // Keyword input count
        els.keywordsInput.addEventListener('input', updateCounts);

        // File upload
        els.keywordFileUpload.addEventListener('change', handleFileUpload);

        // Clear keywords
        els.clearKeywords.addEventListener('click', () => {
            els.keywordsInput.value = '';
            updateCounts();
        });

        // Preset keywords
        $$('.preset-btn').forEach((btn) => {
            btn.addEventListener('click', () => {
                const kws = btn.dataset.keywords.split('||');
                const current = els.keywordsInput.value.trim();
                if (current) {
                    els.keywordsInput.value = current + '\n' + kws.join('\n');
                } else {
                    els.keywordsInput.value = kws.join('\n');
                }
                updateCounts();
            });
        });

        // Select/Deselect All
        els.selectAllOps.addEventListener('click', () => toggleAll(els.operatorGrid, true));
        els.deselectAllOps.addEventListener('click', () => toggleAll(els.operatorGrid, false));
        els.selectAllFt.addEventListener('click', () => toggleAll(els.filetypeGrid, true));
        els.deselectAllFt.addEventListener('click', () => toggleAll(els.filetypeGrid, false));

        // Search
        els.searchInput.addEventListener('input', applyFilter);

        // Sort / Shuffle
        els.sortBtn.addEventListener('click', sortResults);
        els.shuffleBtn.addEventListener('click', shuffleResults);

        // Copy
        els.copyAllBtn.addEventListener('click', copyAll);
        els.copySelectedBtn.addEventListener('click', copySelected);

        // Export
        els.exportTxtBtn.addEventListener('click', () => exportDorks('txt'));
        els.exportCsvBtn.addEventListener('click', () => exportDorks('csv'));
        els.exportJsonBtn.addEventListener('click', () => exportDorks('json'));

        // Keyboard shortcut
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                generate();
            }
        });
    }

    // ── File Upload ──
    function handleFileUpload(e) {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (ev) => {
            const text = ev.target.result;
            const lines = text.split('\n').filter((l) => l.trim());
            const current = els.keywordsInput.value.trim();
            if (current) {
                els.keywordsInput.value = current + '\n' + lines.join('\n');
            } else {
                els.keywordsInput.value = lines.join('\n');
            }
            updateCounts();
            toast(`Loaded ${lines.length} keywords from file`);
        };
        reader.readAsText(file);
        e.target.value = '';
    }

    // ── Toggle All Chips ──
    function toggleAll(grid, active) {
        grid.querySelectorAll('.chip').forEach((c) => {
            if (active) c.classList.add('chip--active');
            else c.classList.remove('chip--active');
        });
        updateCounts();
    }

    // ── Update Counts ──
    function updateCounts() {
        const keywords = getKeywords();
        els.keywordCount.textContent = keywords.length;

        const ops = getSelectedOperators();
        els.operatorCount.textContent = ops.length;

        const fts = getSelectedFiletypes();
        els.filetypeCount.textContent = fts.length;

        // Estimate possible combinations
        let possible = 0;
        const kLen = keywords.length || 0;
        const oLen = ops.length || 0;
        const fLen = fts.length || 0;

        if (oLen > 0 && fLen > 0) {
            // op*kw*ft + kw*ft
            possible = (oLen * kLen * fLen) + (kLen * fLen);
        } else if (oLen > 0) {
            possible = oLen * kLen;
        } else if (fLen > 0) {
            possible = kLen * fLen;
        } else {
            possible = kLen;
        }

        els.statPossibleVal.textContent = possible.toLocaleString();
    }

    // ── Data Extractors ──
    function getKeywords() {
        return els.keywordsInput.value
            .split('\n')
            .map((l) => l.trim())
            .filter((l) => l.length > 0);
    }

    function getSelectedOperators() {
        return Array.from(els.operatorGrid.querySelectorAll('.chip--active'))
            .map((c) => c.dataset.operator);
    }

    function getSelectedFiletypes() {
        return Array.from(els.filetypeGrid.querySelectorAll('.chip--active'))
            .map((c) => c.dataset.filetype);
    }

    // ── Generate ──
    async function generate() {
        const keywords = getKeywords();
        if (keywords.length === 0) {
            toast('Please enter at least one keyword', 'warning');
            els.keywordsInput.focus();
            return;
        }

        const payload = {
            engine: currentEngine,
            keywords: keywords,
            operators: getSelectedOperators(),
            filetypes: getSelectedFiletypes(),
            site: els.siteInput.value.trim(),
            use_quotes: els.useQuotes.checked,
            exclusions: els.exclusionsInput.value
                .split('\n')
                .map((l) => l.trim())
                .filter((l) => l),
            max_results: parseInt(els.maxResults.value) || 100,
        };

        els.loadingOverlay.style.display = 'flex';
        els.generateBtn.disabled = true;

        try {
            const resp = await fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            const result = await resp.json();

            if (result.error) {
                toast(result.error, 'error');
                return;
            }

            allDorks = result.dorks || [];
            filteredDorks = [...allDorks];
            selectedRows.clear();

            // Stats
            els.statGeneratedVal.textContent = result.total_generated.toLocaleString();
            els.statPossibleVal.textContent = result.total_possible.toLocaleString();

            // Warnings
            if (result.warnings && result.warnings.length > 0) {
                els.warningsContainer.style.display = 'block';
                els.warningsContainer.innerHTML = result.warnings
                    .map((w) => `<div class="warning-item">${escapeHtml(w)}</div>`)
                    .join('');
            } else {
                els.warningsContainer.style.display = 'none';
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
            els.loadingOverlay.style.display = 'none';
            els.generateBtn.disabled = false;
        }
    }

    // ── Render Results ──
    function renderResults() {
        els.searchInput.value = '';

        if (filteredDorks.length === 0) {
            els.resultsEmpty.style.display = 'flex';
            els.resultsList.style.display = 'none';
            els.resultCount.textContent = '0 dorks';
            return;
        }

        els.resultsEmpty.style.display = 'none';
        els.resultsList.style.display = 'block';

        // Use DocumentFragment for performance
        const frag = document.createDocumentFragment();

        filteredDorks.forEach((dork, idx) => {
            const row = createDorkRow(dork, idx + 1);
            frag.appendChild(row);
        });

        els.resultsList.innerHTML = '';
        els.resultsList.appendChild(frag);

        els.resultCount.textContent = `${filteredDorks.length.toLocaleString()} dorks`;
    }

    // ── Create Dork Row ──
    function createDorkRow(dork, num) {
        const row = document.createElement('div');
        row.className = 'dork-row';
        row.dataset.index = num - 1;

        // Line number
        const numEl = document.createElement('div');
        numEl.className = 'dork-row__num';
        numEl.textContent = num;

        // Dork text with syntax highlighting
        const textEl = document.createElement('div');
        textEl.className = 'dork-row__text';
        textEl.innerHTML = highlightDork(dork);

        // Copy button
        const copyEl = document.createElement('div');
        copyEl.className = 'dork-row__copy';
        copyEl.innerHTML = '&#128203;';
        copyEl.title = 'Copy this dork';
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
        // Escape first
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
            /(?:^|\s)(-\S+)/g,
            (match, neg) => ` <span class="neg">${neg}</span>`
        );

        return html.trim();
    }

    // ── Filter ──
    function applyFilter() {
        const term = els.searchInput.value.trim().toLowerCase();

        if (!term) {
            filteredDorks = [...allDorks];
        } else {
            filteredDorks = allDorks.filter((d) => d.toLowerCase().includes(term));
        }

        selectedRows.clear();
        renderResults();
        updateButtons();

        // Highlight search term
        if (term) {
            els.resultsList.querySelectorAll('.dork-row__text').forEach((el) => {
                el.innerHTML = el.innerHTML.replace(
                    new RegExp(`(${escapeRegex(escapeHtml(term))})`, 'gi'),
                    '<span class="highlight">$1</span>'
                );
            });
        }
    }

    // ── Sort / Shuffle ──
    function sortResults() {
        filteredDorks.sort();
        selectedRows.clear();
        renderResults();
    }

    function shuffleResults() {
        for (let i = filteredDorks.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [filteredDorks[i], filteredDorks[j]] = [filteredDorks[j], filteredDorks[i]];
        }
        selectedRows.clear();
        renderResults();
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
            const ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed';
            ta.style.left = '-9999px';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
        }
    }

    // ── Export ──
    async function exportDorks(format) {
        if (filteredDorks.length === 0) return;

        const eng = engineConfig.engines[currentEngine];
        const engineName = eng ? eng.name : currentEngine;

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

        els.copyAllBtn.disabled = !hasDorks;
        els.copySelectedBtn.disabled = !hasSelected;
        els.exportTxtBtn.disabled = !hasDorks;
        els.exportCsvBtn.disabled = !hasDorks;
        els.exportJsonBtn.disabled = !hasDorks;
    }

    // ── Toast ──
    function toast(message, type = 'success') {
        const existing = document.querySelector('.toast');
        if (existing) existing.remove();

        const el = document.createElement('div');
        el.className = 'toast';
        el.textContent = message;

        if (type === 'warning') el.style.background = 'var(--warning)';
        else if (type === 'error') el.style.background = 'var(--error)';

        document.body.appendChild(el);
        setTimeout(() => el.remove(), 2700);
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
