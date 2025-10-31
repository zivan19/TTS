const form = document.getElementById("upload-form");
const voiceSelect = document.getElementById("voice-select");
const speedRange = document.getElementById("speed-range");
const speedDisplay = document.getElementById("speed-display");
const progressSection = document.getElementById("progress-section");
const progressFill = document.getElementById("progress-bar-fill");
const statusText = document.getElementById("status-text");
const downloads = document.getElementById("downloads");
const audioLink = document.getElementById("audio-link");
const subtitleLink = document.getElementById("subtitle-link");

async function fetchVoices() {
  try {
    const response = await fetch("/api/voices");
    if (!response.ok) throw new Error("Failed to load voices");
    const data = await response.json();
    voiceSelect.innerHTML = "";
    data.voices.forEach((voice) => {
      const option = document.createElement("option");
      option.value = voice.id;
      option.textContent = voice.label;
      voiceSelect.appendChild(option);
    });
  } catch (error) {
    console.error(error);
    const fallback = document.createElement("option");
    fallback.value = "neutral";
    fallback.textContent = "Neutral";
    voiceSelect.appendChild(fallback);
  }
}

function setLoading(isLoading) {
  Array.from(form.elements).forEach((element) => {
    if (element.tagName === "BUTTON") {
      element.disabled = isLoading;
    }
    if (element.type === "file" && isLoading) {
      element.setAttribute("disabled", "disabled");
    } else if (element.type === "file") {
      element.removeAttribute("disabled");
    }
  });
}

async function createJob(formData) {
  const response = await fetch("/api/jobs", {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(detail.detail || "Failed to start synthesis");
  }
  return response.json();
}

function subscribeToJob(jobId) {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const url = `${protocol}://${window.location.host}/api/jobs/${jobId}/events`;
  const ws = new WebSocket(url);

  ws.addEventListener("message", (event) => {
    const payload = JSON.parse(event.data);
    if (payload.event === "error") {
      statusText.textContent = payload.detail;
      progressFill.style.width = "0%";
      downloads.hidden = true;
      return;
    }

    const progress = Math.round((payload.progress || 0) * 100);
    progressFill.style.width = `${progress}%`;
    statusText.textContent = payload.message || payload.status;

    if (payload.status === "completed") {
      audioLink.href = `/api/jobs/${jobId}/result/audio`;
      subtitleLink.href = `/api/jobs/${jobId}/result/subtitles`;
      downloads.hidden = false;
      ws.close();
    }

    if (payload.status === "failed") {
      downloads.hidden = true;
      ws.close();
    }
  });

  ws.addEventListener("close", () => {
    setLoading(false);
  });

  ws.addEventListener("error", () => {
    statusText.textContent = "Connection error";
    setLoading(false);
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  statusText.textContent = "";
  downloads.hidden = true;
  progressFill.style.width = "0%";
  progressSection.hidden = false;

  const formData = new FormData(form);
  setLoading(true);

  try {
    const { job_id: jobId } = await createJob(formData);
    subscribeToJob(jobId);
  } catch (error) {
    statusText.textContent = error.message;
    setLoading(false);
  }
});

speedRange.addEventListener("input", () => {
  speedDisplay.textContent = `${parseFloat(speedRange.value).toFixed(1)}x`;
});

fetchVoices();
