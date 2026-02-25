// Custom Vintage Audio Player Logic

async function generateAudio(articleId) {
    const button = document.querySelector(`button[onclick="generateAudio('${articleId}')"]`);
    const playerContainer = document.getElementById(`player-${articleId}`);

    // UI Feedback: Loading State
    const originalText = button.innerHTML;
    button.disabled = true;
    button.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Tuning In...`;

    try {
        const response = await fetch(`/api/generate_audio/${articleId}`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const data = await response.json();

        // Success: Inject Custom Vintage Player HTML + Insights
        playerContainer.classList.remove('d-none');
        
        // Format Key Points as bullets
        const keyPointsHtml = data.key_points ? data.key_points.map(p => `<li>${p}</li>`).join('') : '';

        playerContainer.innerHTML = `
            <div class="vintage-player mb-3">
                <div class="player-controls">
                    <button class="btn-play" id="play-btn-${articleId}" onclick="togglePlay('${articleId}')">
                        <i class="bi bi-play-fill"></i>
                    </button>
                    <div class="player-status">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <span class="status-text text-accent">ON AIR</span>
                            <span class="status-text" id="time-${articleId}">0:00 / 0:00</span>
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

            <!-- AI Insights Section -->
            <div class="news-snippet border-0 bg-light p-3 mt-3 shadow-sm" style="border-left: 4px solid var(--accent-color) !important;">
                <h6 class="text-uppercase fw-bold text-accent mb-2 small"><i class="bi bi-journal-text me-2"></i> TLDR</h6>
                <p class="fw-bold mb-3">${data.tldr || 'No short summary available.'}</p>

                <h6 class="text-uppercase fw-bold text-muted mb-2 small">Full Summary</h6>
                <p class="small mb-3 text-secondary">${data.summary || 'No detailed summary available.'}</p>

                <h6 class="text-uppercase fw-bold text-muted mb-2 small">Key Facts</h6>
                <ul class="small text-secondary ps-3 mb-0">
                    ${keyPointsHtml || '<li>No key points available.</li>'}
                </ul>
            </div>
            
            <div class="alert alert-success mt-2 py-1 small text-center bg-transparent border-0 text-muted">
                <i class="bi bi-check-circle"></i> Broadcast Ready
            </div>
        `;

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
