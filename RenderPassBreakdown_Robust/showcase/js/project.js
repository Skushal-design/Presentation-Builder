/* =========================================================
   PROJECT PAGE LOGIC
========================================================= */

(function () {

    const bodyProject = document.body.getAttribute('data-project');
    if (bodyProject === null) return;

    if (typeof PROJECTS === 'undefined' || typeof PATHS === 'undefined') {
        console.error('data.js not loaded');
        if (typeof showToast === 'function') showToast('DATA.JS MISSING');
        return;
    }

    const id = parseInt(bodyProject, 10);
    if (isNaN(id) || id < 0 || id >= PROJECTS.length) {
        console.error('Invalid project index:', bodyProject);
        return;
    }

    const project = PROJECTS[id];
    if (!project) return;

    const asset = (path) => {
        if (!path) return '';
        return (PATHS.assetBase || '') + path;
    };

    function basenameFromPath(path) {
        if (!path) return '';
        const s = String(path).replace(/\\/g, '/');
        const base = s.split('/').pop() || s;
        return base.replace(/\.[^.]+$/, '');
    }

    function normalizePassItem(item) {
        if (!item) return null;
        if (typeof item === 'string') {
            return { src: item, name: basenameFromPath(item) };
        }
        if (typeof item === 'object') {
            const src = item.src || item.path || item.image || '';
            if (!src) return null;
            const name = item.name || item.label || item.title || basenameFromPath(src);
            return { src, name: String(name) };
        }
        return null;
    }

    function getProjectVideos(project) {
        const list = [];
        if (Array.isArray(project.videos) && project.videos.length) {
            project.videos.forEach((v, i) => {
                if (typeof v === 'string') {
                    list.push({ src: v, label: basenameFromPath(v) || ('Video ' + (i + 1)) });
                } else if (v && typeof v === 'object') {
                    const src = v.src || v.path || v.video || '';
                    if (!src) return;
                    list.push({
                        src,
                        label: v.label || v.name || basenameFromPath(src) || ('Video ' + (i + 1)),
                        poster: v.poster || ''
                    });
                }
            });
        }
        if (!list.length && project.video) {
            list.push({ src: project.video, label: 'Main', poster: project.poster || '' });
        }
        return list;
    }

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    const setText = (elId, text) => {
        const el = document.getElementById(elId);
        if (el) el.textContent = text;
    };

    setText('projectNumber', `PROJECT ${String(id + 1).padStart(2, '0')}`);
    setText('projectTitle', project.title || '');
    const catEl = document.getElementById('projectCategory');
    if (catEl) {
        catEl.innerHTML = (project.category || '').replace(/ \/ /g, '<br>');
    }
    // Optional per-project artist — showArtist can hide it; empty name falls back to global
    const artistEl = document.getElementById('projectArtist');
    if (artistEl) {
        const show = project.showArtist !== false;
        const local = (project.artistName || project.artist || '').trim();
        const globalName = (typeof ARTIST !== 'undefined' && ARTIST && ARTIST.name) ? ARTIST.name : '';
        const name = show ? (local || globalName) : '';
        if (name) {
            artistEl.textContent = name;
            artistEl.style.display = '';
            artistEl.classList.toggle('is-override', !!local);
        } else {
            artistEl.textContent = '';
            artistEl.style.display = 'none';
        }
    }

    // Status / tags
    const statusEl = document.getElementById('projectStatus');
    if (statusEl) {
        if (project.status) {
            statusEl.textContent = project.status;
            statusEl.className = 'tag-pill status-' + String(project.status).toLowerCase().replace(/\s+/g, '-');
            statusEl.style.display = '';
        } else {
            statusEl.style.display = 'none';
        }
    }
    const tagsEl = document.getElementById('projectTags');
    if (tagsEl) {
        const tags = project.tags || [];
        tagsEl.innerHTML = tags.map(t => '<span class="tag-pill">' + escapeHtml(t) + '</span>').join('');
    }

    const descEl = document.getElementById('projectDescription');
    if (descEl) {
        const raw = project.description || '';
        if (raw.indexOf('<') !== -1) {
            // Author-controlled rich text (b / i / mark / br)
            descEl.innerHTML = raw;
        } else {
            descEl.innerHTML = escapeHtml(raw).replace(/\n/g, '<br>');
        }
    }

    setText('pageCurrent', String(id + 1).padStart(2, '0'));
    setText('pageTotal', String(PROJECTS.length).padStart(2, '0'));

    const detailsEl = document.getElementById('projectDetails');
    if (detailsEl) {
        detailsEl.innerHTML = '';
        const details = project.details || {};
        const preferred = ['ROLE', 'TASK', 'DURATION', 'OUTPUT'];
        const keys = [
            ...preferred.filter(k => Object.prototype.hasOwnProperty.call(details, k)),
            ...Object.keys(details).filter(k => !preferred.includes(k)),
        ];
        keys.forEach(k => {
            const v = details[k];
            if (v === undefined || v === null) return;
            const d = document.createElement('div');
            d.className = 'detail';
            d.innerHTML = `
                <div class="detail-label">${escapeHtml(k)}</div>
                <div class="detail-value">${escapeHtml(String(v))}</div>
            `;
            detailsEl.appendChild(d);
        });
    }

    const toolsEl = document.getElementById('projectTools');
    if (toolsEl) {
        toolsEl.innerHTML = '';
        (project.tools || []).forEach(t => {
            const s = document.createElement('span');
            s.className = 'tool';
            s.textContent = t;
            toolsEl.appendChild(s);
        });
    }

    const contribEl = document.getElementById('contributionGrid');
    if (contribEl) {
        contribEl.innerHTML = '';
        (project.contributions || []).forEach(pair => {
            const num = Array.isArray(pair) ? pair[0] : (pair.num || '');
            const name = Array.isArray(pair) ? pair[1] : (pair.name || '');
            const c = document.createElement('div');
            c.className = 'breakdown-card';
            c.innerHTML = `<span>${escapeHtml(String(num))}</span><strong>${escapeHtml(String(name))}</strong>`;
            contribEl.appendChild(c);
        });
    }

    const video = document.getElementById('projectVideo');
    const progressBar = document.getElementById('progressBar');
    const progress = document.getElementById('progress');

    /* Poster: explicit field → after image → first gallery still */
    const posterPath = (
        project.poster ||
        project.after ||
        (project.gallery && project.gallery[0]) ||
        ''
    );

    const projectVideos = getProjectVideos(project);
    let currentVideoIndex = 0;

    function loadVideoAt(index, autoplay) {
        if (!video || !projectVideos.length) return;
        currentVideoIndex = Math.max(0, Math.min(index, projectVideos.length - 1));
        const entry = projectVideos[currentVideoIndex];
        const wasPaused = video.paused;
        const t = video.currentTime || 0;
        video.src = asset(entry.src);
        const p = entry.poster || posterPath || '';
        if (p) {
            video.setAttribute('poster', asset(p));
            video.poster = asset(p);
            const posterEl = document.getElementById('videoPosterOverlay');
            if (posterEl) posterEl.src = asset(p);
        }
        document.querySelectorAll('#videoSourceBar .video-source-btn').forEach((btn, i) => {
            btn.classList.toggle('active', i === currentVideoIndex);
        });
        video.load();
        if (autoplay || !wasPaused) {
            video.play().catch(() => {});
        }
        if (typeof showToast === 'function' && projectVideos.length > 1) {
            showToast(entry.label || ('VIDEO ' + (currentVideoIndex + 1)));
        }
    }

    // Video source switcher
    const sourceBar = document.getElementById('videoSourceBar');
    if (sourceBar) {
        sourceBar.innerHTML = '';
        if (projectVideos.length > 1) {
            projectVideos.forEach((entry, i) => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'video-source-btn' + (i === 0 ? ' active' : '');
                btn.textContent = entry.label || ('Video ' + (i + 1));
                btn.addEventListener('click', () => loadVideoAt(i, true));
                sourceBar.appendChild(btn);
            });
        }
    }

    if (video) {
        if (projectVideos.length) {
            video.src = asset(projectVideos[0].src);
            const p0 = projectVideos[0].poster || posterPath || '';
            if (p0) {
                video.setAttribute('poster', asset(p0));
                video.poster = asset(p0);
            }
        } else if (project.video) {
            video.src = asset(project.video);
            if (posterPath) {
                video.setAttribute('poster', asset(posterPath));
                video.poster = asset(posterPath);
            }
        }
        if (posterPath || (projectVideos[0] && projectVideos[0].poster)) {
            // poster handled above
        }

        // Overlay thumbnail (more reliable than native poster alone)
        let posterEl = document.getElementById('videoPosterOverlay');
        const wrapper = video.closest('.video-wrapper');
        if (wrapper && posterPath) {
            if (!posterEl) {
                posterEl = document.createElement('img');
                posterEl.id = 'videoPosterOverlay';
                posterEl.className = 'video-poster-overlay';
                posterEl.alt = 'Video thumbnail';
                wrapper.insertBefore(posterEl, video);
            }
            posterEl.src = asset(posterPath);
            posterEl.style.display = 'block';
            posterEl.onclick = () => {
                if (typeof window.togglePlay === 'function') window.togglePlay();
            };
        }

        const hidePoster = () => {
            if (posterEl) posterEl.classList.add('is-hidden');
        };
        const showPoster = () => {
            if (posterEl) posterEl.classList.remove('is-hidden');
        };

        video.addEventListener('play', hidePoster);
        video.addEventListener('playing', hidePoster);
        video.addEventListener('pause', () => {
            // Show thumbnail again only near the start
            if (video.currentTime < 0.25) showPoster();
        });
        video.addEventListener('ended', () => {
            video.currentTime = 0;
            showPoster();
        });

        video.load();

        video.addEventListener('timeupdate', () => {
            if (!video.duration || !progressBar) return;
            progressBar.style.width = (video.currentTime / video.duration * 100) + '%';
        });

        video.addEventListener('error', () => {
            if (typeof showToast === 'function') {
                showToast('VIDEO NOT FOUND OR FORMAT NOT SUPPORTED');
            }
            // Keep poster visible if video fails
            showPoster();
        });

        if (progress) {
            progress.addEventListener('click', (e) => {
                if (!video.duration) return;
                const rect = progress.getBoundingClientRect();
                video.currentTime = ((e.clientX - rect.left) / rect.width) * video.duration;
                hidePoster();
            });
        }
    }

    const chaptersEl = document.getElementById('chapters');
    if (chaptersEl) {
        chaptersEl.innerHTML = '';
        (project.chapters || []).forEach(ch => {
            const b = document.createElement('button');
            b.className = 'chapter';
            b.textContent = ch.name || '';
            b.onclick = () => {
                if (!video) return;
                video.currentTime = Number(ch.time) || 0;
                video.play().catch(() => {});
            };
            chaptersEl.appendChild(b);
        });
    }

    /* Gallery items: string path OR { src, caption } */
    function normalizeGalleryItem(item) {
        if (!item) return null;
        if (typeof item === 'string') return { src: item, caption: '' };
        if (typeof item === 'object') {
            const src = item.src || item.path || item.image || '';
            if (!src) return null;
            return { src, caption: item.caption || item.description || item.desc || '' };
        }
        return null;
    }

    const galleryItems = (project.gallery || []).map(normalizeGalleryItem).filter(Boolean);
    const passItemsEarly = (project.passes || []).map(normalizePassItem).filter(Boolean);

    // Unified full-view list (gallery stills OR render passes)
    let lightboxItems = [];
    let lightboxIndex = 0;
    let lightboxMode = 'gallery'; // 'gallery' | 'passes'

    const galleryEl = document.getElementById('gallery');
    if (galleryEl) {
        galleryEl.innerHTML = '';
        galleryItems.forEach((item, idx) => {
            const wrap = document.createElement('div');
            wrap.className = 'gallery-item';
            const el = document.createElement('img');
            el.src = asset(item.src);
            el.alt = item.caption || '';
            el.onerror = function () { wrap.style.display = 'none'; };
            el.onclick = () => openLightboxGallery(idx);
            wrap.appendChild(el);
            if (item.caption) {
                const cap = document.createElement('div');
                cap.className = 'gallery-caption';
                cap.textContent = item.caption;
                wrap.appendChild(cap);
            }
            galleryEl.appendChild(wrap);
        });
    }

    function updateLightbox() {
        const lb = document.getElementById('lightbox');
        const img = document.getElementById('lightboxImage');
        const cap = document.getElementById('lightboxCaption');
        const counter = document.getElementById('lightboxCounter');
        if (!lightboxItems.length) return;
        const item = lightboxItems[lightboxIndex];
        if (img) img.src = asset(item.src);
        const label = item.caption || item.name || '';
        if (cap) {
            cap.textContent = label;
            cap.style.display = label ? 'block' : 'none';
        }
        if (counter) counter.textContent = (lightboxIndex + 1) + ' / ' + lightboxItems.length;
        if (lb) lb.classList.add('active');
    }

    function openLightboxList(items, idx, mode) {
        lightboxItems = items || [];
        if (!lightboxItems.length) return;
        lightboxMode = mode || 'gallery';
        lightboxIndex = Math.max(0, Math.min(idx || 0, lightboxItems.length - 1));
        updateLightbox();
    }

    window.openLightboxGallery = (idx) => openLightboxList(galleryItems, idx, 'gallery');
    window.openLightboxPasses = (idx) => openLightboxList(passItemsEarly, idx, 'passes');

    window.openLightboxAt = (idx) => openLightboxGallery(idx);
    window.openLightbox = (src) => {
        // Prefer current mode list, then gallery, then passes
        const lists = [
            lightboxItems,
            galleryItems,
            passItemsEarly,
        ];
        for (const list of lists) {
            if (!list || !list.length) continue;
            const i = list.findIndex(g => asset(g.src) === src || g.src === src);
            if (i >= 0) {
                const mode = (list === passItemsEarly) ? 'passes' : 'gallery';
                openLightboxList(list, i, mode);
                return;
            }
        }
        // Fallback: single image
        openLightboxList([{ src: src.replace(/^\.\.\//, '').replace(PATHS.assetBase || '', ''), caption: '' }], 0, 'gallery');
    };
    window.closeLightbox = () => {
        document.getElementById('lightbox')?.classList.remove('active');
    };
    window.lightboxPrev = (e) => {
        if (e) { e.preventDefault(); e.stopPropagation(); }
        if (!lightboxItems.length) return;
        lightboxIndex = (lightboxIndex - 1 + lightboxItems.length) % lightboxItems.length;
        updateLightbox();
    };
    window.lightboxNext = (e) => {
        if (e) { e.preventDefault(); e.stopPropagation(); }
        if (!lightboxItems.length) return;
        lightboxIndex = (lightboxIndex + 1) % lightboxItems.length;
        updateLightbox();
    };

    const beforeImage = document.getElementById('beforeImage');
    const afterImage = document.getElementById('afterImage');
    const compareSlider = document.getElementById('compareSlider');
    const compareLine = document.getElementById('compareLine');
    const beforeLabel = document.getElementById('beforeLabel');
    const afterLabel = document.getElementById('afterLabel');
    const stagesHost = document.getElementById('compareStages');
    const pairNav = document.getElementById('comparePairNav');
    const pairHint = document.getElementById('comparePairHint');

    // Optional multi-stage pipeline: compareStages[{name,src}, ...]
    // Fallback: classic before / after fields
    function normalizeStage(item, i) {
        if (!item) return null;
        if (typeof item === 'string') {
            return { name: 'Stage ' + (i + 1), src: item };
        }
        const src = item.src || item.path || item.image || '';
        if (!src) return null;
        return {
            name: item.name || item.label || item.title || ('Stage ' + (i + 1)),
            src: src
        };
    }
    let stages = (project.compareStages || project.stages || [])
        .map(normalizeStage)
        .filter(Boolean);
    if (stages.length < 2) {
        // Build from legacy before/after when no stages list
        stages = [];
        if (project.before) stages.push({ name: 'Before', src: project.before });
        if (project.after) stages.push({ name: 'Final', src: project.after });
    }

    let stageA = 0;
    let stageB = Math.max(0, stages.length - 1);

    function setCompareImages() {
        if (!stages.length) return;
        const a = stages[stageA] || stages[0];
        const b = stages[stageB] || stages[stages.length - 1];
        if (beforeImage && a) beforeImage.src = asset(a.src);
        if (afterImage && b) afterImage.src = asset(b.src);
        if (beforeLabel) beforeLabel.textContent = (a && a.name) || 'BEFORE';
        if (afterLabel) afterLabel.textContent = (b && b.name) || 'AFTER';
        if (pairHint) {
            pairHint.textContent = stages.length > 2
                ? ((a && a.name) || '') + '  →  ' + ((b && b.name) || '')
                : '';
        }
        // highlight chips
        if (stagesHost) {
            stagesHost.querySelectorAll('.compare-stage-btn').forEach((btn, i) => {
                btn.classList.toggle('active-a', i === stageA);
                btn.classList.toggle('active-b', i === stageB);
            });
        }
    }

    if (stages.length >= 2) {
        setCompareImages();
        if (stagesHost && stages.length > 2) {
            stagesHost.style.display = 'flex';
            stagesHost.innerHTML = '';
            stages.forEach((st, i) => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'compare-stage-btn';
                btn.textContent = st.name;
                btn.title = 'Click: set left · Shift+click: set right';
                btn.addEventListener('click', (e) => {
                    if (e.shiftKey) {
                        stageB = i;
                        if (stageB === stageA) stageA = Math.max(0, stageB - 1);
                    } else {
                        stageA = i;
                        if (stageA === stageB) stageB = Math.min(stages.length - 1, stageA + 1);
                    }
                    setCompareImages();
                });
                stagesHost.appendChild(btn);
            });
            const hint = document.createElement('span');
            hint.className = 'compare-stage-hint';
            hint.textContent = 'Click left image · Shift+click right';
            stagesHost.appendChild(hint);
        }
        if (pairNav && stages.length > 2) {
            pairNav.style.display = 'flex';
            // consecutive pair mode helpers
            let pairIndex = 0; // compares stages[i] vs stages[i+1]
            function applyPair() {
                stageA = pairIndex;
                stageB = Math.min(stages.length - 1, pairIndex + 1);
                setCompareImages();
            }
            document.getElementById('comparePrevPair')?.addEventListener('click', () => {
                pairIndex = Math.max(0, pairIndex - 1);
                applyPair();
            });
            document.getElementById('compareNextPair')?.addEventListener('click', () => {
                pairIndex = Math.min(stages.length - 2, pairIndex + 1);
                applyPair();
            });
        }
    } else {
        if (beforeImage) beforeImage.src = asset(project.before || '');
        if (afterImage) afterImage.src = asset(project.after || '');
    }

    if (compareSlider && afterImage && compareLine) {
        const applyCompare = () => {
            const v = compareSlider.value;
            afterImage.style.clipPath = `inset(0 0 0 ${v}%)`;
            compareLine.style.left = v + '%';
        };
        compareSlider.addEventListener('input', applyCompare);
        applyCompare();
    }




    /* ---------- Render passes: diagonal split wipe + grid ---------- */
    const passItems = passItemsEarly;

    document.querySelectorAll('[data-media-tab]').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.getAttribute('data-media-tab');
            document.querySelectorAll('[data-media-tab]').forEach(b => b.classList.toggle('active', b === btn));
            document.querySelectorAll('.media-tab-panel').forEach(p => p.classList.remove('active'));
            if (tab === 'compare') {
                document.getElementById('mediaPanelCompare')?.classList.add('active');
            } else if (tab === 'breakdown') {
                document.getElementById('mediaPanelBreakdown')?.classList.add('active');
                var frame = document.getElementById('breakdownViewerFrame');
                var link = document.getElementById('breakdownViewerLink');
                if (frame && !frame.dataset.loaded) {
                    var pid = document.body.getAttribute('data-project');
                    // Prefer per-project viewer data when available
                    var src = '../../viewer/index.html';
                    if (pid !== null && pid !== '' && !isNaN(parseInt(pid, 10))) {
                        var key = 'project-' + String(parseInt(pid, 10) + 1).padStart(2, '0');
                        src = '../../viewer/index.html?project=' + encodeURIComponent(key);
                    }
                    frame.src = src;
                    frame.dataset.loaded = '1';
                    if (link) link.href = src;
                }
            } else {
                document.getElementById('mediaPanelPasses')?.classList.add('active');
            }
        });
    });
    if (!passItems.length) {
        const passTab = document.querySelector('[data-media-tab="passes"]');
        if (passTab) passTab.style.display = 'none';
    }

    const splitRoot = document.getElementById('passesCarousel');
    const baseImg = document.getElementById('passesBaseImg');
    const revealImg = document.getElementById('passesRevealImg');
    const revealLayer = document.getElementById('passesReveal');
    const nameEl = document.getElementById('passesCarouselName');
    const dotsEl = document.getElementById('passesCarouselDots');
    let passIndex = 0;
    let animating = false;

    function setPassImages(fromIdx, toIdx) {
        if (!passItems.length) return;
        const from = passItems[fromIdx] || passItems[toIdx];
        const to = passItems[toIdx];
        if (baseImg) {
            baseImg.src = asset(from.src);
            baseImg.alt = from.name || '';
            baseImg.onclick = () => openLightboxPasses(fromIdx);
        }
        if (revealImg) {
            revealImg.src = asset(to.src);
            revealImg.alt = to.name || '';
            revealImg.onclick = () => openLightboxPasses(toIdx);
        }
    }

    function showPass(i, animate) {
        if (!passItems.length) return;
        const next = ((i % passItems.length) + passItems.length) % passItems.length;
        if (next === passIndex && !animate) {
            // initial paint
            setPassImages(next, next);
            if (revealLayer) {
                revealLayer.style.transition = 'none';
                revealLayer.classList.remove('diag');
                // full reveal of current
                revealLayer.style.clipPath = 'polygon(0 0, 100% 0, 100% 100%, 0 100%)';
            }
            if (nameEl) nameEl.textContent = passItems[next].name || '';
            if (dotsEl) {
                dotsEl.querySelectorAll('.passes-carousel-dot').forEach((d, di) => {
                    d.classList.toggle('active', di === next);
                });
            }
            passIndex = next;
            return;
        }
        if (animating) return;
        const prev = passIndex;
        passIndex = next;
        if (nameEl) nameEl.textContent = passItems[passIndex].name || '';
        if (dotsEl) {
            dotsEl.querySelectorAll('.passes-carousel-dot').forEach((d, di) => {
                d.classList.toggle('active', di === passIndex);
            });
        }
        if (!animate || !revealLayer || !baseImg || !revealImg) {
            setPassImages(passIndex, passIndex);
            if (revealLayer) {
                revealLayer.style.transition = 'none';
                revealLayer.style.clipPath = 'polygon(0 0, 100% 0, 100% 100%, 0 100%)';
            }
            return;
        }
        // Diagonal split wipe: base = previous, reveal = next
        animating = true;
        baseImg.src = asset(passItems[prev].src);
        baseImg.alt = passItems[prev].name || '';
        revealImg.src = asset(passItems[passIndex].src);
        revealImg.alt = passItems[passIndex].name || '';
        revealImg.onclick = () => openLightboxPasses(passIndex);
        baseImg.onclick = () => openLightboxPasses(prev);

        revealLayer.style.transition = 'none';
        revealLayer.classList.add('diag');
        // start collapsed on diagonal
        revealLayer.style.clipPath = 'polygon(0 0, 0 0, 0 100%)';
        // force reflow
        void revealLayer.offsetWidth;
        revealLayer.style.transition = 'clip-path 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
        requestAnimationFrame(() => {
            revealLayer.style.clipPath = 'polygon(0 0, 100% 0, 100% 100%, 0 100%)';
        });
        const done = () => {
            animating = false;
            // settle: both show current
            if (baseImg) {
                baseImg.src = asset(passItems[passIndex].src);
                baseImg.alt = passItems[passIndex].name || '';
                baseImg.onclick = () => openLightboxPasses(passIndex);
            }
            revealLayer.removeEventListener('transitionend', done);
        };
        revealLayer.addEventListener('transitionend', done);
        setTimeout(done, 700);
    }

    if (passItems.length && (baseImg || revealImg)) {
        if (dotsEl) {
            dotsEl.innerHTML = '';
            passItems.forEach((_, i) => {
                const d = document.createElement('span');
                d.className = 'passes-carousel-dot' + (i === 0 ? ' active' : '');
                d.title = passItems[i].name || '';
                d.addEventListener('click', () => showPass(i, true));
                dotsEl.appendChild(d);
            });
        }
        document.getElementById('passesPrev')?.addEventListener('click', () => showPass(passIndex - 1, true));
        document.getElementById('passesNext')?.addEventListener('click', () => showPass(passIndex + 1, true));
        showPass(0, false);
    } else if (splitRoot) {
        splitRoot.classList.add('empty');
        if (nameEl) nameEl.textContent = 'NO PASSES';
    }

    // Full grid below content
    const passesSection = document.getElementById('passesSection');
    const passesGrid = document.getElementById('passesGrid');
    if (passesSection && passesGrid && passItems.length) {
        passesSection.style.display = '';
        passesGrid.innerHTML = '';
        passItems.forEach((item, idx) => {
            const card = document.createElement('div');
            card.className = 'pass-card';
            const img = document.createElement('img');
            img.src = asset(item.src);
            img.alt = item.name || '';
            img.loading = 'lazy';
            img.onerror = function () { card.style.opacity = '0.4'; };
            const label = document.createElement('div');
            label.className = 'pass-card-name';
            label.textContent = item.name || '';
            card.appendChild(img);
            card.appendChild(label);
            card.addEventListener('click', () => openLightboxPasses(idx));
            passesGrid.appendChild(card);
        });
    }


    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');

    if (prevBtn) {
        if (id > 0) prevBtn.href = PROJECTS[id - 1].file;
        else prevBtn.href = '../index.html';
    }

    if (nextBtn) {
        if (id < PROJECTS.length - 1) {
            nextBtn.href = PROJECTS[id + 1].file;
        } else {
            // Always go to fixed end slide (not part of PROJECTS list)
            nextBtn.href = 'end.html';
        }
    }

    /* Playback speed + clip limit */
    let playRate = 1;
    let clipLimitSec = 0;
    let clipStart = 0;

    function applyPlayRate(announce) {
        if (!video) return;
        video.playbackRate = playRate;
        document.querySelectorAll('[data-rate]').forEach(btn => {
            btn.classList.toggle('active', parseFloat(btn.getAttribute('data-rate')) === playRate);
        });
        if (announce && typeof showToast === 'function') showToast(playRate + '× SPEED');
    }

    function applyClipLimit(announce) {
        document.querySelectorAll('[data-clip]').forEach(btn => {
            const v = btn.getAttribute('data-clip');
            const match = (clipLimitSec === 0 && v === 'full') || (String(clipLimitSec) === v);
            btn.classList.toggle('active', match);
        });
        if (announce && typeof showToast === 'function') {
            showToast(clipLimitSec === 0 ? 'FULL VIDEO' : ('CLIP ' + clipLimitSec + 's'));
        }
    }

    window.setPlayRate = (rate) => {
        playRate = Number(rate) || 1;
        applyPlayRate(true);
    };
    window.setClipLimit = (sec) => {
        if (sec === 'full' || sec === 0 || sec === '0') clipLimitSec = 0;
        else clipLimitSec = Number(sec) || 0;
        if (video) clipStart = video.currentTime || 0;
        applyClipLimit(true);
    };

    if (video) {
        video.addEventListener('timeupdate', () => {
            // After the selected clip length, continue the rest of the video at 1×
            if (clipLimitSec > 0 && video.currentTime >= clipStart + clipLimitSec) {
                clipLimitSec = 0;
                playRate = 1;
                video.playbackRate = 1;
                applyPlayRate(false);
                applyClipLimit(false); // highlight FULL again
                if (typeof showToast === 'function') showToast('CLIP DONE · 1× CONTINUE');
            }
        });
    }

    document.querySelectorAll('[data-rate]').forEach(btn => {
        btn.addEventListener('click', () => window.setPlayRate(btn.getAttribute('data-rate')));
    });
    document.querySelectorAll('[data-clip]').forEach(btn => {
        btn.addEventListener('click', () => window.setClipLimit(btn.getAttribute('data-clip')));
    });
    applyPlayRate(false);
    applyClipLimit(false);

    window.togglePlay = () => {
        if (!video) return;
        if (video.paused) {
            clipStart = video.currentTime || 0;
            video.playbackRate = playRate;
            video.play().catch(() => {});
        } else {
            video.pause();
        }
    };
    window.restartVideo = () => {
        if (!video) return;
        video.currentTime = 0;
        video.play().catch(() => {});
    };
    window.toggleMute = () => {
        if (!video) return;
        video.muted = !video.muted;
        if (typeof showToast === 'function') {
            showToast(video.muted ? 'MUTED' : 'AUDIO ON');
        }
    };
    window.fullscreenVideo = () => {
        if (!video) return;
        if (video.requestFullscreen) video.requestFullscreen();
        else if (video.webkitRequestFullscreen) video.webkitRequestFullscreen();
    };

    document.addEventListener('keydown', (e) => {
        const tag = (e.target && e.target.tagName) || '';
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
        if (document.getElementById('helpPanel')?.classList.contains('active')) return;

        const lbOpen = document.getElementById('lightbox')?.classList.contains('active');
        if (lbOpen) {
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                e.stopPropagation();
                window.lightboxPrev(e);
                return;
            }
            if (e.key === 'ArrowRight') {
                e.preventDefault();
                e.stopPropagation();
                window.lightboxNext(e);
                return;
            }
            if (e.key === 'Escape') {
                e.preventDefault();
                e.stopPropagation();
                window.closeLightbox();
                return;
            }
            return;
        }

        if (e.code === 'Space') {
            e.preventDefault();
            window.togglePlay();
        } else if (e.key === 'r' || e.key === 'R') {
            window.restartVideo();
        } else if (e.key === 'm' || e.key === 'M') {
            window.toggleMute();
        } else if (e.key === 'f' || e.key === 'F') {
            window.fullscreenVideo();
        }
    });

    if (video) {
        video.addEventListener('dblclick', window.fullscreenVideo);
    }


    // Passes story mode button
    (function setupStory() {
        const btn = document.getElementById('passesStoryBtn');
        const stageImg = document.querySelector('.passes-split-img, .passes-carousel img, #passesStageImg');
        const label = document.getElementById('passesLabel') || document.querySelector('.passes-name, .pass-name-label');
        if (!btn) return;
        let timer = null;
        btn.addEventListener('click', () => {
            const raw = project.passes || [];
            if (!raw.length) return;
            if (timer) {
                clearInterval(timer);
                timer = null;
                btn.classList.remove('active');
                btn.textContent = 'Story';
                return;
            }
            btn.classList.add('active');
            btn.textContent = 'Stop';
            if (typeof window.startPassesStory === 'function') {
                timer = window.startPassesStory(raw, label, stageImg, 1600);
            }
        });
    })();

    // Chapter chips timeline
    (function setupChapters() {
        const host = document.getElementById('chapterTimeline');
        const video = document.getElementById('projectVideo');
        if (!host || !video) return;
        const chapters = project.chapters || [];
        if (!chapters.length) { host.style.display = 'none'; return; }
        host.className = 'chapter-timeline';
        host.innerHTML = '';
        chapters.forEach((ch) => {
            const name = Array.isArray(ch) ? ch[0] : (ch.name || ch.title || '');
            const time = Array.isArray(ch) ? ch[1] : (ch.time || ch.t || '0');
            const sec = typeof time === 'number' ? time : parseTime(time);
            const chip = document.createElement('button');
            chip.type = 'button';
            chip.className = 'chapter-chip';
            chip.textContent = name || (sec + 's');
            chip.addEventListener('click', () => {
                video.currentTime = sec;
                video.play().catch(() => {});
                host.querySelectorAll('.chapter-chip').forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
            });
            host.appendChild(chip);
        });
        function parseTime(s) {
            if (typeof s === 'number') return s;
            const p = String(s).split(':').map(Number);
            if (p.length === 3) return p[0]*3600 + p[1]*60 + p[2];
            if (p.length === 2) return p[0]*60 + p[1];
            return Number(s) || 0;
        }
    })();



    /* ========== Presenter VO (Web Speech) — inside page scope ========== */
    function pickFemaleVoice() {
        const voices = (window.speechSynthesis && speechSynthesis.getVoices()) || [];
        if (!voices.length) return null;
        const prefer = [
            /zira/i, /hazel/i, /susan/i, /samantha/i, /victoria/i, /karen/i,
            /moira/i, /tessa/i, /fiona/i, /female/i, /woman/i, /girl/i,
            /google uk english female/i, /microsoft.*(zira|hazel|susan)/i,
        ];
        for (const re of prefer) {
            const v = voices.find((x) => re.test(x.name) || re.test(x.voiceURI || ""));
            if (v) return v;
        }
        // Prefer any en voice that looks non-male
        const en = voices.filter((x) => (x.lang || "").toLowerCase().startsWith("en"));
        const soft = en.find((x) => !/male|david|mark|james|george|daniel/i.test(x.name));
        return soft || en[0] || voices[0] || null;
    }

    function buildProjectScript(proj) {
        if (!proj) return "";
        if (proj.vo_script && String(proj.vo_script).trim()) {
            return String(proj.vo_script).trim();
        }
        const parts = [];
        if (proj.title) parts.push(String(proj.title));
        if (proj.category) parts.push(String(proj.category));
        let desc = proj.description || "";
        if (typeof desc === "string") {
            desc = desc.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
            if (desc.length > 280) desc = desc.slice(0, 277) + "…";
            if (desc) parts.push(desc);
        }
        const details = proj.details || {};
        Object.keys(details).forEach((k) => {
            const v = details[k];
            if (v) parts.push(k + ": " + v);
        });
        const passes = (proj.passes || []).map((p) => {
            if (typeof p === "string") return p.split("/").pop();
            return p.name || (p.src || "").split("/").pop();
        }).filter(Boolean);
        if (passes.length) parts.push("Render passes: " + passes.join(", "));
        return parts.join(". ") + ".";
    }

    function speakProjectVO(proj) {
        if (!window.speechSynthesis) {
            if (typeof showToast === "function") showToast("NO SYSTEM VOICE — install a Windows voice pack");
            return;
        }
        const text = buildProjectScript(proj || project);
        if (!text) return;
        try {
            speechSynthesis.cancel();
            const u = new SpeechSynthesisUtterance(text);
            u.rate = 0.95;
            u.pitch = 1.05;
            const voice = pickFemaleVoice();
            if (voice) u.voice = voice;
            speechSynthesis.speak(u);
            if (typeof showToast === "function") showToast("VOICE-OVER");
        } catch (err) {
            console.warn("VO failed", err);
        }
    }

    function stopProjectVO() {
        try { if (window.speechSynthesis) speechSynthesis.cancel(); } catch (_) {}
    }

    // Prefetch voices (Chrome loads them async)
    if (window.speechSynthesis) {
        try { speechSynthesis.getVoices(); speechSynthesis.onvoiceschanged = function () {}; } catch (_) {}
    }

    document.addEventListener("keydown", (e) => {
        const tag = (e.target && e.target.tagName) || "";
        if (tag === "INPUT" || tag === "TEXTAREA") return;
        if (e.key === "v" || e.key === "V") {
            e.preventDefault();
            speakProjectVO(project);
        }
        if (e.key === "Escape") stopProjectVO();
    });

    // Optional on-page button if chrome has a slot
    
    // On-page Speak control
    (function addVoButton() {
        let bar = document.querySelector(".bottom-bar") || document.querySelector(".topbar-right");
        if (!bar) return;
        const b = document.createElement("button");
        b.type = "button";
        b.id = "voSpeakBtn";
        b.className = "bottom-button";
        b.textContent = "▶ Speak";
        b.title = "Speak project voice-over (V)";
        b.style.fontWeight = "700";
        b.style.padding = "10px 16px";
        b.style.letterSpacing = "0.04em";
        b.addEventListener("click", (e) => {
            e.preventDefault();
            speakProjectVO(project);
        });
        bar.appendChild(b);
    })();

    window.speakCurrentProjectVO = function () { speakProjectVO(project); };
    window.stopProjectVO = stopProjectVO;


})();
