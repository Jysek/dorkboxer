/**
 * DorkForge v5.0 - Frontend Application
 * ========================================
 * Handles UI interactions, API communication, panel resizing,
 * virtual rendering for large result sets, and result management
 * for multi-engine dork generation.
 */

(function () {
    'use strict';

    // -- Constants --
    const VIRTUAL_ROW_HEIGHT = 32;
    const VIRTUAL_OVERSCAN = 20;
    const RENDER_CHUNK_LIMIT = 5000;

    // -- State --
    let currentEngine = 'google';
    let allDorks = [];
    let filteredDorks = [];
    let selectedRows = new Set();
    let engineConfig = null;
    let sortAscending = true;
    let useVirtualScroll = false;

    // -- DOM Helpers --
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    // -- Cached DOM References --
    const els = {};

    function cacheElements() {
        const ids = [
            'engineSelector', 'keywordsInput', 'keywordFileUpload', 'clearKeywords',
            'operatorGrid', 'filetypeGrid', 'siteInput', 'exclusionsInput',
            'useQuotes', 'generateAll', 'maxResults', 'maxResultsGroup',
            'maxResultsHint', 'generateBtn', 'searchInput', 'searchClear',
            'sortBtn', 'shuffleBtn', 'resultsEmpty', 'resultsList', 'resultCount',
            'warningsContainer', 'copyAllBtn', 'copySelectedBtn',
            'exportTxtBtn', 'exportCsvBtn', 'exportJsonBtn',
            'loadingOverlay', 'loadingSubtext',
            'statPossibleVal', 'statGeneratedVal',
            'keywordCount', 'operatorCount', 'filetypeCount',
            'selectAllOps', 'deselectAllOps', 'selectAllFt', 'deselectAllFt',
            'configPanel', 'resultsPanel', 'resizeHandle', 'resultsBody',
        ];
        ids.forEach((id) => {
            els[id] = document.getElementById(id);
        });
    }

    // -- Initialize --
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
        syncGenerateAllUI();
    }

    // -- Engine Selector --
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

    // -- Render Operators --
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

    // -- Render Filetypes --
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

    // -- Event Bindings --
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

        // Generate All toggle
        els.generateAll?.addEventListener('change', syncGenerateAllUI);

        // Search
        els.searchInput?.addEventListener('input', () => {
            applyFilter();
            if (els.searchClear) {
                els.searchClear.style.display = els.searchInput.value ? 'block' : 'none';
            }
        });

        // Search clear
        els.searchClear?.addEventListener('click', () => {
            if (els.searchInput) els.searchInput.value = '';
            if (els.searchClear) els.searchClear.style.display = 'none';
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
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                generate();
            }
            if (e.key === 'Escape' && document.activeElement === els.searchInput) {
                els.searchInput.value = '';
                if (els.searchClear) els.searchClear.style.display = 'none';
                applyFilter();
                els.searchInput.blur();
            }
        });
    }

    // -- Generate All UI sync --
    function syncGenerateAllUI() {
        const checked = els.generateAll?.checked || false;
        if (els.maxResults) {
            els.maxResults.disabled = checked;
            if (checked) {
                els.maxResults.dataset.prevValue = els.maxResults.value;
                els.maxResults.value = '0';
            } else {
                els.maxResults.value = els.maxResults.dataset.prevValue || '100';
            }
        }
    }

    // -- Panel Resize --
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

    // -- File Upload --
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
        reader.onerror = () => toast('Failed to read file', 'error');
        reader.readAsText(file);
        e.target.value = '';
    }

    // -- Toggle All Chips --
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

    // -- Update Counts --
    function updateCounts() {
        const keywords = getKeywords();
        if (els.keywordCount) els.keywordCount.textContent = keywords.length;

        const ops = getSelectedOperators();
        if (els.operatorCount) els.operatorCount.textContent = ops.length;

        const fts = getSelectedFiletypes();
        if (els.filetypeCount) els.filetypeCount.textContent = fts.length;

        // Estimate possible combinations (matches backend logic)
        const kLen = keywords.length;
        const nonFtOps = ops.filter((o) => o !== 'filetype' && o !== 'ext' && o !== 'mime');
        const oLen = nonFtOps.length;
        const fLen = fts.length;
        let possible = 0;

        if (oLen > 0 && fLen > 0) {
            possible += oLen * kLen * fLen;       // single op + kw + ft
            possible += kLen * fLen;              // bare kw + ft
            if (oLen >= 2) {
                const pairs = oLen * (oLen - 1) / 2;
                possible += pairs * kLen;          // op pair + kw
                possible += pairs * kLen * fLen;   // op pair + kw + ft
            }
        } else if (oLen > 0) {
            possible += oLen * kLen;
            if (oLen >= 2) {
                const pairs = oLen * (oLen - 1) / 2;
                possible += pairs * kLen;
            }
        } else if (fLen > 0) {
            possible += kLen * fLen;
        } else {
            possible += kLen;
        }

        if (els.statPossibleVal) els.statPossibleVal.textContent = possible.toLocaleString();
    }

    // -- Data Extractors --
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

    // -- Generate --
    async function generate() {
        const keywords = getKeywords();
        if (keywords.length === 0) {
            toast('Please enter at least one keyword', 'warning');
            els.keywordsInput?.focus();
            return;
        }

        const generateAllChecked = els.generateAll?.checked || false;
        let maxResultsVal = parseInt(els.maxResults?.value, 10);
        if (isNaN(maxResultsVal) || maxResultsVal < 0) maxResultsVal = 100;
        if (generateAllChecked) maxResultsVal = 0;

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
        if (els.loadingSubtext) {
            els.loadingSubtext.textContent = maxResultsVal === 0
                ? 'Generating ALL combinations - this may take a moment...'
                : 'This may take a moment for large queries';
        }
        if (els.generateBtn) els.generateBtn.disabled = true;

        try {
            const resp = await fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!resp.ok) throw new Error(`Server error (HTTP ${resp.status})`);

            const result = await resp.json();

            if (result.error) {
                toast(result.error, 'error');
                return;
            }

            allDorks = result.dorks || [];
            filteredDorks = [...allDorks];
            selectedRows.clear();

            // Decide rendering strategy based on result size
            useVirtualScroll = filteredDorks.length > RENDER_CHUNK_LIMIT;

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

    // -- Render Results --
    function renderResults() {
        if (els.searchInput) els.searchInput.value = '';
        if (els.searchClear) els.searchClear.style.display = 'none';
        renderFilteredResults();
    }

    // -- Render Filtered Results --
    function renderFilteredResults() {
        if (filteredDorks.length === 0) {
            if (els.resultsEmpty) els.resultsEmpty.style.display = 'flex';
            if (els.resultsList) els.resultsList.style.display = 'none';
            if (els.resultCount) els.resultCount.textContent = '0 dorks';
            return;
        }

        if (els.resultsEmpty) els.resultsEmpty.style.display = 'none';
        if (els.resultsList) els.resultsList.style.display = 'block';

        if (useVirtualScroll) {
            renderVirtual();
        } else {
            renderDirect();
        }

        if (els.resultCount) {
            els.resultCount.textContent = `${filteredDorks.length.toLocaleString()} dorks`;
        }
    }

    // -- Direct DOM rendering (for manageable sizes) --
    function renderDirect() {
        const frag = document.createDocumentFragment();
        filteredDorks.forEach((dork, idx) => {
            frag.appendChild(createDorkRow(dork, idx + 1));
        });
        if (els.resultsList) {
            els.resultsList.innerHTML = '';
            els.resultsList.className = 'results-list';
            els.resultsList.appendChild(frag);
        }
        // Remove any prior virtual scroll listener
        if (els.resultsBody) {
            els.resultsBody.onscroll = null;
        }
    }

    // -- Virtual scroll rendering (for large lists) --
    function renderVirtual() {
        if (!els.resultsList || !els.resultsBody) return;

        els.resultsList.innerHTML = '';
        els.resultsList.className = 'results-list results-list--virtual';

        const totalHeight = filteredDorks.length * VIRTUAL_ROW_HEIGHT;
        els.resultsList.style.height = totalHeight + 'px';
        els.resultsList.style.position = 'relative';

        const renderVisibleRows = () => {
            const scrollTop = els.resultsBody.scrollTop;
            const viewHeight = els.resultsBody.clientHeight;

            const startIdx = Math.max(0, Math.floor(scrollTop / VIRTUAL_ROW_HEIGHT) - VIRTUAL_OVERSCAN);
            const endIdx = Math.min(
                filteredDorks.length,
                Math.ceil((scrollTop + viewHeight) / VIRTUAL_ROW_HEIGHT) + VIRTUAL_OVERSCAN
            );

            // Remove out-of-view rows
            const existing = els.resultsList.querySelectorAll('.dork-row');
            existing.forEach((row) => {
                const rowIdx = parseInt(row.dataset.virtualIndex, 10);
                if (rowIdx < startIdx || rowIdx >= endIdx) {
                    row.remove();
                }
            });

            // Add new visible rows
            const existingIndices = new Set();
            els.resultsList.querySelectorAll('.dork-row').forEach((row) => {
                existingIndices.add(parseInt(row.dataset.virtualIndex, 10));
            });

            const frag = document.createDocumentFragment();
            for (let i = startIdx; i < endIdx; i++) {
                if (existingIndices.has(i)) continue;
                const row = createDorkRow(filteredDorks[i], i + 1);
                row.style.position = 'absolute';
                row.style.top = (i * VIRTUAL_ROW_HEIGHT) + 'px';
                row.style.left = '0';
                row.style.right = '0';
                row.style.height = VIRTUAL_ROW_HEIGHT + 'px';
                row.dataset.virtualIndex = i;
                frag.appendChild(row);
            }
            els.resultsList.appendChild(frag);
        };

        renderVisibleRows();
        els.resultsBody.onscroll = renderVisibleRows;
    }

    // -- Create Dork Row --
    function createDorkRow(dork, num) {
        const row = document.createElement('div');
        row.className = 'dork-row';
        row.dataset.index = num - 1;
        row.setAttribute('role', 'row');

        const numEl = document.createElement('div');
        numEl.className = 'dork-row__num';
        numEl.textContent = num;

        const textEl = document.createElement('div');
        textEl.className = 'dork-row__text';
        textEl.innerHTML = highlightDork(dork);

        const copyEl = document.createElement('button');
        copyEl.type = 'button';
        copyEl.className = 'dork-row__copy';
        copyEl.textContent = '\u{1F4CB}';
        copyEl.title = 'Copy this dork';
        copyEl.setAttribute('aria-label', 'Copy dork to clipboard');
        copyEl.addEventListener('click', (e) => {
            e.stopPropagation();
            copyToClipboard(dork);
            toast('Copied to clipboard');
        });

        row.addEventListener('click', () => {
            const idx = parseInt(row.dataset.index, 10);
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

    // -- Syntax Highlighting --
    function highlightDork(dork) {
        let html = escapeHtml(dork);

        // Highlight operators with quoted values: operator:"value"
        html = html.replace(
            /\b([\w.]+):(&quot;[^&]*&quot;)/gi,
            (match, op, val) => {
                const opLower = op.toLowerCase();
                if (['filetype', 'ext', 'mime'].includes(opLower)) {
                    return `<span class="op">${op}:</span><span class="ft">${val}</span>`;
                }
                return `<span class="op">${op}:</span><span class="qt">${val}</span>`;
            }
        );

        // Highlight operators with unquoted values: operator:value
        html = html.replace(
            /\b([\w.]+):(\S+)/gi,
            (match, op, val) => {
                if (match.includes('<span')) return match;
                const opLower = op.toLowerCase();
                if (['filetype', 'ext', 'mime'].includes(opLower)) {
                    return `<span class="op">${op}:</span><span class="ft">${val}</span>`;
                }
                return `<span class="op">${op}:</span><span class="kw">${val}</span>`;
            }
        );

        // Highlight "in:name value" style operators (GitHub)
        html = html.replace(
            /\b(in:\w+)\s+(\S+)/gi,
            (match, op, val) => {
                if (match.includes('<span')) return match;
                return `<span class="op">${op}</span> <span class="kw">${val}</span>`;
            }
        );

        // Highlight standalone quoted strings
        html = html.replace(
            /(?<![:\w])(&quot;[^&]*&quot;)/g,
            '<span class="qt">$1</span>'
        );

        // Highlight negations (prefix -)
        html = html.replace(
            /(^|\s)(-\S+)/g,
            '$1<span class="neg">$2</span>'
        );

        // Highlight NOT keyword (Bing/GitHub) and ~~ (Yandex)
        html = html.replace(
            /(^|\s)(NOT\s+\S+)/g,
            '$1<span class="neg">$2</span>'
        );
        html = html.replace(
            /(^|\s)(~~\S+)/g,
            '$1<span class="neg">$2</span>'
        );

        return html.trim();
    }

    // -- Filter --
    function applyFilter() {
        const term = els.searchInput?.value.trim().toLowerCase() || '';

        if (!term) {
            filteredDorks = [...allDorks];
        } else {
            filteredDorks = allDorks.filter((d) => d.toLowerCase().includes(term));
        }

        useVirtualScroll = filteredDorks.length > RENDER_CHUNK_LIMIT;
        selectedRows.clear();
        renderFilteredResults();
        updateButtons();

        // Highlight search term in rendered results (only for direct rendering)
        if (term && !useVirtualScroll && els.resultsList) {
            const escapedTerm = escapeRegex(escapeHtml(term));
            els.resultsList.querySelectorAll('.dork-row__text').forEach((el) => {
                el.innerHTML = el.innerHTML.replace(
                    new RegExp(`(${escapedTerm})`, 'gi'),
                    '<span class="highlight">$1</span>'
                );
            });
        }
    }

    // -- Sort / Shuffle --
    function sortResults() {
        if (sortAscending) {
            filteredDorks.sort((a, b) => a.localeCompare(b));
        } else {
            filteredDorks.sort((a, b) => b.localeCompare(a));
        }
        sortAscending = !sortAscending;
        if (els.sortBtn) {
            els.sortBtn.textContent = sortAscending ? 'A-Z' : 'Z-A';
        }
        selectedRows.clear();
        renderFilteredResults();
        updateButtons();
    }

    function shuffleResults() {
        for (let i = filteredDorks.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [filteredDorks[i], filteredDorks[j]] = [filteredDorks[j], filteredDorks[i]];
        }
        selectedRows.clear();
        renderFilteredResults();
        updateButtons();
    }

    // -- Copy --
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
            ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px;';
            document.body.appendChild(ta);
            ta.select();
            try { document.execCommand('copy'); } catch { /* ignore */ }
            document.body.removeChild(ta);
        }
    }

    // -- Export --
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

    // -- Update Buttons --
    function updateButtons() {
        const hasDorks = filteredDorks.length > 0;
        const hasSelected = selectedRows.size > 0;

        if (els.copyAllBtn) els.copyAllBtn.disabled = !hasDorks;
        if (els.copySelectedBtn) els.copySelectedBtn.disabled = !hasSelected;
        if (els.exportTxtBtn) els.exportTxtBtn.disabled = !hasDorks;
        if (els.exportCsvBtn) els.exportCsvBtn.disabled = !hasDorks;
        if (els.exportJsonBtn) els.exportJsonBtn.disabled = !hasDorks;
    }

    // -- Toast --
    function toast(message, type) {
        type = type || 'success';
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

    // -- Utilities --
    function escapeHtml(str) {
        const div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

    function escapeRegex(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    // -- Boot --
    document.addEventListener('DOMContentLoaded', init);
})();
