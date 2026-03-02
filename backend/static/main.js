// Custom Vintage Audio Player Logic

async function generateAudio(articleId) {
    const button = document.querySelector(`button[onclick="generateAudio('${articleId}')"]`);
    const playerContainer = document.getElementById(`player-${articleId}`);

    // Get the selected language from the UI if available, else default to English
    const languageSelect = document.getElementById('language-select');
    const selectedLanguage = languageSelect ? languageSelect.value : 'en';

    // UI Feedback: Loading State
    const originalText = button.innerHTML;
    button.disabled = true;
    button.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Tuning...`;

    // Show static noise in player container while loading
    playerContainer.classList.remove('d-none');
    playerContainer.innerHTML = `
        <div class="static-noise d-flex align-items-center justify-content-center">
            <div class="text-white small fw-bold" style="font-family: var(--font-console); z-index: 10;">
                <i class="bi bi-broadcast"></i> ACQUIRING SIGNAL...
            </div>
        </div>
    `;

    try {
        const response = await fetch(`/api/generate_audio/${articleId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ language: selectedLanguage })
        });

        const data = await response.json();

        if (data.error) {
            alert(data.error);
            button.disabled = false;
            button.innerHTML = originalText;
            playerContainer.classList.add('d-none');
            return;
        }

        // Format Key Points as bullets
        const keyPointsHtml = data.key_points ? data.key_points.map(p => `<li>${p}</li>`).join('') : '';

        // Format Comprehend Entities
        const entitiesHtml = (data.nlp_entities && data.nlp_entities.length > 0)
            ? data.nlp_entities.map(e => `<span class="badge bg-secondary me-1 mb-1">${e}</span>`).join('')
            : '<span class="text-muted small">No significant entities found.</span>';

        // Format Comprehend Key Phrases
        const phrasesHtml = (data.nlp_key_phrases && data.nlp_key_phrases.length > 0)
            ? data.nlp_key_phrases.map(p => `<span class="badge border border-dark text-dark me-1 mb-1" style="background:transparent;">${p}</span>`).join('')
            : '';

        // Sentiment Badge Color Logic
        let sentimentColor = "bg-secondary";
        if (data.nlp_sentiment === "POSITIVE") sentimentColor = "bg-success";
        else if (data.nlp_sentiment === "NEGATIVE") sentimentColor = "bg-danger";
        else if (data.nlp_sentiment === "MIXED") sentimentColor = "bg-warning text-dark";

        // Format Script Dialogue
        const scriptHtml = data.script ? data.script
            .replace(/\[HOST\]:/g, '<span class="speaker-host">HOST</span>')
            .replace(/\[EXPERT\]:/g, '<span class="speaker-expert">EXPERT</span>')
            .replace(/\[HOST\]/g, '<span class="speaker-host">HOST</span>')
            .replace(/\[EXPERT\]/g, '<span class="speaker-expert">EXPERT</span>') : '';

        playerContainer.innerHTML = `
        <div class="radio-dashboard">
            <div class="small text-uppercase mb-2 fw-bold" style="font-family: var(--font-console); color: var(--dial-amber);">
                <i class="bi bi-broadcast"></i> Catching Frequency...
            </div>
            
            <div class="frequency-dial">
                <div class="dial-markings">
                    <span>550</span><span>700</span><span>900</span><span>1200</span><span>1400</span><span>1700</span>
                </div>
                <div class="frequency-needle" id="needle-${articleId}" style="left: 0%"></div>
            </div>

            <div class="player-controls mt-3">
                <button class="btn-play" id="play-btn-${articleId}" onclick="togglePlay('${articleId}')">
                    <i class="bi bi-play-fill"></i>
                </button>
                <div class="player-status">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <span class="status-text" id="time-${articleId}" style="color: var(--radio-gold);">0:00 / 0:00</span>
                    </div>
                    <div class="progress-container" onclick="seek(event, '${articleId}')">
                        <div class="progress-bar" id="bar-${articleId}"></div>
                    </div>
                </div>
            </div>
            
            <audio id="audio-${articleId}" src="${data.audio_url}" 
                ontimeupdate="updateProgress('${articleId}')" 
                onloadedmetadata="initDuration('${articleId}')"
                onended="resetPlayer('${articleId}')"></audio>
        </div>

        <!-- Broadsheet Insights Section -->
        <div class="mt-4 p-4 border border-dark" style="background: rgba(0,0,0,0.03);">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h6 class="text-uppercase fw-bold small mb-0" style="letter-spacing: 2px;">Dispatch Summary</h6>
                ${data.nlp_sentiment ? `<span class="badge ${sentimentColor}">${data.nlp_sentiment} Sentiment</span>` : ''}
            </div>
            
            <p class="fw-bold mb-3" style="font-family: var(--font-header); font-size: 1.2rem;">${data.tldr || 'No short summary available.'}</p>
            
            <div class="news-body small">
                <p>${data.summary || 'No detailed summary available.'}</p>
            </div>
            
            ${(entitiesHtml || phrasesHtml) ? `
            <div class="mt-3 mb-3 p-3 bg-white border border-light shadow-sm">
                <h6 class="text-uppercase fw-bold small mb-2" style="opacity: 0.7;">AI NLP Extraction</h6>
                <div class="mb-2"><strong>Entities:</strong><br/> ${entitiesHtml}</div>
                ${phrasesHtml ? `<div><strong>Keywords:</strong><br/> ${phrasesHtml}</div>` : ''}
            </div>
            ` : ''}

            <h6 class="text-uppercase fw-bold mt-4 mb-2 small" style="opacity: 0.6;">Key Dispatches</h6>
            <ul class="small ps-3 mb-4" style="font-family: var(--font-news);">
                ${keyPointsHtml || '<li>No key points available.</li>'}
            </ul>

            ${scriptHtml ? `
            <div class="mt-4 pt-3 border-top border-dark">
                <h6 class="text-uppercase fw-bold mb-3 small" style="font-family: var(--font-console);">Radio Script (Dialogue):</h6>
                <div class="dialogue-script small">
                    ${scriptHtml}
                </div>
            </div>
            ` : ''}
        </div>`;

        // Hide the original button after success to keep UI clean
        button.style.display = 'none';

    } catch (error) {
        console.error('Error:', error);
        alert('Failed to tune in. Please try again.');
        button.disabled = false;
        button.innerHTML = originalText;
    }
}

