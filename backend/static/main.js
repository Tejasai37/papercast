// Custom Vintage Audio Player Logic

async function generateAudio(articleId) {
    const button = document.querySelector(`button[onclick="generateAudio('${articleId}')"]`);
    const playerContainer = document.getElementById(`player-${articleId}`);

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
            method: 'POST'
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
            <h6 class="text-uppercase fw-bold mb-3 small" style="letter-spacing: 2px;">Dispatch Summary</h6>
            <p class="fw-bold mb-3" style="font-family: var(--font-header); font-size: 1.2rem;">${data.tldr || 'No short summary available.'}</p>
            
            <div class="news-body small">
                <p>${data.summary || 'No detailed summary available.'}</p>
            </div>

            <h6 class="text-uppercase fw-bold mt-4 mb-2 small" style="opacity: 0.6;">Key Dispatches</h6>
            <ul class="small ps-3 mb-0" style="font-family: var(--font-news);">
                ${keyPointsHtml || '<li>No key points available.</li>'}
            </ul>
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
