"use strict";

const themeToggle = document.getElementById("theme-toggle");
const promptSelect = document.getElementById("prompt");
const backendSelect = document.getElementById("backend");
const promptFormBackend = document.getElementById("prompt-backend");
const promptFormModel = document.getElementById("prompt-lm-model");
const lmStudioControls = document.getElementById("lm-studio-controls");
const modelSelect = document.getElementById("lm-studio-model");
const modelStatus = document.getElementById("model-status");
const refreshModelsButton = document.getElementById("refresh-models");
const exampleSelect = document.getElementById("example");
const userPrompt = document.getElementById("user-prompt");
const runButton = document.getElementById("run-button");
const runnerForm = document.getElementById("runner-form");
const compatibilityMessage = document.getElementById(
    "compatibility-message",
);
const imageInputPanel = document.getElementById("image-input");
const imageDropZone = document.getElementById("image-drop-zone");
const imageInput = document.getElementById("image-override");
const imagePreview = document.getElementById("image-preview");
const imageStatus = document.getElementById("image-status");
const pythonRequestCode = document.getElementById("python-request-code");
const copyPythonRequest = document.getElementById(
    "copy-python-request",
);
const copyStatus = document.getElementById("copy-status");

function setTheme(theme) {
    document.documentElement.dataset.theme = theme;
    themeToggle.setAttribute("aria-pressed", String(theme === "dark"));
    themeToggle.textContent = theme === "dark"
        ? "Switch to light mode"
        : "Switch to dark mode";
}

if (themeToggle) {
    const savedTheme = localStorage.getItem("prompt-runner-theme");
    const initialTheme = savedTheme || (
        window.matchMedia("(prefers-color-scheme: dark)").matches
            ? "dark"
            : "light"
    );
    setTheme(initialTheme);
    themeToggle.addEventListener("click", () => {
        const nextTheme = (
            document.documentElement.dataset.theme === "dark"
                ? "light"
                : "dark"
        );
        localStorage.setItem("prompt-runner-theme", nextTheme);
        setTheme(nextTheme);
    });
}

if (promptSelect) {
    promptSelect.addEventListener("change", () => {
        promptSelect.form.requestSubmit();
    });
}

let modelsLoaded = false;

function selectedExampleOption() {
    return exampleSelect
        ? exampleSelect.selectedOptions[0]
        : null;
}

function syncPromptForm() {
    if (promptFormBackend && backendSelect) {
        promptFormBackend.value = backendSelect.value;
    }
    if (promptFormModel && modelSelect) {
        promptFormModel.value = (
            modelSelect.value || promptFormModel.value
        );
    }
}

function updateRequestExample() {
    if (!pythonRequestCode) {
        return;
    }
    const useLmStudio = backendSelect
        && backendSelect.value === "lm_studio";
    const baseUrl = useLmStudio
        ? pythonRequestCode.dataset.lmStudioUrl
        : pythonRequestCode.dataset.localUrl;
    const modelId = useLmStudio
        ? (modelSelect.value || "SELECT_LOADED_MODEL_ID")
        : pythonRequestCode.dataset.localModel;
    const lines = [
        "import json",
        "from urllib.request import Request, urlopen",
        "",
        `base_url = ${JSON.stringify(baseUrl)}`,
        `model_id = ${JSON.stringify(modelId)}`,
        'prompt_state = "You are Chromite, a small tadpole creature."',
        'user_input = "The pet owner says hello."',
        "state = prompt_state",
        "if user_input:",
        "    state = (",
        '        f"{state}\\n\\nUser message: {user_input}"',
        "        if state",
        '        else f"User message: {user_input}"',
        "    )",
        "payload = {",
        '    "model": model_id,',
        '    "state": state,',
        '    "questions": {',
        '        "greeting": {',
        '            "type": "noul",',
        '            "instructions": "Is the pet owner greeting Chromite?",',
        "        },",
        "    },",
        "}",
        "request = Request(",
        '    f"{base_url}/v1/systemone",',
        "    data=json.dumps(payload).encode('utf-8'),",
        '    headers={"Content-Type": "application/json"},',
        ")",
        "with urlopen(request) as response:",
        "    print(json.dumps(json.load(response), indent=2))",
    ];
    pythonRequestCode.textContent = lines.join("\n");
}

function updateImageInput() {
    if (!imageInputPanel || !exampleSelect || !imageInput) {
        return;
    }
    const option = selectedExampleOption();
    const isImage = option
        && option.dataset.isImage === "true";
    const useLmStudio = backendSelect
        && backendSelect.value === "lm_studio";
    imageInputPanel.hidden = !isImage || useLmStudio;
    imageInput.disabled = !isImage || useLmStudio;
    if (!isImage) {
        imageInput.value = "";
        URL.revokeObjectURL(imagePreview.src);
        imagePreview.removeAttribute("src");
        imagePreview.hidden = true;
    }
}