function togglePlay(id) {
    const audio = document.getElementById(`audio-${id}`);
    const btnIcon = document.querySelector(`#play-btn-${id} i`);

    if (audio.paused) {
        audio.play();
        btnIcon.classList.remove('bi-play-fill');
        btnIcon.classList.add('bi-pause-fill');
    } else {
        audio.pause();
        btnIcon.classList.remove('bi-pause-fill');
        btnIcon.classList.add('bi-play-fill');
    }
}

function updateProgress(id) {
    const audio = document.getElementById(`audio-${id}`);
    const bar = document.getElementById(`bar-${id}`);
    const timeDisplay = document.getElementById(`time-${id}`);

    if (audio.duration) {
        const percent = (audio.currentTime / audio.duration) * 100;
        bar.style.width = `${percent}%`;

        // Update the frequency needle position too!
        const needle = document.getElementById(`needle-${id}`);
        if (needle) {
            needle.style.left = `${percent}%`;
        }

        timeDisplay.textContent = `${formatTime(audio.currentTime)} / ${formatTime(audio.duration)}`;
    }
}

function initDuration(id) {
    const audio = document.getElementById(`audio-${id}`);
    const timeDisplay = document.getElementById(`time-${id}`);
    timeDisplay.textContent = `0:00 / ${formatTime(audio.duration)}`;
}

function seek(event, id) {
    const audio = document.getElementById(`audio-${id}`);
    const container = event.currentTarget; // The progress-container
    const width = container.clientWidth;
    const clickX = event.offsetX;
    const duration = audio.duration;

    audio.currentTime = (clickX / width) * duration;
}

function resetPlayer(id) {
    const btnIcon = document.querySelector(`#play-btn-${id} i`);
    btnIcon.classList.remove('bi-pause-fill');
    btnIcon.classList.add('bi-play-fill');
}

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}:${secs < 10 ? '0' : ''}${secs}`;
}
