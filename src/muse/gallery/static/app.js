// app.js — muse gallery SPA (local-only, serves user's own data)
var appEl = document.getElementById('app');
var breadcrumbEl = document.getElementById('breadcrumb');

var currentView = 'grid';
var currentSession = null;
var currentStep = null;
var pollTimer = null;

function fetchJSON(url) {
    return fetch(url).then(function(res) { return res.json(); });
}

function navigate(view, session, step) {
    currentView = view;
    currentSession = session;
    currentStep = step;
    render();
}

function render() {
    clearInterval(pollTimer);

    if (currentView === 'grid') {
        renderGrid();
        breadcrumbEl.textContent = '';
        pollTimer = setInterval(renderGrid, 2000);
    } else if (currentView === 'timeline') {
        renderTimeline();
        breadcrumbEl.textContent = '';
        var link = document.createElement('a');
        link.href = '#';
        link.textContent = 'sessions';
        link.addEventListener('click', function(e) { e.preventDefault(); navigate('grid'); });
        breadcrumbEl.appendChild(link);
        breadcrumbEl.appendChild(document.createTextNode(' / ' + currentSession));
        pollTimer = setInterval(function() { renderTimeline(true); }, 2000);
    }
}

function renderGrid() {
    fetchJSON('/api/sessions').then(function(sessions) {
        if (sessions.length === 0) {
            appEl.textContent = '';
            var emptyDiv = document.createElement('div');
            emptyDiv.className = 'empty';
            emptyDiv.textContent = 'No sessions yet. Run muse new "..." to start.';
            appEl.appendChild(emptyDiv);
            return;
        }

        var grid = document.createElement('div');
        grid.className = 'sessions-grid';

        sessions.forEach(function(s) {
            var card = document.createElement('div');
            card.className = 'session-card';
            card.addEventListener('click', function() { navigate('timeline', s.name, s.current_step); });

            var img = document.createElement('img');
            img.src = '/images/' + encodeURIComponent(s.name) + '/step-' + String(s.current_step).padStart(3, '0') + '.png';
            img.alt = s.name;
            img.addEventListener('error', function() { this.style.background = '#1a1a2e'; });

            var info = document.createElement('div');
            info.className = 'info';

            var nameDiv = document.createElement('div');
            nameDiv.className = 'name';
            nameDiv.textContent = s.name;

            var metaDiv = document.createElement('div');
            metaDiv.className = 'meta';
            metaDiv.textContent = s.total_steps + ' step' + (s.total_steps !== 1 ? 's' : '') + ' \u00b7 ' + s.provider;

            info.appendChild(nameDiv);
            info.appendChild(metaDiv);
            card.appendChild(img);
            card.appendChild(info);
            grid.appendChild(card);
        });

        appEl.textContent = '';
        appEl.appendChild(grid);
    });
}

function renderTimeline(isPolling) {
    fetchJSON('/api/sessions/' + encodeURIComponent(currentSession)).then(function(data) {
        if (data.error) {
            appEl.textContent = '';
            var errDiv = document.createElement('div');
            errDiv.className = 'empty';
            errDiv.textContent = data.error;
            appEl.appendChild(errDiv);
            return;
        }

        var session = data.session;
        var steps = data.steps;
        if (!currentStep) currentStep = session.current_step;

        if (isPolling && steps.length === parseInt(appEl.dataset.stepCount || '0', 10)) return;
        appEl.dataset.stepCount = steps.length;

        var activeStep = steps.find(function(s) { return s.step === currentStep; }) || steps[steps.length - 1];

        var strip = document.createElement('div');
        strip.className = 'timeline-strip';

        steps.forEach(function(s, i) {
            var thumb = document.createElement('div');
            thumb.className = 'timeline-thumb' + (s.step === currentStep ? ' active' : '');
            thumb.addEventListener('click', function() { currentStep = s.step; renderTimeline(); });

            var thumbImg = document.createElement('img');
            thumbImg.src = '/images/' + encodeURIComponent(session.name) + '/step-' + String(s.step).padStart(3, '0') + '.png';
            thumbImg.alt = 'Step ' + s.step;
            thumbImg.addEventListener('error', function() { this.style.background = '#1a1a2e'; });

            var label = document.createElement('div');
            label.className = 'label';
            label.textContent = 'Step ' + s.step + (s.step === session.current_step ? ' \u2605' : '');

            thumb.appendChild(thumbImg);
            thumb.appendChild(label);
            strip.appendChild(thumb);

            if (i < steps.length - 1) {
                var arrow = document.createElement('div');
                arrow.className = 'timeline-arrow';
                arrow.textContent = '\u2192';
                strip.appendChild(arrow);
            }
        });

        var detail = document.createElement('div');
        detail.className = 'step-detail';

        var imageDiv = document.createElement('div');
        imageDiv.className = 'step-image';
        var mainImg = document.createElement('img');
        mainImg.src = '/images/' + encodeURIComponent(session.name) + '/' + activeStep.image;
        mainImg.alt = 'Step ' + activeStep.step;
        imageDiv.appendChild(mainImg);

        var infoDiv = document.createElement('div');
        infoDiv.className = 'step-info';

        var stepLabel = document.createElement('div');
        stepLabel.className = 'step-label';
        stepLabel.textContent = 'Step ' + activeStep.step + (activeStep.step === session.current_step ? ' \u2014 current' : '');

        var prompt = document.createElement('div');
        prompt.className = 'prompt';
        prompt.textContent = '"' + activeStep.prompt + '"';

        var metadata = document.createElement('div');
        metadata.className = 'metadata';
        var metaLines = ['Provider: ' + activeStep.provider, 'Model: ' + activeStep.model];
        if (activeStep.parent_step) metaLines.push('From step: ' + activeStep.parent_step);
        metaLines.push(activeStep.timestamp);
        metadata.textContent = metaLines.join(' | ');

        infoDiv.appendChild(stepLabel);
        infoDiv.appendChild(prompt);
        infoDiv.appendChild(metadata);

        detail.appendChild(imageDiv);
        detail.appendChild(infoDiv);

        appEl.textContent = '';
        appEl.appendChild(strip);
        appEl.appendChild(detail);
    });
}

navigate('grid');