function updateRunState() {
    if (!runButton) {
        return;
    }
    const option = selectedExampleOption();
    const hasUserInput = Boolean(userPrompt && userPrompt.value.trim());
    const hasExample = Boolean(option);
    const hasInput = hasUserInput || hasExample;
    const useLmStudio = backendSelect
        && backendSelect.value === "lm_studio";
    let compatible = true;
    let reason = "";

    if (useLmStudio && runnerForm) {
        const questionsSupported = option
            ? option.dataset.lmQuestionsSupported === "true"
            : runnerForm.dataset.lmQuestionsSupported === "true";
        const selectedImage = Boolean(
            option && option.dataset.isImage === "true",
        );
        const imageIsReplaced = hasUserInput;
        compatible = questionsSupported && (
            !selectedImage || imageIsReplaced
        );
        if (!questionsSupported) {
            reason = (
                "LM Studio supports only noul, choice, and score questions."
            );
        } else if (selectedImage && !imageIsReplaced) {
            reason = (
                "This image example is unavailable in LM Studio mode. "
                + "Enter a text input to use it instead."
            );
        }
    }

    if (compatibilityMessage) {
        compatibilityMessage.textContent = reason;
        compatibilityMessage.hidden = !reason;
    }
    runButton.disabled = !hasInput || (
        useLmStudio && (
            !modelsLoaded
            || !modelSelect
            || !modelSelect.value
            || !compatible
        )
    );
}

async function loadModels() {
    if (!lmStudioControls || !modelSelect || !modelStatus) {
        return;
    }
    modelsLoaded = false;
    modelSelect.disabled = true;
    modelStatus.textContent = "Loading decision models...";
    modelSelect.replaceChildren(new Option("Select a model", ""));
    updateRunState();
    try {
        const response = await fetch(lmStudioControls.dataset.modelsUrl, {
            headers: {"Accept": "application/json"},
        });
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || "Could not load LM Studio models.");
        }
        if (!Array.isArray(result.models)) {
            throw new Error("LM Studio returned an unexpected model list.");
        }
        for (const modelId of result.models) {
            const option = new Option(modelId, modelId);
            modelSelect.add(option);
        }
        const selectedModel = (
            lmStudioControls.dataset.selectedModel
            || modelSelect.dataset.selectedModel
        );
        if (result.models.includes(selectedModel)) {
            modelSelect.value = selectedModel;
        }
        modelsLoaded = true;
        modelSelect.disabled = result.models.length === 0;
        modelStatus.textContent = result.models.length
            ? `Found ${result.models.length} loaded decision model(s).`
            : "No loaded decision models were found.";
    } catch (error) {
        modelStatus.textContent = error.message;
    }
    syncPromptForm();
    updateRequestExample();
    updateRunState();
}

if (backendSelect) {
    backendSelect.addEventListener("change", () => {
        const useLmStudio = backendSelect.value === "lm_studio";
        lmStudioControls.hidden = !useLmStudio;
        syncPromptForm();
        updateImageInput();
        updateRequestExample();
        updateRunState();
        if (useLmStudio && !modelsLoaded) {
            loadModels();
        }
    });
}

if (refreshModelsButton) {
    refreshModelsButton.addEventListener("click", loadModels);
}

if (modelSelect) {
    modelSelect.addEventListener("change", () => {
        syncPromptForm();
        updateRequestExample();
        updateRunState();
    });
}

if (exampleSelect) {
    exampleSelect.addEventListener("change", () => {
        updateImageInput();
        updateRunState();
    });
}

if (userPrompt) {
    userPrompt.addEventListener("input", updateRunState);
}

if (imageInput) {
    imageInput.addEventListener("change", () => {
        const file = imageInput.files[0];
        if (!file) {
            URL.revokeObjectURL(imagePreview.src);
            imagePreview.removeAttribute("src");
            imagePreview.hidden = true;
            return;
        }
        const supportedTypes = [
            "image/jpeg",
            "image/png",
            "image/webp",
        ];
        if (!supportedTypes.includes(file.type)) {
            imageInput.value = "";
            imageStatus.textContent = (
                "Choose a PNG, JPEG, or WebP image."
            );
            return;
        }
        imageStatus.textContent = "";
        URL.revokeObjectURL(imagePreview.src);
        imagePreview.src = URL.createObjectURL(file);
        imagePreview.hidden = false;
    });
}

if (imageDropZone && imageInput) {
    imageDropZone.addEventListener("dragover", (event) => {
        event.preventDefault();
        imageDropZone.classList.add("is-dragging");
    });
    imageDropZone.addEventListener("dragleave", () => {
        imageDropZone.classList.remove("is-dragging");
    });
    imageDropZone.addEventListener("drop", (event) => {
        event.preventDefault();
        imageDropZone.classList.remove("is-dragging");
        const file = event.dataTransfer.files[0];
        const supportedTypes = [
            "image/jpeg",
            "image/png",
            "image/webp",
        ];
        if (!file || !supportedTypes.includes(file.type)) {
            imageStatus.textContent = (
                "Drop a PNG, JPEG, or WebP image."
            );
            return;
        }
        const transfer = new DataTransfer();
        transfer.items.add(file);
        imageInput.files = transfer.files;
        imageInput.dispatchEvent(new Event("change"));
    });
}

if (copyPythonRequest && pythonRequestCode && copyStatus) {
    copyPythonRequest.addEventListener("click", async () => {
        try {
            await navigator.clipboard.writeText(
                pythonRequestCode.textContent,
            );
            copyStatus.textContent = "Copied.";
        } catch (error) {
            copyStatus.textContent = (
                `Could not copy: ${error.message}. Select the code manually.`
            );
        }
    });
}

syncPromptForm();
updateRequestExample();
updateImageInput();
updateRunState();
if (backendSelect && backendSelect.value === "lm_studio") {
    lmStudioControls.hidden = false;
    loadModels();
}
